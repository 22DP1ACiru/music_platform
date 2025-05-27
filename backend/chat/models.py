from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid # For unique attachment filenames
from django.db.models.signals import pre_save, post_delete # For file deletion signals
from django.dispatch import receiver # For file deletion signals
import logging

# Import utility functions for file deletion
from vaultwave.utils import delete_file_if_changed, delete_file_on_instance_delete

logger = logging.getLogger(__name__)

def chat_attachment_path(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = f"{uuid.uuid4()}.{ext}"
    conversation_id_for_path = instance.conversation.id if instance.conversation and instance.conversation.id else "temp_conv"
    return f'chat_attachments/{conversation_id_for_path}/{random_filename}'

class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_conversations',
        help_text="Users participating in this conversation."
    )
    is_accepted = models.BooleanField(default=False)
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='initiated_conversations',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    # New field to link conversation to an artist context if applicable
    related_artist = models.ForeignKey(
        'music.Artist', # Use string reference to avoid circular import
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='artist_context_conversations',
        help_text="If this conversation is directed towards an artist profile, this links to that artist."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of the last message or activity.")

    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        status = "Accepted" if self.is_accepted else "Pending"
        initiator_username = f" (Initiator: {self.initiator.username})" if self.initiator else ""
        artist_context = f" (Context: Artist {self.related_artist.name})" if self.related_artist else ""
        return f"Conversation ({status}) between {participant_names}{initiator_username}{artist_context}"

    class Meta:
        ordering = ['-updated_at']

    def update_timestamp(self):
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])

    def get_other_participant(self, user):
        if self.participants.count() == 2:
            return self.participants.exclude(id=user.id).first()
        return None


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        AUDIO = 'AUDIO', 'Audio Attachment'
        VOICE = 'VOICE', 'Voice Message'
        TRACK_SHARE = 'TRACK_SHARE', 'Track Share'

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
    text = models.TextField(blank=True, null=True)
    
    attachment = models.FileField(upload_to=chat_attachment_path, blank=True, null=True)
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    
    # shared_track = models.ForeignKey('music.Track', on_delete=models.SET_NULL, null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, help_text="Has the recipient(s) read this message?")

    def __str__(self):
        return f"Message ({self.get_message_type_display()}) from {self.sender.username} in Conv {self.conversation.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['timestamp']

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if self.message_type == self.MessageType.TEXT and not self.text:
            raise ValueError("Text message cannot be empty if message type is TEXT.")
        if (self.message_type == self.MessageType.AUDIO or self.message_type == self.MessageType.VOICE) and not self.attachment:
            raise ValueError(f"{self.get_message_type_display()} message must have an attachment.")
        
        super().save(*args, **kwargs)

        if is_new and self.conversation:
            if not self.conversation.is_accepted and \
               self.conversation.initiator and \
               self.sender != self.conversation.initiator:
                if not self.conversation.messages.filter(sender=self.sender).exclude(pk=self.pk).exists():
                    self.conversation.is_accepted = True
                    # When accepting, also make sure related_artist is preserved if it was set
                    # No specific change needed here for related_artist, just that save() includes it if it has a value.
                    self.conversation.save(update_fields=['is_accepted', 'updated_at'])
                else:
                    self.conversation.update_timestamp()
            else:
                self.conversation.update_timestamp()

# --- Signal Receivers for Message Attachments ---
@receiver(pre_save, sender=Message)
def message_pre_save_delete_old_attachment(sender, instance, **kwargs):
    """ Deletes old file from storage when Message.attachment is changed """
    delete_file_if_changed(sender, instance, 'attachment')

@receiver(post_delete, sender=Message)
def message_post_delete_cleanup_attachment(sender, instance, **kwargs):
    """ Deletes file from storage when Message instance is deleted """
    delete_file_on_instance_delete(instance.attachment)