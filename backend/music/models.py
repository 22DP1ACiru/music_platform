from django.db import models
from django.conf import settings # For AUTH_USER_MODEL
from django.utils import timezone # For release_date checks

# Define upload path functions
def artist_pic_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/artist_pics/<artist_id>/<filename>
    # Ensure instance.id exists. This might require saving the instance first in some cases,
    # but Django handles it during file upload.
    return f'artist_pics/{instance.id}/{filename}'

def cover_art_path(instance, filename):
    # MEDIA_ROOT/cover_art/<artist_name_slug>/<album_title_slug>/<filename>
    # Requires slugifying names - simplify path for now
    # TODO - use slugify for artist and album names
    return f'cover_art/{instance.artist.id}/{instance.id}/{filename}' # Simpler path using IDs

def track_audio_path(instance, filename):
    # MEDIA_ROOT/tracks/<artist_id>/<album_id>/<track_id>/<filename>
    return f'tracks/{instance.release.artist.id}/{instance.release.id}/{instance.id}/{filename}'

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Add slug if needed for URLs: slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Artist(models.Model):
    # Link to the User who controls this Artist profile
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='artist_profile'
    )
    name = models.CharField(max_length=200, unique=True, help_text="Artist or band name")
    bio = models.TextField(blank=True, null=True)
    artist_picture = models.ImageField(
        upload_to=artist_pic_path,
        null=True,
        blank=True
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    website_url = models.URLField(
        max_length=200,
        blank=True,
        null=True
    )


    def __str__(self):
        return self.name

class Release(models.Model):
    class ReleaseType(models.TextChoices):
        ALBUM = 'ALBUM', 'Album'
        EP = 'EP', 'EP'
        SINGLE = 'SINGLE', 'Single'

    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='releases')
    release_type = models.CharField(max_length=10, choices=ReleaseType.choices, default=ReleaseType.ALBUM)
    
    # Release date determines visibility if in future
    release_date = models.DateTimeField(default=timezone.now)
    cover_art = models.ImageField(upload_to=cover_art_path, null=True, blank=True)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    
    # Explicit published flag might be useful beyond just date check
    is_published = models.BooleanField(default=True, help_text="If unchecked, release is a draft.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_visible(self):
        """Checks if the release should be visible to regular users."""
        return self.is_published and self.release_date <= timezone.now()

    def __str__(self):
        return f"{self.title} ({self.get_release_type_display()}) by {self.artist.name}"

    class Meta:
        ordering = ['-release_date'] # Default order: newest first

class Track(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=255)
    # The actual audio file
    audio_file = models.FileField(upload_to=track_audio_path)
    track_number = models.PositiveIntegerField(null=True, blank=True, help_text="Order within the release")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name='tracks')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds (can be auto-populated)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):  
        return f"{self.title} from {self.release.title} by {self.release.artist.name})"

    class Meta:
         # Order by release, then track number
         ordering = ['release', 'track_number']

class Comment(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    timestamp_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Optional: time in track comment refers to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        ts = f" @ {self.timestamp_seconds}s" if self.timestamp_seconds is not None else ""
        return f"Comment by {self.user.username} on {self.track.title}{ts}"

    class Meta:
        ordering = ['created_at'] # Show oldest comments first

class Highlight(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='highlights')
    # Limit choices in admin forms to staff users
    highlighted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+') # '+' prevents reverse relation
    highlighted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Optional ordering for highlights display")

    def __str__(self):
        return f"Highlight for {self.release.title}"

    class Meta:
        ordering = ['-highlighted_at'] # Show newest highlights first by default