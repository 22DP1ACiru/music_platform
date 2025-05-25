from django.db import models
from django.conf import settings # For AUTH_USER_MODEL
from django.utils import timezone # For release_date checks
from mutagen import File as MutagenFile # For audio file metadata
from mutagen import MutagenError
from django.core.exceptions import ValidationError # For GIF validation
# from PIL import Image, UnidentifiedImageError # No longer needed here, use utility
import os # For file deletion (though utility handles it)
from django.db.models.signals import pre_save, post_delete # For file deletion signals
from django.dispatch import receiver # For file deletion signals
import logging # Import Python's logging module

# Import from the new utility module
from vaultwave.utils import (
    delete_file_if_changed,
    delete_file_on_instance_delete,
    validate_image_not_gif_utility
)

# Get an instance of a logger
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger

# Define upload path functions
def artist_pic_path(instance, filename):
    artist_id_for_path = instance.user.id if instance.user else "unknown_user"
    return f'artist_pics/{artist_id_for_path}/{filename}'

def cover_art_path(instance, filename):
    artist_id_for_path = instance.artist.id if instance.artist else "unknown_artist"
    release_id_for_path = instance.id if instance.id else "new_release" # Use placeholder if ID not yet set
    return f'cover_art/{artist_id_for_path}/{release_id_for_path}/{filename}'

def track_audio_path(instance, filename):
    artist_id_for_path = instance.release.artist.id if instance.release and instance.release.artist else "unknown_artist"
    release_id_for_path = instance.release.id if instance.release and instance.release.id else "unknown_release"
    # The track_id_for_path will use "new_track_temp_id" if the instance.id is not yet set.
    # Django's file handling should manage renaming the file/path if the ID-dependent part changes after the initial save.
    track_id_for_path = instance.id if instance.id else "new_track_temp_id"
    return f'tracks/{artist_id_for_path}/{release_id_for_path}/{track_id_for_path}/{filename}'

# Removed local validate_image_not_gif, will use validate_image_not_gif_utility directly in fields

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
        validators=[validate_image_not_gif_utility] # Use utility validator
    )
    location = models.CharField(max_length=100, blank=True, null=True)
    website_url = models.URLField(max_length=200, blank=True, null=True)
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
        validators=[validate_image_not_gif_utility] # Use utility validator
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

    # To store the original audio file name to detect changes
    _original_audio_file_name_on_load = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store the original file name when the instance is loaded from DB
        if self.pk and self.audio_file and hasattr(self.audio_file, 'name'):
            self._original_audio_file_name_on_load = self.audio_file.name
        else:
            self._original_audio_file_name_on_load = None

    def __str__(self):
        return f"{self.title} (from {self.release.title} by {self.release.artist.name})"

    def save(self, *args, **kwargs):
        logger.info(f"Track.save() started for track PK '{self.pk}' - Title: '{self.title}'")
        
        is_new_instance = self.pk is None
        
        # Determine if the audio file has changed or if it's a new instance with a file
        file_changed = False
        current_audio_file_name = self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else None

        if current_audio_file_name:
            if is_new_instance:
                file_changed = True
                logger.info(f"Track PK '{self.pk}': New instance with audio file '{current_audio_file_name}'.")
            elif self._original_audio_file_name_on_load != current_audio_file_name:
                file_changed = True
                logger.info(f"Track PK '{self.pk}': Audio file changed from '{self._original_audio_file_name_on_load}' to '{current_audio_file_name}'.")
        elif not current_audio_file_name and self._original_audio_file_name_on_load:
            file_changed = True # File is being cleared
            logger.info(f"Track PK '{self.pk}': Audio file '{self._original_audio_file_name_on_load}' is being cleared.")

        # Save the model instance and the file to storage first.
        super().save(*args, **kwargs)
        logger.info(f"Track PK '{self.pk}': super().save() completed. Current audio_file.name from object: '{self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else 'No audio file'}'.")

        # After super().save(), self.audio_file.name should reflect the final path.
        # Update our tracker for the next save cycle if the instance is kept in memory.
        current_audio_file_name_in_storage = self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else None
        self._original_audio_file_name_on_load = current_audio_file_name_in_storage # Update for subsequent saves if object persists
        
        new_duration = None
        should_update_duration_in_db = False

        if not current_audio_file_name_in_storage: # If audio file is None or empty string after save
            if self.duration_in_seconds is not None:
                logger.info(f"Track PK '{self.pk}': Audio file is not present in storage. Clearing duration from {self.duration_in_seconds}s to None.")
                self.duration_in_seconds = None
                should_update_duration_in_db = True
            else:
                logger.info(f"Track PK '{self.pk}': Audio file is not present and duration is already None. No change.")
        elif file_changed or self.duration_in_seconds is None:
            logger.info(f"Track PK '{self.pk}': Attempting duration calculation. file_changed={file_changed}, current_duration={self.duration_in_seconds}s.")
            try:
                if self.audio_file.storage.exists(current_audio_file_name_in_storage):
                    logger.info(f"Track PK '{self.pk}': File '{current_audio_file_name_in_storage}' exists in storage. Opening with mutagen...")
                    with self.audio_file.storage.open(current_audio_file_name_in_storage, 'rb') as f:
                        audio_metadata_obj = MutagenFile(f) 
                        
                        if audio_metadata_obj is None:
                            logger.warning(f"Track PK '{self.pk}': MutagenFile(f) returned None for '{current_audio_file_name_in_storage}'. File type not recognized or error during init.")
                        elif not hasattr(audio_metadata_obj, 'info'):
                            logger.warning(f"Track PK '{self.pk}': Mutagen object for '{current_audio_file_name_in_storage}' (type: {type(audio_metadata_obj)}) has no 'info' attribute.")
                        elif audio_metadata_obj.info is None:
                            logger.warning(f"Track PK '{self.pk}': Mutagen 'info' attribute is None for '{current_audio_file_name_in_storage}' (type: {type(audio_metadata_obj)}).")
                        elif not hasattr(audio_metadata_obj.info, 'length'):
                            logger.warning(f"Track PK '{self.pk}': Mutagen 'info' object for '{current_audio_file_name_in_storage}' (type: {type(audio_metadata_obj.info)}) has no 'length' attribute.")
                        elif audio_metadata_obj.info.length > 0:
                            new_duration = round(audio_metadata_obj.info.length)
                            logger.info(f"Track PK '{self.pk}': Mutagen successfully read duration: {new_duration}s from '{current_audio_file_name_in_storage}'.")
                        else: # length <= 0
                            logger.warning(f"Track PK '{self.pk}': Mutagen extracted zero or negative duration ({audio_metadata_obj.info.length}s) for '{current_audio_file_name_in_storage}'. Type: {type(audio_metadata_obj)}")
                else:
                    logger.error(f"Track PK '{self.pk}': Audio file '{current_audio_file_name_in_storage}' NOT FOUND in storage for duration calculation despite self.audio_file object existing.")
            except MutagenError as e:
                logger.error(f"Track PK '{self.pk}': MutagenError for '{self.title}' reading '{current_audio_file_name_in_storage}': {e}", exc_info=True)
            except FileNotFoundError as e: 
                logger.error(f"Track PK '{self.pk}': FileNotFoundError for '{current_audio_file_name_in_storage}' when opening with storage: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Track PK '{self.pk}': Unexpected error reading audio for '{self.title}' from '{current_audio_file_name_in_storage}': {e}", exc_info=True)

            if self.duration_in_seconds != new_duration:
                logger.info(f"Track PK '{self.pk}': Duration will be updated from {self.duration_in_seconds}s to {new_duration}s.")
                self.duration_in_seconds = new_duration
                should_update_duration_in_db = True
            else:
                logger.info(f"Track PK '{self.pk}': Calculated duration ({new_duration}s) is same as current ({self.duration_in_seconds}s). No DB update for duration needed.")
        else:
            logger.info(f"Track PK '{self.pk}': Conditions for duration recalculation not met (file not changed and duration already exists). Duration remains {self.duration_in_seconds}s.")
        
        if should_update_duration_in_db:
            logger.info(f"Track PK '{self.pk}': Calling super().save(update_fields=['duration_in_seconds']) to save duration: {self.duration_in_seconds}s.")
            # Save again, but only the duration field to avoid recursion and unnecessary signal triggers for other fields.
            super().save(update_fields=['duration_in_seconds']) 
        
        logger.info(f"Track.save() finished for track PK '{self.pk}'.")

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

# --- Signal Receivers for Deleting Old Files ---
# Use the imported utility functions

@receiver(pre_save, sender=Artist)
def artist_pre_save_delete_old_picture(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'artist_picture')

@receiver(pre_save, sender=Release)
def release_pre_save_delete_old_cover(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'cover_art')

@receiver(pre_save, sender=Track)
def track_pre_save_delete_old_audio(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'audio_file')


@receiver(post_delete, sender=Artist)
def artist_post_delete_cleanup_picture(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.artist_picture)

@receiver(post_delete, sender=Release)
def release_post_delete_cleanup_cover(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.cover_art)

@receiver(post_delete, sender=Track)
def track_post_delete_cleanup_audio(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.audio_file)