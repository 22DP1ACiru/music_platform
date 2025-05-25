from django.db import models
from django.conf import settings # For AUTH_USER_MODEL
from django.utils import timezone # For release_date checks
from mutagen import File as MutagenFile # For audio file metadata
from mutagen import MutagenError

# Define upload path functions
def artist_pic_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/artist_pics/<artist_id>/<filename>
    return f'artist_pics/{instance.user.id}/{filename}' # Assuming artist is saved first, or user.id is used if artist.id not yet available

def cover_art_path(instance, filename):
    # MEDIA_ROOT/cover_art/<artist_id>/<release_id>/<filename>
    return f'cover_art/{instance.artist.id}/{instance.id}/{filename}'

def track_audio_path(instance, filename):
    # MEDIA_ROOT/tracks/<artist_id>/<release_id>/<track_id>/<filename>
    return f'tracks/{instance.release.artist.id}/{instance.release.id}/{instance.id}/{filename}'

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Add slug if needed for URLs: slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Artist(models.Model):
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
    release_date = models.DateTimeField(default=timezone.now)
    cover_art = models.ImageField(upload_to=cover_art_path, null=True, blank=True)
    
    # Changed from ForeignKey to ManyToManyField
    genres = models.ManyToManyField(Genre, blank=True, related_name='releases')
    
    is_published = models.BooleanField(default=True, help_text="If unchecked, release is a draft.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_visible(self):
        return self.is_published and self.release_date <= timezone.now()

    def __str__(self):
        return f"{self.title} ({self.get_release_type_display()}) by {self.artist.name}"

    class Meta:
        ordering = ['-release_date']

class Track(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to=track_audio_path)
    track_number = models.PositiveIntegerField(null=True, blank=True, help_text="Order within the release")
    
    # Changed from ForeignKey to ManyToManyField
    genres = models.ManyToManyField(Genre, blank=True, related_name='tracks')
    
    duration_in_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds (auto-populated)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (from {self.release.title} by {self.release.artist.name})"

    def save(self, *args, **kwargs):
        get_duration = False
        if self.pk:
            try:
                old_instance = Track.objects.get(pk=self.pk)
                if old_instance.audio_file != self.audio_file or self.duration_in_seconds is None:
                    get_duration = True
            except Track.DoesNotExist:
                get_duration = True
        elif self.audio_file:
             get_duration = True

        if get_duration and self.audio_file:
            try:
                self.audio_file.seek(0)
                audio = MutagenFile(self.audio_file)
                if audio and audio.info:
                    self.duration_in_seconds = round(audio.info.length)
                    print(f"Calculated duration for {self.title}: {self.duration_in_seconds}s")
                else:
                     self.duration_in_seconds = None
                     print(f"Could not get audio info for {self.title}")
                self.audio_file.seek(0)
            except MutagenError as e:
                print(f"Mutagen error reading {self.title}: {e}")
                self.duration_in_seconds = None
            except Exception as e:
                print(f"Error reading audio file {self.title}: {e}")
                self.duration_in_seconds = None

        super().save(*args, **kwargs)

    class Meta:
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
        ordering = ['created_at']

class Highlight(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='highlights')
    highlighted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    highlighted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Optional ordering for highlights display")

    def __str__(self):
        return f"Highlight for {self.release.title}"

    class Meta:
        ordering = ['-highlighted_at']