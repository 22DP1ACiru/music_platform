from django.db import models
from django.conf import settings 
from django.utils import timezone 
from mutagen import File as MutagenFile 
from mutagen import MutagenError
from django.core.exceptions import ValidationError 
import os 
from django.db.models.signals import pre_save, post_delete 
from django.dispatch import receiver 
import logging 
from decimal import Decimal 
import uuid 
import subprocess 
import json 

from vaultwave.utils import (
    delete_file_if_changed,
    delete_file_on_instance_delete,
    validate_image_not_gif_utility
)
from vaultwave.constants import CURRENCY_CHOICES


logger = logging.getLogger(__name__) 

def artist_pic_path(instance, filename):
    artist_id_for_path = instance.user.id if instance.user else "unknown_user"
    return f'artist_pics/{artist_id_for_path}/{filename}'

def cover_art_path(instance, filename):
    artist_id_for_path = instance.artist.id if instance.artist else "unknown_artist"
    release_id_for_path = instance.id if instance.id else "new_release" 
    return f'cover_art/{artist_id_for_path}/{release_id_for_path}/{filename}'

def track_audio_path(instance, filename):
    artist_id_for_path = instance.release.artist_id if instance.release and instance.release.artist_id else "unknown_artist"
    release_id_for_path = instance.release_id if instance.release_id else "unknown_release"
    
    _, ext = os.path.splitext(filename)
    clean_ext = ext.lstrip('.').lower()
    if not clean_ext: 
        clean_ext = 'mp3' 
        
    unique_filename = f"{uuid.uuid4()}.{clean_ext}"
    track_id_component = instance.id if instance.id else "new_track_temp"
    return f'tracks/{artist_id_for_path}/{release_id_for_path}/{track_id_component}/{unique_filename}'


def generated_release_download_path(instance, filename):
    release_id_for_path = instance.release.id if instance.release else "unknown_release"
    unique_id = instance.unique_identifier or uuid.uuid4()
    return f'generated_downloads/release_{release_id_for_path}/{unique_id}_{filename}'

def highlight_custom_image_path(instance, filename):
    highlight_id_for_path = instance.id if instance.id else "new_highlight"
    return f'highlights/{highlight_id_for_path}/{filename}'


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
        validators=[validate_image_not_gif_utility] 
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
        validators=[validate_image_not_gif_utility] 
    )
    genres = models.ManyToManyField(Genre, blank=True, related_name='releases')
    is_published = models.BooleanField(default=True, help_text="If unchecked, release is a draft.")
    
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
    
    listen_count = models.PositiveIntegerField(default=0, help_text="Aggregated significant listens for this release.")


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.pricing_model == self.PricingModel.PAID:
            if self.price is None or self.price < Decimal('0.00'):
                raise ValidationError({'price': "Price must be set and cannot be negative for 'Paid' model."})
            if not self.currency:
                raise ValidationError({'currency': "Currency must be set for 'Paid' model."})
        
        if self.pricing_model == self.PricingModel.NAME_YOUR_PRICE:
            if self.minimum_price_nyp is not None and self.minimum_price_nyp < Decimal('0.00'):
                raise ValidationError({'minimum_price_nyp': "Minimum 'Name Your Price' cannot be negative."})
        

    def save(self, *args, **kwargs):
        if self.pricing_model != self.PricingModel.PAID:
            self.price = None
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
    audio_file = models.FileField(upload_to=track_audio_path, max_length=255) 
    track_number = models.PositiveIntegerField(null=True, blank=True, help_text="Order within the release")
    genres = models.ManyToManyField(Genre, blank=True, related_name='tracks')
    
    duration_in_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds (auto-populated)")
    codec_name = models.CharField(max_length=50, blank=True, null=True, help_text="Audio codec (e.g., mp3, flac, pcm_s16le)")
    bit_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Bit rate in kbit/s (e.g., 320, 1411)")
    sample_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Sample rate in Hz (e.g., 44100, 48000)")
    channels = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Number of audio channels (e.g., 1 for mono, 2 for stereo)")
    is_lossless = models.BooleanField(null=True, blank=True, help_text="True if the original uploaded format is lossless")
    
    listen_count = models.PositiveIntegerField(default=0, help_text="Aggregated significant listens for this track.")

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

    def extract_audio_metadata(self):
        if not self.audio_file or not self.audio_file.name:
            logger.warning(f"Track {self.id or self.title}: No audio file to extract metadata from.")
            return False

        if not self.audio_file.storage.exists(self.audio_file.name):
            logger.error(f"Track {self.id or self.title}: Audio file {self.audio_file.name} not found in storage for metadata extraction.")
            return False
        
        file_path = self.audio_file.path 
        probe_data = {} 
        audio_stream = None 

        try:
            ffprobe_cmd = [
                'ffprobe', '-v', 'error', '-print_format', 'json',
                '-show_streams', '-show_format', file_path
            ]
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)

            if 'streams' in probe_data:
                for stream in probe_data['streams']:
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
            
            if audio_stream:
                self.codec_name = audio_stream.get('codec_name')
                br_str = audio_stream.get('bit_rate') or probe_data.get('format', {}).get('bit_rate')
                if br_str: self.bit_rate = int(int(br_str) / 1000)
                else: self.bit_rate = None
                self.sample_rate = int(audio_stream.get('sample_rate', 0)) if audio_stream.get('sample_rate') else None
                self.channels = audio_stream.get('channels')
                
                lossless_codecs = [
                    'flac', 'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 
                    'pcm_f32le', 'pcm_f64le', 
                    'alac', 'ape', 'wavpack', 'shorten', 'dsd', 'truehd', 'dts-hd' 
                ]
                self.is_lossless = self.codec_name in lossless_codecs if self.codec_name else None
                logger.info(f"Track {self.id or self.title}: ffprobe - Codec: {self.codec_name}, Bitrate: {self.bit_rate}kbps, SampleRate: {self.sample_rate}Hz, Channels: {self.channels}, Lossless: {self.is_lossless}")
            else:
                logger.warning(f"Track {self.id or self.title}: No audio stream by ffprobe in {self.audio_file.name}.")
                self.codec_name = None; self.bit_rate = None; self.sample_rate = None; self.channels = None; self.is_lossless = None;
        except subprocess.CalledProcessError as e:
            logger.error(f"Track {self.id or self.title}: ffprobe error for {self.audio_file.name}: {e.stderr}")
            self.codec_name = None; self.bit_rate = None; self.sample_rate = None; self.channels = None; self.is_lossless = None;
        except FileNotFoundError:
            logger.error(f"Track {self.id or self.title}: ffprobe not found.")
            return False 
        except json.JSONDecodeError:
            logger.error(f"Track {self.id or self.title}: Failed to parse ffprobe JSON for {self.audio_file.name}.")
        except Exception as e: 
            logger.error(f"Track {self.id or self.title}: Unexpected ffprobe error for {self.audio_file.name}: {e}")


        new_duration = None
        try:
            with self.audio_file.storage.open(self.audio_file.name, 'rb') as f:
                audio_metadata_obj = MutagenFile(f)
                if audio_metadata_obj and hasattr(audio_metadata_obj, 'info') and audio_metadata_obj.info and hasattr(audio_metadata_obj.info, 'length') and audio_metadata_obj.info.length > 0:
                    new_duration = round(audio_metadata_obj.info.length)
                    logger.info(f"Track {self.id or self.title}: Mutagen duration: {new_duration}s")
                else: 
                    if audio_stream and 'duration' in audio_stream:
                        duration_str = audio_stream.get('duration')
                        if duration_str: new_duration = round(float(duration_str))
                        logger.info(f"Track {self.id or self.title}: ffprobe stream duration: {new_duration}s (mutagen failed/no length).")
                    elif 'format' in probe_data and 'duration' in probe_data['format']:
                        duration_str = probe_data['format'].get('duration')
                        if duration_str: new_duration = round(float(duration_str))
                        logger.info(f"Track {self.id or self.title}: ffprobe format duration: {new_duration}s (mutagen failed/no length).")
                    else:
                         logger.warning(f"Track {self.id or self.title}: Mutagen & ffprobe couldn't extract duration from {self.audio_file.name}.")
        except MutagenError as e: 
            logger.error(f"Track {self.id or self.title}: MutagenError reading duration for {self.audio_file.name}: {e}")
        except Exception as e: 
            logger.error(f"Track {self.id or self.title}: Error reading for duration with Mutagen/ffprobe fallback for {self.audio_file.name}: {e}")


        if self.duration_in_seconds != new_duration:
            self.duration_in_seconds = new_duration
            return True 
        return True 

    def save(self, *args, **kwargs):
        logger.info(f"Track.save() started for track PK '{self.pk}' - Title: '{self.title}'")
        is_new_instance = self.pk is None
        file_changed = False
        current_audio_file_name = self.audio_file.name if self.audio_file and hasattr(self.audio_file, 'name') else None

        if current_audio_file_name:
            if is_new_instance or self._original_audio_file_name_on_load != current_audio_file_name:
                file_changed = True
        elif not current_audio_file_name and self._original_audio_file_name_on_load: 
            file_changed = True 

        if file_changed and not current_audio_file_name: 
            self.duration_in_seconds = None; self.codec_name = None; self.bit_rate = None
            self.sample_rate = None; self.channels = None; self.is_lossless = None
            logger.info(f"Track PK '{self.pk}': File cleared, metadata reset.")
            super().save(*args, **kwargs) 
            self._original_audio_file_name_on_load = None 
            logger.info(f"Track.save() finished early for cleared file on track PK '{self.pk}'.")
            return
        
        if not is_new_instance and not file_changed:
             super().save(*args, **kwargs)
        else: 
            super().save(*args, **kwargs) 


        self._original_audio_file_name_on_load = self.audio_file.name if self.audio_file else None

        metadata_fields_to_update = []
        
        if file_changed and self.audio_file and self.audio_file.name:
            logger.info(f"Track PK '{self.pk}': File changed to '{self.audio_file.name}'. Extracting metadata.")
            
            old_metadata = {
                'duration_in_seconds': self.duration_in_seconds, 'codec_name': self.codec_name,
                'bit_rate': self.bit_rate, 'sample_rate': self.sample_rate,
                'channels': self.channels, 'is_lossless': self.is_lossless
            }
            self.extract_audio_metadata() 

            for field_name, old_value in old_metadata.items():
                if getattr(self, field_name) != old_value:
                    metadata_fields_to_update.append(field_name)
            
            if metadata_fields_to_update:
                logger.info(f"Track PK '{self.pk}': Metadata changed. Fields: {metadata_fields_to_update}. Saving metadata.")
            else:
                logger.info(f"Track PK '{self.pk}': Metadata extracted but no changes detected to metadata fields.")

        elif is_new_instance and self.audio_file and self.audio_file.name and self.codec_name is None: 
            logger.info(f"Track PK '{self.pk}': New instance, metadata not yet set. Extracting and saving metadata.")
            self.extract_audio_metadata() 
            metadata_fields_to_update = ['duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless']
            
        if metadata_fields_to_update:
            super().save(update_fields=metadata_fields_to_update)
            
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
    
    title = models.CharField(
        max_length=70, 
        blank=True, 
        help_text="Optional: Highlight title (max 70 chars). Defaults to release title."
    )
    subtitle = models.CharField(
        max_length=64, 
        blank=True,
        help_text="Optional: Subtitle for the highlight (max 64 chars)."
    )
    description = models.TextField(
        max_length=255, 
        blank=True, 
        help_text="Optional: Description for the highlight (max 255 chars)."
    )
    custom_carousel_image = models.ImageField(
        upload_to=highlight_custom_image_path, 
        null=True, 
        blank=True,
        validators=[validate_image_not_gif_utility],
        help_text="Optional: Custom image for carousel. Defaults to release cover art."
    )

    display_start_datetime = models.DateTimeField(default=timezone.now,
                                                help_text="When this highlight should start being displayed.")
    display_end_datetime = models.DateTimeField(null=True, blank=True,
                                              help_text="Optional: When this highlight should stop being displayed. Leave blank for indefinite.")
    
    is_active = models.BooleanField(default=True, help_text="Manually activate or deactivate this highlight.")
    order = models.PositiveIntegerField(
        default=0, 
        help_text="Order for display (e.g., 0 is first). Must be unique.", # Updated help_text
        unique=True # Enforce uniqueness at the database level
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_highlights',
        help_text="Admin/Staff user who created this highlight."
    )
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        effective_title = self.get_effective_title()
        return f"Highlight: {effective_title} (Order: {self.order})"

    def get_effective_title(self):
        return self.title or self.release.title 

    def get_effective_image_url(self):
        if self.custom_carousel_image and hasattr(self.custom_carousel_image, 'url'):
            return self.custom_carousel_image.url
        if self.release.cover_art and hasattr(self.release.cover_art, 'url'):
            return self.release.cover_art.url
        return None

    class Meta:
        ordering = ['order', '-display_start_datetime', '-created_at']

class GeneratedDownload(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'
        EXPIRED = 'EXPIRED', 'Expired'

    class DownloadFormatChoices(models.TextChoices):
        MP3_320 = 'MP3_320', 'MP3 (320kbps)'
        MP3_192 = 'MP3_192', 'MP3 (192kbps)'
        FLAC = 'FLAC', 'FLAC (Lossless)'
        WAV = 'WAV', 'WAV (Uncompressed Lossless)' 
        ORIGINAL_ZIP = 'ORIGINAL_ZIP', 'Original Files'
    
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='generated_downloads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_downloads')
    requested_format = models.CharField(max_length=20, choices=DownloadFormatChoices.choices)
    
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
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

class ListenEvent(models.Model):
    user = models.ForeignKey( 
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='listen_events',
        db_index=True
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name='listen_events',
        db_index=True
    )
    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name='listen_events',
        null=True, 
        db_index=True
    )
    listen_start_timestamp_utc = models.DateTimeField(
        help_text="UTC timestamp when this unmuted listening segment started."
    )
    reported_listen_duration_ms = models.PositiveIntegerField(
        help_text="Duration of this unmuted listening segment in milliseconds, reported by client."
    )
    listened_at = models.DateTimeField(
        auto_now_add=True, 
        help_text="Timestamp when this event was logged by the backend."
    )

    class Meta:
        ordering = ['-listened_at']
        indexes = [
            models.Index(fields=['track', 'listened_at']),
            models.Index(fields=['release', 'listened_at']),
            models.Index(fields=['user', 'listened_at']),
        ]

    def __str__(self):
        return f"Significant listen for '{self.track.title}' by {self.user.username} at {self.listened_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if self.track and not self.release: 
            self.release = self.track.release
        super().save(*args, **kwargs)

# --- Signal Receivers ---
@receiver(pre_save, sender=Artist)
def artist_pre_save_delete_old_picture(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'artist_picture')

@receiver(pre_save, sender=Release)
def release_pre_save_delete_old_cover(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'cover_art')
    
@receiver(pre_save, sender=Track)
def track_pre_save_delete_old_audio(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'audio_file')

@receiver(pre_save, sender=GeneratedDownload) 
def generated_download_pre_save_delete_old_file(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'download_file')

@receiver(pre_save, sender=Highlight)
def highlight_pre_save_delete_old_custom_image(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'custom_carousel_image')


@receiver(post_delete, sender=Artist)
def artist_post_delete_cleanup_picture(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.artist_picture)

@receiver(post_delete, sender=Release)
def release_post_delete_cleanup_cover_and_download(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.cover_art)
    
@receiver(post_delete, sender=Track)
def track_post_delete_cleanup_audio(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.audio_file)

@receiver(post_delete, sender=GeneratedDownload) 
def generated_download_post_delete_cleanup_file(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.download_file)

@receiver(post_delete, sender=Highlight)
def highlight_post_delete_cleanup_custom_image(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.custom_carousel_image)