from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid # For unique attachment filenames

def chat_attachment_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/chat_attachments/<conversation_id>/<random_filename>.<ext>
    # Ensure filename is somewhat sanitized or use uuid for the full name if concerned about original filenames
    ext = filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{ext}"
    # Use instance.conversation.id only if conversation is already saved and has an ID.
    # For new messages in new conversations, this might need adjustment or deferral.
    # However, message is saved after conversation is typically established.
    conversation_id_for_path = instance.conversation.id if instance.conversation and instance.conversation.id else "temp_conv"
    return f'chat_attachments/{conversation_id_for_path}/{random_filename}'

class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_conversations', # Changed related_name to avoid clash
        help_text="Users participating in this conversation."
    )
    # True if the DM request has been accepted by the recipient responding or explicitly accepting.
    is_accepted = models.BooleanField(default=False)
    # The user who initiated the conversation by sending the first message.
    # This helps in determining who needs to accept the request.
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='initiated_conversations',
        on_delete=models.SET_NULL, # If initiator is deleted, conversation might still exist but uninitiated
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of the last message or activity.")

    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        status = "Accepted" if self.is_accepted else "Pending"
        initiator_username = f" (Initiator: {self.initiator.username})" if self.initiator else ""
        return f"Conversation ({status}) between {participant_names}{initiator_username}"

    class Meta:
        ordering = ['-updated_at']
        # Consider constraints if needed, e.g., ensuring initiator is a participant (often handled in save())

    def update_timestamp(self):
        """Manually update the timestamp when a new message is added."""
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])

    def get_other_participant(self, user):
        """Helper to get the other participant in a 1-on-1 conversation."""
        if self.participants.count() == 2: # Assuming mostly 1-on-1 for DMs
            return self.participants.exclude(id=user.id).first()
        return None


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        AUDIO = 'AUDIO', 'Audio Attachment' # For uploaded audio files
        VOICE = 'VOICE', 'Voice Message' # For recorded voice notes
        TRACK_SHARE = 'TRACK_SHARE', 'Track Share' # Future: for sharing tracks

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    text = models.TextField(blank=True, null=True) # Can be blank if it's an attachment-only message
    
    attachment = models.FileField(upload_to=chat_attachment_path, blank=True, null=True)
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    
    # Future: For track shares
    # shared_track = models.ForeignKey('music.Track', on_delete=models.SET_NULL, null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, help_text="Has the recipient(s) read this message?")

    def __str__(self):
        return f"Message ({self.get_message_type_display()}) from {self.sender.username} in Conv {self.conversation.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['timestamp']

    def save(self, *args, **kwargs):
        is_new = self._state.adding # Check if it's a new message being added

        # Basic validation
        if self.message_type == self.MessageType.TEXT and not self.text:
            raise ValueError("Text message cannot be empty if message type is TEXT.")
        if (self.message_type == self.MessageType.AUDIO or self.message_type == self.MessageType.VOICE) and not self.attachment:
            raise ValueError(f"{self.get_message_type_display()} message must have an attachment.")
        # Add more validation as needed (e.g., attachment type for AUDIO/VOICE based on file extension)

        super().save(*args, **kwargs)

        if is_new and self.conversation:
            # If this message is from the recipient of a pending DM, accept the conversation
            if not self.conversation.is_accepted and \
               self.conversation.initiator and \
               self.sender != self.conversation.initiator:
                # Check if this is the first message from this non-initiator user in this conversation
                # to avoid re-triggering acceptance on subsequent messages.
                # (A more robust check might be to see if there are *any* prior messages from this sender in this convo)
                if not self.conversation.messages.filter(sender=self.sender).exclude(pk=self.pk).exists():
                    self.conversation.is_accepted = True
                    self.conversation.save(update_fields=['is_accepted', 'updated_at']) # Ensure updated_at is also saved
                else: # If not the first reply, still update timestamp
                    self.conversation.update_timestamp()

            else: # For all other new messages (e.g., in accepted convos, or from initiator)
                self.conversation.update_timestamp()
            
            # Notification logic could be triggered here after save
            # E.g., if self.conversation.is_accepted: send_notification(self)