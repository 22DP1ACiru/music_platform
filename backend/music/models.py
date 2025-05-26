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
from decimal import Decimal # For default price
import uuid # For unique identifiers for generated downloads

# Import from the new utility module
from vaultwave.utils import (
    delete_file_if_changed,
    delete_file_on_instance_delete,
    validate_image_not_gif_utility
)
# Import CURRENCY_CHOICES from the new constants.py
from vaultwave.constants import CURRENCY_CHOICES


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
    track_id_for_path = instance.id if instance.id else "new_track_temp_id"
    return f'tracks/{artist_id_for_path}/{release_id_for_path}/{track_id_for_path}/{filename}'

def release_download_path(instance, filename):
    artist_id_for_path = instance.artist.id if instance.artist else "unknown_artist"
    release_id_for_path = instance.id if instance.id else "new_release"
    return f'release_downloads/{artist_id_for_path}/{release_id_for_path}/{filename}'

def generated_release_download_path(instance, filename):
    # instance is GeneratedDownload
    release_id_for_path = instance.release.id if instance.release else "unknown_release"
    # Use instance.id (GeneratedDownload ID) or a UUID for uniqueness to avoid collisions
    # filename will likely be constructed like "release_title_format.zip"
    # Path: generated_downloads/release_<release_id>/<uuid_or_generated_id>_<filename>
    unique_id = instance.unique_identifier or uuid.uuid4()
    return f'generated_downloads/release_{release_id_for_path}/{unique_id}_{filename}'


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

    class PricingModel(models.TextChoices):
        FREE = 'FREE', 'Free'
        PAID = 'PAID', 'Paid'
        NAME_YOUR_PRICE = 'NYP', 'Name Your Price'

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
    
    # Shop related fields for downloads (musician-uploaded)
    download_file = models.FileField(
        upload_to=release_download_path, 
        null=True, 
        blank=True, 
        help_text="The downloadable file for the release (e.g., ZIP archive) uploaded by the musician."
    )
    pricing_model = models.CharField(
        max_length=10, 
        choices=PricingModel.choices, 
        default=PricingModel.PAID, 
        help_text="Choose the pricing model for downloads."
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Price for 'Paid' model. Leave blank if not 'Paid'."
    )
    currency = models.CharField(
        max_length=3, 
        choices=CURRENCY_CHOICES, 
        null=True, 
        blank=True, 
        default='USD', 
        help_text="Currency for 'Paid' model."
    )
    minimum_price_nyp = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        default=Decimal('0.00'), 
        help_text="Minimum price for 'Name Your Price' model. Can be 0."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.pricing_model == self.PricingModel.PAID:
            if self.price is None or self.price < Decimal('0.00'):
                raise ValidationError({'price': "Price must be set and cannot be negative for 'Paid' model."})
            if not self.currency:
                raise ValidationError({'currency': "Currency must be set for 'Paid' model."})
        else:
            pass # No specific price validation if not 'PAID'
        
        if self.pricing_model == self.PricingModel.NAME_YOUR_PRICE:
            if self.minimum_price_nyp is not None and self.minimum_price_nyp < Decimal('0.00'):
                raise ValidationError({'minimum_price_nyp': "Minimum 'Name Your Price' cannot be negative."})
        
        # This validation regarding download_file is for musician-uploaded files.
        # For on-demand generated files, this model won't store the file directly.
        if self.download_file and self.pricing_model not in [self.PricingModel.FREE, self.PricingModel.PAID, self.PricingModel.NAME_YOUR_PRICE]:
             raise ValidationError("Download file provided but pricing model is unclear or not set for downloads.")
        
        if self.download_file and not self.pricing_model:
             raise ValidationError({'pricing_model': "A pricing model must be selected if a download file is provided."})


    def save(self, *args, **kwargs):
        # Nullify price/min_price if pricing model doesn't match
        if self.pricing_model != self.PricingModel.PAID:
            self.price = None
            # Keep currency as it might be used for NYP or default display
        if self.pricing_model != self.PricingModel.NAME_YOUR_PRICE:
            self.minimum_price_nyp = None
        
        self.full_clean() 
        super().save(*args, **kwargs)

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

    _original_audio_file_name_on_load = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk and self.audio_file and hasattr(self.audio_file, 'name'):
            self._original_audio_file_name_on_load = self.audio_file.name
        else:
            self._original_audio_file_name_on_load = None

    def __str__(self):
        return f"{self.title} (from {self.release.title} by {self.release.artist.name})"

    def save(self, *args, **kwargs):
        logger.info(f"Track.save() started for track PK '{self.pk}' - Title: '{self.title}'")
        
        is_new_instance = self.pk is None
        
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
            # File is being cleared
            file_changed = True 
            logger.info(f"Track PK '{self.pk}': Audio file '{self._original_audio_file_name_on_load}' is being cleared.")

        # Save the model first, especially if it's a new instance or file path depends on PK
        super().save(*args, **kwargs)
        logger.info(f"Track PK '{self.pk}': super().save() completed. Current audio_file.name from object: '{self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else 'No audio file'}'.")

        # Update the original file name tracker *after* save, as save might rename the file
        current_audio_file_name_in_storage = self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else None
        self._original_audio_file_name_on_load = current_audio_file_name_in_storage 
        
        new_duration = None
        should_update_duration_in_db = False

        # If file was cleared or does not exist in storage
        if not current_audio_file_name_in_storage: 
            if self.duration_in_seconds is not None:
                logger.info(f"Track PK '{self.pk}': Audio file is not present in storage. Clearing duration from {self.duration_in_seconds}s to None.")
                self.duration_in_seconds = None
                should_update_duration_in_db = True
            else:
                logger.info(f"Track PK '{self.pk}': Audio file is not present and duration is already None. No change.")
        # If file changed, or if duration was not previously set (e.g., new file or previous error)
        elif file_changed or self.duration_in_seconds is None:
            logger.info(f"Track PK '{self.pk}': Attempting duration calculation. file_changed={file_changed}, current_duration={self.duration_in_seconds}s.")
            try:
                # Check if file exists in storage *before* trying to open
                if self.audio_file.storage.exists(current_audio_file_name_in_storage):
                    logger.info(f"Track PK '{self.pk}': File '{current_audio_file_name_in_storage}' exists in storage. Opening with mutagen...")
                    with self.audio_file.storage.open(current_audio_file_name_in_storage, 'rb') as f:
                        audio_metadata_obj = MutagenFile(f) # Pass the file object directly
                        
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
                        else: 
                            logger.warning(f"Track PK '{self.pk}': Mutagen extracted zero or negative duration ({audio_metadata_obj.info.length}s) for '{current_audio_file_name_in_storage}'. Type: {type(audio_metadata_obj)}")
                else:
                    logger.error(f"Track PK '{self.pk}': Audio file '{current_audio_file_name_in_storage}' NOT FOUND in storage for duration calculation despite self.audio_file object existing.")
            except MutagenError as e:
                logger.error(f"Track PK '{self.pk}': MutagenError for '{self.title}' reading '{current_audio_file_name_in_storage}': {e}", exc_info=True)
            except FileNotFoundError as e: # Should be caught by storage.exists, but as a fallback
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
            # Re-fetch the instance to avoid saving a stale version if other fields were changed elsewhere
            # This is a known issue with calling save() multiple times in one method if not careful.
            # However, update_fields should limit the scope.
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


# --- Model for On-Demand Generated Downloads ---
class GeneratedDownload(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'
        EXPIRED = 'EXPIRED', 'Expired'

    class DownloadFormatChoices(models.TextChoices):
        # Define based on what your Celery task will support
        MP3_320 = 'MP3_320', 'MP3 (320kbps)'
        MP3_192 = 'MP3_192', 'MP3 (192kbps)'
        FLAC = 'FLAC', 'FLAC'
        WAV = 'WAV', 'WAV (Original Quality)' # Or just 'Original'
        # ORIGINAL = 'ORIGINAL', 'Original Uploaded Format' # If you want to offer this option directly for individual tracks too
    
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='generated_downloads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_downloads')
    requested_format = models.CharField(max_length=20, choices=DownloadFormatChoices.choices)
    # quality_options = models.JSONField(null=True, blank=True) # For more granular control if needed, e.g., VBR settings for MP3

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # Using FileField to store the generated ZIP. This benefits from Django's storage system.
    download_file = models.FileField(
        upload_to=generated_release_download_path, 
        null=True, 
        blank=True, 
        help_text="The generated ZIP file for download."
    )
    unique_identifier = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Unique ID for download URL")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this download link/file expires.")
    failure_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Download for {self.release.title} ({self.get_requested_format_display()}) by {self.user.username} - {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expires_at']),
        ]


# --- Signal Receivers for Deleting Old Files ---
@receiver(pre_save, sender=Artist)
def artist_pre_save_delete_old_picture(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'artist_picture')

@receiver(pre_save, sender=Release)
def release_pre_save_delete_old_cover(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'cover_art')
    delete_file_if_changed(sender, instance, 'download_file') 

@receiver(pre_save, sender=Track)
def track_pre_save_delete_old_audio(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'audio_file')

@receiver(pre_save, sender=GeneratedDownload) # Signal for new model
def generated_download_pre_save_delete_old_file(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'download_file')


@receiver(post_delete, sender=Artist)
def artist_post_delete_cleanup_picture(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.artist_picture)

@receiver(post_delete, sender=Release)
def release_post_delete_cleanup_cover_and_download(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.cover_art)
    delete_file_on_instance_delete(instance.download_file) # Musician-uploaded

@receiver(post_delete, sender=Track)
def track_post_delete_cleanup_audio(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.audio_file)

@receiver(post_delete, sender=GeneratedDownload) # Signal for new model
def generated_download_post_delete_cleanup_file(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.download_file)