from django.db import models
from django.conf import settings

def playlist_cover_path(instance, filename):
    return f'playlist_covers/{instance.owner.id}/{instance.id}/{filename}'

class Playlist(models.Model):
    title = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    # The core relationship: links to many tracks
    tracks = models.ManyToManyField(
        'music.Track', # Avoid circular imports
        related_name='playlists',
        blank=True # A playlist can be empty initially
    )
    cover_art = models.ImageField(upload_to=playlist_cover_path, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True) # Allow private playlists
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.owner.username}"

    class Meta:
        ordering = ['-updated_at'] # Show recently updated playlists first