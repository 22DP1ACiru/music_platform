from django.db import models
from django.conf import settings # For AUTH_USER_MODEL
from django.utils import timezone # For release_date checks
from mutagen import File as MutagenFile # For audio file metadata
from mutagen import MutagenError
from django.core.exceptions import ValidationError # For GIF validation
from PIL import Image, UnidentifiedImageError # For GIF validation

# Define upload path functions
def artist_pic_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/artist_pics/<artist_id>/<filename>
    return f'artist_pics/{instance.user.id}/{filename}' # Assuming artist is saved first, or user.id is used if artist.id not yet available

def cover_art_path(instance, filename):
    # MEDIA_ROOT/cover_art/<artist_id>/<release_id>/<filename>
    # Instance ID might not be available on first save if path is determined before model is saved.
    # This could be an issue if cover_art_path is called before Release instance has an ID.
    # A common pattern is to save the model without the file first, then update with the file.
    # Or use a temporary path / signal to rename after save.
    # For simplicity now, assuming instance.id is available or will be handled by deferring file save.
    # If instance.id is None, this will cause an error or a literal "None" in the path.
    # This needs careful handling in production, possibly by saving the file after the instance gets an ID.
    artist_id_for_path = instance.artist.id if instance.artist else "unknown_artist"
    release_id_for_path = instance.id if instance.id else "new_release"
    return f'cover_art/{artist_id_for_path}/{release_id_for_path}/{filename}'


def track_audio_path(instance, filename):
    # MEDIA_ROOT/tracks/<artist_id>/<release_id>/<track_id>/<filename>
    # Similar to cover_art_path, instance.id might not be available on first save.
    artist_id_for_path = instance.release.artist.id if instance.release and instance.release.artist else "unknown_artist"
    release_id_for_path = instance.release.id if instance.release and instance.release.id else "unknown_release"
    track_id_for_path = instance.id if instance.id else "new_track"
    return f'tracks/{artist_id_for_path}/{release_id_for_path}/{track_id_for_path}/{filename}'

def validate_image_not_gif(value):
    """
    Validator for ImageField to disallow GIFs.
    Allows Pillow to first validate if it's a recognizable image.
    """
    try:
        value.seek(0)  # Go to the start of the file
        img = Image.open(value)
        # No need to call img.verify() if we just need the format.
        # verify() can be problematic as it might close the file or be destructive.
        image_format = img.format
        value.seek(0)  # Reset file pointer for Django to save it

        if image_format and image_format.upper() == 'GIF':
            raise ValidationError(
                "Animated GIFs are not allowed. Please use a static image format like JPG or PNG.",
                code='gif_not_allowed'
            )
    except UnidentifiedImageError:
        # This means Pillow cannot identify the image format.
        # Django's ImageField validation will also catch this.
        # We let Django's built-in validation raise the error for "not a valid image".
        pass
    except Exception as e:
        # Catch other potential errors during image processing.
        # Log this or handle as per requirements, but for now, let other validations proceed.
        # print(f"Unexpected error in image validator: {e}")
        # For a production system, you might want to raise a generic validation error here
        # or ensure Django's ImageField catches it.
        # To be safe, let's allow Django's ImageField to make the final call if our specific check fails unexpectedly.
        pass


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
        blank=True,
        validators=[validate_image_not_gif] # Can also apply here if desired
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
    cover_art = models.ImageField(
        upload_to=cover_art_path, 
        null=True, 
        blank=True,
        validators=[validate_image_not_gif] # Applied validator
    )
    
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
    
    genres = models.ManyToManyField(Genre, blank=True, related_name='tracks')
    
    duration_in_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds (auto-populated)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (from {self.release.title} by {self.release.artist.name})"

    def save(self, *args, **kwargs):
        is_new_instance = self.pk is None
        old_audio_file_name = None
        initial_duration = self.duration_in_seconds

        if not is_new_instance:
            try:
                original_track = Track.objects.get(pk=self.pk)
                if original_track.audio_file:
                    old_audio_file_name = original_track.audio_file.name
                # Keep initial_duration as what's currently on the instance being saved,
                # as it might have been changed before save() is called.
            except Track.DoesNotExist:
                is_new_instance = True 

        # Save the model instance and file to storage first.
        super().save(*args, **kwargs)

        recalculate_duration = False
        if self.audio_file:
            current_audio_file_name = self.audio_file.name
            if is_new_instance:
                recalculate_duration = True
            elif old_audio_file_name != current_audio_file_name: # File changed
                recalculate_duration = True
            elif initial_duration is None: # Duration was missing, and file exists
                recalculate_duration = True
        
        if recalculate_duration:
            new_duration_value = None
            try:
                self.audio_file.seek(0)
                audio_metadata = MutagenFile(self.audio_file) # Pass FieldFile
                if audio_metadata and audio_metadata.info:
                    new_duration_value = round(audio_metadata.info.length)
                self.audio_file.seek(0) 
            except MutagenError as e:
                print(f"Mutagen error for '{self.title}': {e}")
            except Exception as e:
                print(f"Unexpected error reading audio for '{self.title}': {e}")

            # Only re-save if the calculated duration is different from the current one,
            # or if the current one was None and we calculated a new one.
            if self.duration_in_seconds != new_duration_value:
                self.duration_in_seconds = new_duration_value
                super().save(update_fields=['duration_in_seconds'])
                print(f"Duration for '{self.title}' updated to: {self.duration_in_seconds}s")
            elif new_duration_value is None and self.duration_in_seconds is not None:
                # If calculation failed but a duration was previously set, clear it
                self.duration_in_seconds = None
                super().save(update_fields=['duration_in_seconds'])
                print(f"Duration for '{self.title}' cleared as it could not be recalculated.")


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