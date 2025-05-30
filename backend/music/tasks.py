from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime 
from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models import Q 
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import zipfile
import os
import tempfile
import logging
import shutil 
from datetime import timedelta 

from .models import Release, GeneratedDownload, Track, ListenEvent 

logger = logging.getLogger(__name__)
User = get_user_model()

# Factor to multiply track duration by for the debounce window.
# 1.0 means debounce for the length of the track.
# 0.5 would mean debounce for half the track's length.
# Set to 0 if you want no debouncing beyond the duration significance itself for a user.
SIGNIFICANT_LISTEN_DEBOUNCE_FACTOR = 1.0 


@shared_task(bind=True)
def generate_release_download_zip(self, generated_download_id):
    # ... (generate_release_download_zip code remains the same)
    try:
        download_request = GeneratedDownload.objects.select_related('release__artist').get(id=generated_download_id)
        download_request.status = GeneratedDownload.StatusChoices.PROCESSING
        download_request.celery_task_id = self.request.id
        download_request.save()

        release = download_request.release
        tracks = release.tracks.all().order_by('track_number', 'id') 
        requested_format_key = download_request.requested_format 

        logger.info(f"Starting ZIP generation for Release ID {release.id}, Format: {requested_format_key}, DownloadRequest ID: {download_request.id}")

        with tempfile.TemporaryDirectory(prefix="release_zip_") as temp_dir_path:
            safe_release_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in release.title)
            zip_file_name = f"{safe_release_title}_{requested_format_key}.zip"
            zip_file_path_temp = os.path.join(temp_dir_path, zip_file_name)
            processed_track_paths_for_zip = []

            for track_obj in tracks: 
                if not track_obj.audio_file or not track_obj.audio_file.name:
                    logger.warning(f"Track ID {track_obj.id} ('{track_obj.title}') has no audio file. Skipping.")
                    continue

                original_file_path = track_obj.audio_file.path 
                original_file_name_from_path = os.path.basename(original_file_path)
                
                track_original_format_ext = track_obj.codec_name 
                if track_original_format_ext in ['pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le']: 
                    track_original_format_ext = 'wav'


                if not track_original_format_ext:
                    logger.warning(f"Could not determine original format for track ID {track_obj.id} ('{track_obj.title}') from codec_name. Skipping conversion, will use original if possible")
                    if requested_format_key == GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP:
                        pass 
                    else:
                        logger.error(f"Cannot process track '{track_obj.title}' due to unknown original format for non-ORIGINAL_ZIP request.")
                        continue 

                safe_track_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in track_obj.title)
                track_arcname_base = f"{str(track_obj.track_number).zfill(2)}_{safe_track_title}" if track_obj.track_number else safe_track_title
                
                current_file_to_add_path = original_file_path
                current_file_arcname_ext = track_original_format_ext
                
                try:
                    if requested_format_key != GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP:
                        logger.info(f"Processing track: {track_obj.title}, Original Codec: {track_obj.codec_name}, Lossless: {track_obj.is_lossless}, Requested Key: {requested_format_key}")
                        audio = AudioSegment.from_file(original_file_path) 
                        converted_file_in_temp = None
                        target_ext = ""

                        if requested_format_key == GeneratedDownload.DownloadFormatChoices.MP3_320:
                            target_ext = "mp3"
                            if track_obj.codec_name == "mp3" and (track_obj.bit_rate is None or track_obj.bit_rate >= 300):
                                logger.info(f"Track '{track_obj.title}' is already high-quality MP3. Using original for MP3_320 request.")
                            else:
                                converted_file_in_temp = os.path.join(temp_dir_path, f"{track_arcname_base}.{target_ext}")
                                audio.export(converted_file_in_temp, format=target_ext, bitrate="320k")
                        
                        elif requested_format_key == GeneratedDownload.DownloadFormatChoices.MP3_192:
                            target_ext = "mp3"
                            if track_obj.codec_name == "mp3" and (track_obj.bit_rate is None or track_obj.bit_rate >= 180): 
                                logger.info(f"Track '{track_obj.title}' is already MP3 of sufficient quality for 192k. Using original.")
                            else:
                                converted_file_in_temp = os.path.join(temp_dir_path, f"{track_arcname_base}.{target_ext}")
                                audio.export(converted_file_in_temp, format=target_ext, bitrate="192k")

                        elif requested_format_key == GeneratedDownload.DownloadFormatChoices.FLAC:
                            if track_obj.is_lossless: 
                                target_ext = "flac"
                                converted_file_in_temp = os.path.join(temp_dir_path, f"{track_arcname_base}.{target_ext}")
                                audio.export(converted_file_in_temp, format=target_ext)
                            else: 
                                logger.info(f"Original track '{track_obj.title}' is lossy. Including original for FLAC request.")
                        
                        elif requested_format_key == GeneratedDownload.DownloadFormatChoices.WAV:
                            if track_obj.is_lossless: 
                                target_ext = "wav"
                                converted_file_in_temp = os.path.join(temp_dir_path, f"{track_arcname_base}.{target_ext}")
                                audio.export(converted_file_in_temp, format=target_ext)
                            else: 
                                logger.info(f"Original track '{track_obj.title}' is lossy. Including original for WAV request.")
                        
                        if converted_file_in_temp:
                            current_file_to_add_path = converted_file_in_temp
                            current_file_arcname_ext = target_ext

                except CouldntDecodeError:
                    logger.error(f"Pydub CouldntDecodeError for track ID {track_obj.id} ('{track_obj.title}'). Path: {original_file_path}")
                    if requested_format_key == GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP: pass
                    else: 
                        logger.warning(f"Skipping track '{track_obj.title}' in '{requested_format_key}' ZIP due to decode error.")
                        continue 
                except FileNotFoundError: 
                    logger.error(f"FileNotFoundError for track ID {track_obj.id} ('{track_obj.title}'). Path: {original_file_path}. Skipping.")
                    continue
                except Exception as e_conv:
                    logger.exception(f"Error during audio processing/conversion for track {track_obj.id}: {e_conv}")
                    if requested_format_key == GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP: pass
                    else:
                        logger.warning(f"Skipping track '{track_obj.title}' in '{requested_format_key}' ZIP due to processing error.")
                        continue
                
                final_path_in_temp_for_zip = current_file_to_add_path
                if current_file_to_add_path == original_file_path: 
                    final_path_in_temp_for_zip = os.path.join(temp_dir_path, f"{track_arcname_base}.{current_file_arcname_ext}")
                    if not os.path.exists(original_file_path):
                        logger.error(f"CRITICAL: Original file path {original_file_path} for track '{track_obj.title}' does not exist before copy. Skipping.")
                        continue
                    try:
                        shutil.copy2(original_file_path, final_path_in_temp_for_zip)
                    except Exception as e_copy:
                        logger.error(f"Failed to copy {original_file_path} to {final_path_in_temp_for_zip}: {e_copy}")
                        continue 
                
                processed_track_paths_for_zip.append((final_path_in_temp_for_zip, f"{track_arcname_base}.{current_file_arcname_ext}"))

            if not processed_track_paths_for_zip:
                download_request.status = GeneratedDownload.StatusChoices.FAILED
                download_request.failure_reason = "No tracks were successfully processed or found for zipping."
                download_request.save()
                logger.error(f"No tracks processed for DownloadRequest ID {download_request.id}. Setting status to FAILED.")
                return {"download_id": download_request.id, "status": "FAILED", "reason": download_request.failure_reason}

            with zipfile.ZipFile(zip_file_path_temp, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_to_zip, arcname_in_zip in processed_track_paths_for_zip:
                    if os.path.exists(file_to_zip):
                         zf.write(file_to_zip, arcname=arcname_in_zip)
                    else:
                        logger.warning(f"File {file_to_zip} (arcname: {arcname_in_zip}) not found for zipping. Skipping.")
            
            logger.info(f"ZIP file '{zip_file_name}' created successfully in temp dir.")

            with open(zip_file_path_temp, 'rb') as f_zip:
                django_file = ContentFile(f_zip.read(), name=zip_file_name)
                download_request.download_file.save(zip_file_name, django_file, save=False) 
            
            download_request.status = GeneratedDownload.StatusChoices.READY
            download_request.expires_at = timezone.now() + timezone.timedelta(hours=1) 
            download_request.save() 
            logger.info(f"Download Request ID {download_request.id} is READY. File: {download_request.download_file.name}. Expires at: {download_request.expires_at}")

        return {"download_id": download_request.id, "status": "READY", "file_url": download_request.download_file.url}

    except GeneratedDownload.DoesNotExist:
        logger.error(f"GeneratedDownload ID {generated_download_id} not found.")
        return {"error": "Download request not found."}
    except Exception as e:
        logger.exception(f"Error generating ZIP for DownloadRequest ID {generated_download_id}: {e}")
        try:
            dl_req_fail = GeneratedDownload.objects.get(id=generated_download_id) 
            dl_req_fail.status = GeneratedDownload.StatusChoices.FAILED
            dl_req_fail.failure_reason = str(e)[:1000] 
            dl_req_fail.save()
        except GeneratedDownload.DoesNotExist:
             logger.error(f"Could not update DownloadRequest status to FAILED (ID: {generated_download_id}) as it was not found during exception handling.")
        except Exception as e_save:
            logger.error(f"Additionally, failed to update download_request status to FAILED: {e_save}")
        raise

@shared_task(name="cleanup_generated_downloads")
def cleanup_generated_downloads_task():
    # ... (cleanup_generated_downloads_task code remains the same)
    now = timezone.now()
    items_to_cleanup = GeneratedDownload.objects.filter(
        Q(status=GeneratedDownload.StatusChoices.FAILED) |
        Q(status=GeneratedDownload.StatusChoices.EXPIRED) |
        (Q(status=GeneratedDownload.StatusChoices.READY) & Q(expires_at__lt=now))
    )

    count_cleaned = 0
    count_failed_to_clean = 0

    logger.info(f"[Celery Task] Found {items_to_cleanup.count()} GeneratedDownload items for cleanup.")

    for item in items_to_cleanup:
        original_status = item.status
        file_deleted_successfully = False
        if item.download_file and item.download_file.name:
            try:
                item.download_file.delete(save=False) 
                file_deleted_successfully = True
                logger.info(f"[Celery Task] Deleted file {item.download_file.name} for GeneratedDownload ID {item.id}")
            except Exception as e:
                logger.error(f"[Celery Task] Failed to delete file for GeneratedDownload ID {item.id}: {e}")
                item.failure_reason = (item.failure_reason or "") + f"\nFile deletion error: {e}"
        
        item.status = GeneratedDownload.StatusChoices.EXPIRED
        
        if item.download_file.name : 
             if file_deleted_successfully:
                item.failure_reason = (item.failure_reason or "") + f"\nFile cleaned up by periodic task (original status: {original_status})."
             else: 
                item.failure_reason = (item.failure_reason or "") + f"\nFile cleanup FAILED by periodic task (original status: {original_status})."
        else: 
            item.failure_reason = (item.failure_reason or "") + f"\nMarked EXPIRED by periodic task (original status: {original_status}, no file found)."


        try:
            item.save(update_fields=['status', 'download_file', 'failure_reason']) 
            count_cleaned += 1
        except Exception as e_save:
            logger.error(f"[Celery Task] Failed to update status for GeneratedDownload ID {item.id} after cleanup attempt: {e_save}")
            count_failed_to_clean +=1
    
    logger.info(f"[Celery Task] Cleanup finished. Cleaned records: {count_cleaned}. Failed to update records: {count_failed_to_clean}.")
    return f"Cleaned {count_cleaned} items. Failed to update {count_failed_to_clean} items."


@shared_task(name="music.process_listen_segment")
def process_listen_segment_task(user_id, track_id, segment_start_timestamp_utc_iso, segment_duration_ms):
    logger.info(f"Celery Task: Processing listen segment for track_id={track_id}, user_id={user_id}, start={segment_start_timestamp_utc_iso}, duration_ms={segment_duration_ms}")
    
    if not user_id:
        logger.info(f"Celery Task: Anonymous user_id={user_id}. Listen not tracked as per policy.")
        return

    try:
        track = Track.objects.select_related('release').get(pk=track_id)
    except Track.DoesNotExist:
        logger.error(f"Celery Task: Track with ID {track_id} not found. Cannot process listen segment.")
        return

    try:
        user_instance = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Celery Task: User with ID {user_id} not found. Cannot process listen segment for track_id={track_id}.")
        return
    
    is_duration_significant = False
    if track.duration_in_seconds and track.duration_in_seconds > 0: # Ensure duration_in_seconds is positive
        required_listen_duration_ms = 0
        if track.duration_in_seconds >= 30:
            required_listen_duration_ms = 30000 
        else:
            required_listen_duration_ms = track.duration_in_seconds * 1000 * 0.9 
        
        if segment_duration_ms >= required_listen_duration_ms:
            is_duration_significant = True
    else: # Track has no duration or zero duration, cannot be significant by this rule
        logger.warning(f"Celery Task: Track ID {track.id} has no duration or zero duration. Segment cannot be duration-significant.")
        is_duration_significant = False # Explicitly false
    
    if not is_duration_significant:
        logger.info(f"Celery Task: Listen segment for track ID {track.id} (user: {user_instance.username}, duration: {segment_duration_ms}ms) was not duration-significant. Not creating ListenEvent record.")
        return

    # Segment IS duration-significant. Now check debounce for this user and track.
    # Calculate dynamic debounce window based on track duration
    if track.duration_in_seconds and track.duration_in_seconds > 0 : # Ensure positive duration
        dynamic_debounce_seconds = track.duration_in_seconds * SIGNIFICANT_LISTEN_DEBOUNCE_FACTOR
        # Ensure a minimum sensible debounce, e.g., 5 minutes, to avoid too frequent counts even for short songs if factor is small
        # Or, just use the calculated value. For 1.0 factor, it is the track length.
        # For extremely short tracks (e.g. 10s), this means debounce window is 10s.
        # Let's add a MINIMUM debounce window for very short tracks if the factor results in too small a window.
        # For example, if track_duration * factor < 60s, use 60s.
        # For now, let's stick to the direct factor multiplication.
        if dynamic_debounce_seconds < 1: # Ensure it's at least 1 second
            dynamic_debounce_seconds = 1

        dynamic_debounce_window = timedelta(seconds=dynamic_debounce_seconds)
    else:
        # Fallback to a fixed window if track duration is somehow unavailable or zero
        logger.warning(f"Celery Task: Track ID {track.id} has no/zero duration. Using fixed debounce window for user {user_instance.username}.")
        dynamic_debounce_window = timedelta(minutes=10) # Fallback fixed window (e.g., 10 minutes)

    debounce_time_threshold = timezone.now() - dynamic_debounce_window
    
    recently_counted_for_public_stats = ListenEvent.objects.filter(
        track=track, 
        user=user_instance, 
        listened_at__gte=debounce_time_threshold 
    ).exists()

    if recently_counted_for_public_stats:
        logger.info(f"Celery Task: Duration-significant listen for track ID {track.id} by user {user_instance.username} is within dynamic debounce window ({dynamic_debounce_window}). Not creating new ListenEvent or incrementing public counts.")
        return 

    try:
        parsed_start_time = parse_datetime(segment_start_timestamp_utc_iso)
        effective_listen_start_time = parsed_start_time
        if not parsed_start_time:
            logger.error(f"Celery Task: Could not parse segment_start_timestamp_utc_iso: {segment_start_timestamp_utc_iso}. Using current time minus duration as fallback for ListenEvent.")
            effective_listen_start_time = timezone.now() - timedelta(milliseconds=segment_duration_ms)
        
        ListenEvent.objects.create(
            user=user_instance,
            track=track,
            listen_start_timestamp_utc=effective_listen_start_time,
            reported_listen_duration_ms=segment_duration_ms
        )
        
        Track.objects.filter(pk=track.pk).update(listen_count=F('listen_count') + 1)
        if track.release: 
            Release.objects.filter(pk=track.release.pk).update(listen_count=F('listen_count') + 1)
        
        logger.info(f"Celery Task: Significant, non-debounced listen processed, ListenEvent created, and public counts incremented for track ID {track.id} by user {user_instance.username}.")

    except Exception as e:
        logger.exception(f"Celery Task: Error creating ListenEvent or updating counts for track {track.id}: {e}")