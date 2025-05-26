from django.db import models
from django.conf import settings
from django.utils import timezone

class Conversation(models.Model):
    """
    Represents a private chat conversation between two or more users.
    For a simple 1-on-1 chat, participants m2m might seem like overkill,
    but it allows for future group chats easily.
    """
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Users participating in this conversation."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of the last message or activity.")

    def __str__(self):
        # Generate a string representation, e.g., names of participants
        participant_names = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation between {participant_names}"

    class Meta:
        ordering = ['-updated_at']
        # Optional: Ensure unique set of participants for 1-on-1 if strictly needed,
        # but this is complex with ManyToManyField. Usually handled at creation logic.

    def update_timestamp(self):
        """Helper method to update the conversation's timestamp when a new message is added."""
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])


class Message(models.Model):
    """
    Represents a single message within a conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # Or SET_NULL if you want to keep messages from deleted users
        related_name='sent_messages'
    )
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, help_text="Has the recipient(s) read this message?")
    # You might add more fields like read_by (M2M to User) for group chats
    # or read_at timestamp.

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['timestamp'] # Oldest messages first

    def save(self, *args, **kwargs):
        """Override save to update conversation timestamp."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.conversation:
            self.conversation.update_timestamp()