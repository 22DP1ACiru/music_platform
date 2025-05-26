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
import shutil 

from .models import Release, GeneratedDownload, Track 

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def generate_release_download_zip(self, generated_download_id):
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
                
                track_original_format_ext = track_obj.codec_name # Use the more reliable codec_name
                if track_original_format_ext in ['pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le']: # Map various PCM types to 'wav' for extension
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
                            if track_obj.codec_name == "mp3" and (track_obj.bit_rate is None or track_obj.bit_rate >= 180): # Adjusted for 192k
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
            # Change expiry to 1 hour
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