from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid 
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
import logging
import os 
from django.core.exceptions import ValidationError

from vaultwave.utils import delete_file_if_changed, delete_file_on_instance_delete

logger = logging.getLogger(__name__)

def chat_attachment_path(instance, filename):
    ext = os.path.splitext(filename)[1] 
    random_filename = f"{uuid.uuid4()}{ext}"
    conversation_id_for_path = instance.conversation.id if instance.conversation and instance.conversation.id else "temp_conv"
    return f'chat_attachments/{conversation_id_for_path}/{random_filename}'

class Conversation(models.Model):
    class IdentityType(models.TextChoices): # For initiator's identity in this conversation
        USER = 'USER', 'User'
        ARTIST = 'ARTIST', 'Artist'

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_conversations',
        help_text="Users participating in this conversation."
    )
    is_accepted = models.BooleanField(default=False)
    
    # The User who technically created the conversation record
    initiator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='initiated_user_conversations', # New related_name
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="The actual user who created this conversation."
    )
    # The identity the initiator_user chose for THIS conversation
    initiator_identity_type = models.CharField(
        max_length=10,
        choices=IdentityType.choices,
        default=IdentityType.USER,
        help_text="The identity (User or Artist) the initiator used for this conversation."
    )
    initiator_artist_profile = models.ForeignKey(
        'music.Artist',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='initiated_artist_conversations',
        help_text="If initiator_identity_type is ARTIST, this links to their artist profile."
    )

    # Who the conversation is directed TOWARDS (if an artist)
    related_artist_recipient = models.ForeignKey( # Renamed for clarity
        'music.Artist', 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_artist_conversations', # New related_name
        help_text="If this conversation is directed towards an artist profile, this links to that target artist."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of the last message or activity.")

    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        status = "Accepted" if self.is_accepted else "Pending"
        
        initiator_display = "N/A"
        if self.initiator_user:
            if self.initiator_identity_type == self.IdentityType.ARTIST and self.initiator_artist_profile:
                initiator_display = f"{self.initiator_artist_profile.name} [Artist] (via {self.initiator_user.username})"
            else:
                initiator_display = f"{self.initiator_user.username} [User]"
        
        recipient_context = ""
        if self.related_artist_recipient:
            recipient_context = f" (To Artist: {self.related_artist_recipient.name})"
        
        return f"Conversation ({status}) initiated by {initiator_display}{recipient_context} with {participant_names}"

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['initiator_identity_type', 'initiator_artist_profile']),
        ]

    def clean(self):
        super().clean()
        if self.initiator_identity_type == self.IdentityType.ARTIST:
            if not self.initiator_artist_profile:
                raise ValidationError("If initiator_identity_type is ARTIST, initiator_artist_profile must be set.")
            if self.initiator_user and self.initiator_artist_profile.user != self.initiator_user:
                raise ValidationError("Initiator artist profile must belong to the initiator user.")
        if self.initiator_identity_type == self.IdentityType.USER and self.initiator_artist_profile:
            raise ValidationError("Initiator_artist_profile should not be set if initiator_identity_type is USER.")

    def save(self, *args, **kwargs):
        if self.initiator_identity_type == self.IdentityType.USER:
            self.initiator_artist_profile = None
        self.full_clean()
        super().save(*args, **kwargs)


    def update_timestamp(self):
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])

    def get_other_participant(self, user_instance): # Parameter renamed for clarity
        if self.participants.count() == 2:
            return self.participants.exclude(id=user_instance.id).first()
        return None

class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        AUDIO = 'AUDIO', 'Audio Attachment'
        VOICE = 'VOICE', 'Voice Message' # New
        TRACK_SHARE = 'TRACK_SHARE', 'Track Share' # New

    class SenderIdentity(models.TextChoices): 
        USER = 'USER', 'User'
        ARTIST = 'ARTIST', 'Artist'

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender_user = models.ForeignKey( 
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages'
    )
    sender_identity_type = models.CharField(
        max_length=10,
        choices=SenderIdentity.choices,
        help_text="The identity (User or Artist) used by the sender for this message."
    )
    sending_artist = models.ForeignKey(
        'music.Artist',
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='sent_chat_messages_as_artist',
        help_text="The artist profile used for sending, if sender_identity_type is ARTIST."
    )
    
    text = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to=chat_attachment_path, blank=True, null=True)
    original_attachment_filename = models.CharField(max_length=255, blank=True, null=True)
    
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    shared_track = models.ForeignKey( # New field for track sharing
        'music.Track',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chat_shares',
        help_text="The track shared in this message, if any."
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, help_text="Has the recipient(s) read this message?")

    def __str__(self):
        sender_display = self.sender_user.username
        if self.sender_identity_type == self.SenderIdentity.ARTIST and self.sending_artist:
            sender_display = f"{self.sending_artist.name} [Artist]"
        return f"Message ({self.get_message_type_display()}) from {sender_display} in Conv {self.conversation.id}"

    class Meta:
        ordering = ['timestamp']
        indexes = [ 
            models.Index(fields=['sender_identity_type', 'sending_artist']),
        ]

    def clean(self): 
        super().clean()
        if self.sender_identity_type == self.SenderIdentity.ARTIST and not self.sending_artist:
            raise ValidationError("If sender_identity_type is ARTIST, sending_artist must be set.")
        if self.sender_identity_type == self.SenderIdentity.ARTIST and self.sending_artist:
            if self.sending_artist.user != self.sender_user:
                raise ValidationError("Sending artist must belong to the sender user.")
        if self.sender_identity_type == self.SenderIdentity.USER and self.sending_artist:
            raise ValidationError("Sending_artist should not be set if sender_identity_type is USER.")
        
        if self.message_type == self.MessageType.TRACK_SHARE and not self.shared_track:
            raise ValidationError("A track must be specified for 'Track Share' message type.")
        if self.message_type != self.MessageType.TRACK_SHARE and self.shared_track:
            raise ValidationError("shared_track should only be set for 'Track Share' message type.")
        if self.message_type == self.MessageType.TRACK_SHARE and self.attachment:
            raise ValidationError("Track share messages should not have a direct file attachment.")


    def save(self, *args, **kwargs):
        if self.sender_identity_type == Message.SenderIdentity.USER:
            self.sending_artist = None
        if self.message_type != self.MessageType.TRACK_SHARE:
            self.shared_track = None
        if self.message_type == self.MessageType.TRACK_SHARE:
             self.attachment = None # Ensure no attachment for track shares
             self.original_attachment_filename = None

        self.full_clean()

        is_new = self._state.adding
        file_changed = False
        if self.pk: 
            try:
                old_instance = Message.objects.get(pk=self.pk)
                if old_instance.attachment != self.attachment:
                    file_changed = True
            except Message.DoesNotExist: pass 
        elif self.attachment and self.attachment.name: file_changed = True

        if self.attachment and self.attachment.name and (is_new or file_changed):
            if not self.original_attachment_filename or file_changed : 
                self.original_attachment_filename = os.path.basename(self.attachment.name)
        elif not self.attachment and self.original_attachment_filename: 
             # Only clear original_attachment_filename if there's no attachment *and* it's not a track share
             if self.message_type != self.MessageType.TRACK_SHARE:
                self.original_attachment_filename = None
        
        if not self.sender_user_id: raise ValueError("Message must have a sender_user.")
        
        if self.message_type == self.MessageType.TEXT and not self.text:
            if not self.attachment: 
                raise ValueError("Text message cannot be empty if message type is TEXT and no attachment is present.")
        if (self.message_type == self.MessageType.AUDIO or self.message_type == self.MessageType.VOICE) and not self.attachment:
            if is_new: 
                raise ValueError(f"{self.get_message_type_display()} message must have an attachment.")
        
        super().save(*args, **kwargs)

        if is_new and self.conversation:
            if not self.conversation.is_accepted and \
               self.conversation.initiator_user and \
               self.sender_user != self.conversation.initiator_user: 
                if not self.conversation.messages.filter(sender_user=self.sender_user).exclude(pk=self.pk).exists():
                    self.conversation.is_accepted = True
                    self.conversation.save(update_fields=['is_accepted', 'updated_at'])
                else: self.conversation.update_timestamp()
            else: self.conversation.update_timestamp()

@receiver(pre_save, sender=Message)
def message_pre_save_delete_old_attachment(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'attachment')

@receiver(post_delete, sender=Message)
def message_post_delete_cleanup_attachment(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.attachment)