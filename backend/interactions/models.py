from django.db import models
from django.conf import settings

class Follow(models.Model):
    """
    Represents a User following an Artist.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_set',
        help_text="The user who is following."
    )
    artist = models.ForeignKey(
        'music.Artist',
        on_delete=models.CASCADE,
        related_name='follower_set',
        help_text="The artist being followed."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artist') # A user can only follow an artist once
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'artist']),
        ]

    def __str__(self):
        return f"{self.user.username} follows {self.artist.name}"