from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import zipfile
import os
import tempfile
import logging
import shutil # For cleaning up temp directories

from .models import Release, GeneratedDownload, Track

logger = logging.getLogger(__name__)

def get_track_original_format(track_file_path):
    """Helper to guess track format from extension."""
    try:
        _, extension = os.path.splitext(track_file_path)
        return extension.lower().replace('.', '')
    except Exception:
        return None

@shared_task(bind=True)
def generate_release_download_zip(self, generated_download_id):
    try:
        download_request = GeneratedDownload.objects.get(id=generated_download_id)
        download_request.status = GeneratedDownload.StatusChoices.PROCESSING
        download_request.celery_task_id = self.request.id
        download_request.save()

        release = download_request.release
        tracks = release.tracks.all().order_by('track_number', 'id')
        requested_format_key = download_request.requested_format # e.g., 'MP3_320', 'FLAC'

        logger.info(f"Starting ZIP generation for Release ID {release.id}, Format: {requested_format_key}, DownloadRequest ID: {download_request.id}")

        # Create a temporary directory to store converted files before zipping
        with tempfile.TemporaryDirectory(prefix="release_zip_") as temp_dir_path:
            zip_file_name = f"{release.title.replace(' ', '_')}_{requested_format_key}.zip"
            zip_file_path_temp = os.path.join(temp_dir_path, zip_file_name)

            processed_track_paths = []

            for track in tracks:
                if not track.audio_file or not track.audio_file.name:
                    logger.warning(f"Track ID {track.id} ('{track.title}') has no audio file. Skipping.")
                    continue

                original_file_path = track.audio_file.path # Assumes default FileSystemStorage
                original_file_name = os.path.basename(original_file_path)
                
                # Sanitize track title for file name
                safe_track_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in track.title)
                track_output_base_name = f"{str(track.track_number).zfill(2)}_{safe_track_title}" if track.track_number else safe_track_title


                target_file_path_in_temp = ""
                conversion_needed = True
                
                original_format_ext = get_track_original_format(original_file_name)
                logger.info(f"Processing track: {track.title}, Original format: {original_format_ext}, Requested format key: {requested_format_key}")

                try:
                    audio = AudioSegment.from_file(original_file_path)
                except CouldntDecodeError:
                    logger.error(f"Could not decode audio for track ID {track.id} ('{track.title}') at path {original_file_path}. Skipping.")
                    continue
                except FileNotFoundError:
                    logger.error(f"Original audio file not found for track ID {track.id} ('{track.title}') at path {original_file_path}. Skipping.")
                    continue


                if requested_format_key == GeneratedDownload.DownloadFormatChoices.MP3_320:
                    target_ext = "mp3"
                    target_file_path_in_temp = os.path.join(temp_dir_path, f"{track_output_base_name}.{target_ext}")
                    audio.export(target_file_path_in_temp, format=target_ext, bitrate="320k")
                elif requested_format_key == GeneratedDownload.DownloadFormatChoices.MP3_192:
                    target_ext = "mp3"
                    target_file_path_in_temp = os.path.join(temp_dir_path, f"{track_output_base_name}.{target_ext}")
                    audio.export(target_file_path_in_temp, format=target_ext, bitrate="192k")
                elif requested_format_key == GeneratedDownload.DownloadFormatChoices.FLAC:
                    if original_format_ext in ['wav', 'flac', 'aiff']: # Only convert from lossless or itself
                        target_ext = "flac"
                        target_file_path_in_temp = os.path.join(temp_dir_path, f"{track_output_base_name}.{target_ext}")
                        audio.export(target_file_path_in_temp, format=target_ext)
                    else: # Original is lossy, provide original instead of up-converting to FLAC
                        logger.info(f"Original format for '{track.title}' is lossy ({original_format_ext}). Providing original for FLAC request.")
                        conversion_needed = False # Use original
                elif requested_format_key == GeneratedDownload.DownloadFormatChoices.WAV:
                     if original_format_ext in ['wav', 'flac', 'aiff']: # Convert from lossless or itself to WAV
                        target_ext = "wav"
                        target_file_path_in_temp = os.path.join(temp_dir_path, f"{track_output_base_name}.{target_ext}")
                        audio.export(target_file_path_in_temp, format=target_ext)
                     else: # Original is lossy, provide original instead of up-converting to WAV
                        logger.info(f"Original format for '{track.title}' is lossy ({original_format_ext}). Providing original for WAV request.")
                        conversion_needed = False
                else:
                    logger.warning(f"Unsupported format key: {requested_format_key} for track '{track.title}'. Providing original.")
                    conversion_needed = False

                if conversion_needed and target_file_path_in_temp:
                    processed_track_paths.append((target_file_path_in_temp, f"{track_output_base_name}.{target_ext}"))
                elif not conversion_needed:
                    # Copy original to temp dir with standardized name for zipping
                    _, original_ext = os.path.splitext(original_file_name)
                    temp_original_copy_path = os.path.join(temp_dir_path, f"{track_output_base_name}{original_ext.lower()}")
                    shutil.copy2(original_file_path, temp_original_copy_path)
                    processed_track_paths.append((temp_original_copy_path, f"{track_output_base_name}{original_ext.lower()}"))

            if not processed_track_paths:
                raise ValueError("No tracks were processed successfully for zipping.")

            # Create ZIP file
            with zipfile.ZipFile(zip_file_path_temp, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_to_zip, arcname in processed_track_paths:
                    zf.write(file_to_zip, arcname=arcname)
            
            logger.info(f"ZIP file '{zip_file_name}' created successfully in temp dir.")

            # Save the ZIP to Django's storage
            with open(zip_file_path_temp, 'rb') as f_zip:
                django_file = ContentFile(f_zip.read(), name=zip_file_name)
                download_request.download_file.save(zip_file_name, django_file, save=True)
            
            download_request.status = GeneratedDownload.StatusChoices.READY
            # Set expiry, e.g., 24 hours from now
            download_request.expires_at = timezone.now() + timezone.timedelta(days=1)
            download_request.save()
            logger.info(f"Download Request ID {download_request.id} is READY. File: {download_request.download_file.name}")

        return {"download_id": download_request.id, "status": "READY", "file_url": download_request.download_file.url}

    except GeneratedDownload.DoesNotExist:
        logger.error(f"GeneratedDownload ID {generated_download_id} not found.")
        # Cannot update status if object doesn't exist.
        return {"error": "Download request not found."}
    except Exception as e:
        logger.exception(f"Error generating ZIP for DownloadRequest ID {generated_download_id}: {e}")
        try:
            # Ensure download_request is defined for failure update
            download_request = GeneratedDownload.objects.get(id=generated_download_id)
            download_request.status = GeneratedDownload.StatusChoices.FAILED
            download_request.failure_reason = str(e)[:1000] # Limit reason length
            download_request.save()
        except GeneratedDownload.DoesNotExist:
            pass # Already logged
        except Exception as e_save:
            logger.error(f"Additionally, failed to update download_request status to FAILED: {e_save}")
        # Re-raise the original exception so Celery knows the task failed
        raise