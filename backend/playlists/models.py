from django.db import models
from django.conf import settings
from django.db.models.signals import pre_save, post_delete # Import signals
from django.dispatch import receiver # Import receiver
from vaultwave.utils import delete_file_if_changed, delete_file_on_instance_delete # Import utils

def playlist_cover_path(instance, filename):
    owner_id_for_path = instance.owner.id if instance.owner_id else "unknown_owner"
    playlist_id_for_path = instance.id if instance.id else "new_playlist"
    return f'playlist_covers/{owner_id_for_path}/{playlist_id_for_path}/{filename}'

class Playlist(models.Model):
    title = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    tracks = models.ManyToManyField(
        'music.Track', 
        related_name='playlists',
        blank=True 
    )
    cover_art = models.ImageField(upload_to=playlist_cover_path, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.owner.username}"

    class Meta:
        ordering = ['-updated_at']

# --- Signal Receivers for Playlist ---
@receiver(pre_save, sender=Playlist)
def playlist_pre_save_delete_old_cover(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'cover_art')

@receiver(post_delete, sender=Playlist)
def playlist_post_delete_cleanup_cover(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.cover_art)