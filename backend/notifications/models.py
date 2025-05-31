from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_RELEASE = 'NEW_RELEASE', 'New Release'
        NEW_FOLLOWER = 'NEW_FOLLOWER', 'New Follower'
        SALE_MADE_ARTIST = 'SALE_MADE_ARTIST', 'Sale Made (Artist)'
        NEW_CHAT_MESSAGE = 'NEW_CHAT_MESSAGE', 'New Chat Message'
        # Future: MENTION, COMMENT_ON_TRACK, etc.

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user who receives the notification."
    )
    
    # Actor: Who performed the action (optional)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Keep notification even if actor is deleted
        null=True, blank=True,
        related_name='triggered_notifications_as_user',
        help_text="The user who performed the action (e.g., followed, sent message)."
    )
    actor_artist = models.ForeignKey(
        'music.Artist',
        on_delete=models.SET_NULL, # Keep notification even if actor artist profile is deleted
        null=True, blank=True,
        related_name='triggered_notifications_as_artist',
        help_text="The artist profile that performed the action (e.g., released music)."
    )

    verb = models.CharField(max_length=255, help_text="A short description of the action, e.g., 'released', 'followed you'.")
    description = models.TextField(blank=True, null=True, help_text="Optional: More details about the notification or a preview.")
    
    notification_type = models.CharField(max_length=50, choices=NotificationType.choices, db_index=True)
    
    # Target: The primary object this notification is about (optional)
    target_release = models.ForeignKey(
        'music.Release',
        on_delete=models.CASCADE, # If release deleted, notification might not make sense or link broken
        null=True, blank=True,
        related_name='notifications_about'
    )
    target_artist_profile = models.ForeignKey( # e.g., The artist profile that was followed, or artist of new release
        'music.Artist',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications_about_artist_profile'
    )
    target_user_profile = models.ForeignKey( # e.g., The user profile that followed
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications_about_user_profile_actor' # Renamed related_name for clarity
    )
    target_conversation = models.ForeignKey(
        'chat.Conversation',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications_about'
    )
    target_order = models.ForeignKey( # For sales notifications for an artist
        'shop.Order',
        on_delete=models.SET_NULL, # Keep notification even if order is deleted
        null=True, blank=True,
        related_name='notifications_about'
    )
    # Could add more target fields for comments, likes, etc.

    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True) # Use default=timezone.now for flexibility

    # For Artist's Inbox: if true, this notification is intended for the artist's specific "activity" feed
    # (e.g., new follower, new sale).
    # If false, it's for the user's general notification feed (e.g., new release from followed artist, chat message).
    is_artist_channel = models.BooleanField(default=False, db_index=True,
        help_text="Is this notification for the artist's activity channel (sales, follows)?")


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['recipient', 'is_artist_channel', 'is_read', 'created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username} ({self.get_notification_type_display()}) at {self.created_at.strftime('%Y-%m-%d %H:%M')}"