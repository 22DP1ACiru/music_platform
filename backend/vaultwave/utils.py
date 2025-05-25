import os
import logging
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# --- File Handling Utilities ---

def delete_file_if_changed(sender, instance, field_name):
    """
    Signal helper to delete an old file from storage if it has changed.
    To be used with pre_save signals.
    """
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = getattr(old_instance, field_name, None)
    new_file = getattr(instance, field_name, None)

    if old_file and old_file != new_file:
        if hasattr(old_file, 'name') and old_file.name and \
            hasattr(old_file, 'storage') and old_file.storage.exists(old_file.name):
            try:
                old_file.storage.delete(old_file.name)
                logger.info(f"Util Signal: Deleted old file from storage: {old_file.name} (field: {field_name})")
            except Exception as e:
                logger.error(f"Util Signal: Error deleting old file {old_file.name} from storage (field: {field_name}): {e}")
        # Fallback for local storage if storage.exists might not be reliable or it's a direct FileField.
        elif hasattr(old_file, 'path') and os.path.isfile(old_file.path):
            try:
                os.remove(old_file.path)
                logger.info(f"Util Signal: Deleted old file (local): {old_file.path} (field: {field_name})")
            except Exception as e:
                logger.error(f"Util Signal: Error deleting old file (local) {old_file.path} (field: {field_name}): {e}")


def delete_file_on_instance_delete(instance_file_field):
    """
    Helper to delete a file from storage when an instance is deleted.
    To be used with post_delete signals.
    `instance_file_field` is the FileField attribute of the instance being deleted.
    """
    if instance_file_field:
        if hasattr(instance_file_field, 'name') and instance_file_field.name and \
            hasattr(instance_file_field, 'storage') and instance_file_field.storage.exists(instance_file_field.name):
            try:
                instance_file_field.storage.delete(instance_file_field.name)
                logger.info(f"Util Signal: Deleted file from storage on instance delete: {instance_file_field.name}")
            except Exception as e:
                logger.error(f"Util Signal: Error deleting file {instance_file_field.name} from storage on instance delete: {e}")
        # Fallback for local storage
        elif hasattr(instance_file_field, 'path') and os.path.isfile(instance_file_field.path):
            try:
                os.remove(instance_file_field.path)
                logger.info(f"Util Signal: Deleted file on instance delete (local): {instance_file_field.path}")
            except Exception as e:
                logger.error(f"Util Signal: Error deleting file {instance_file_field.path} on instance delete (local): {e}")


# --- Image Validation ---
def validate_image_not_gif_utility(value):
    """
    Shared validator to ensure an image is not a GIF.
    `value` is the InMemoryUploadedFile or similar file object.
    """
    try:
        value.seek(0)  # Ensure we're at the start of the file
        img = Image.open(value)
        image_format = img.format
        value.seek(0)  # Reset cursor for further processing by Django
        if image_format and image_format.upper() == 'GIF':
            raise ValidationError(
                "Animated GIFs are not allowed. Please use a static image format like JPG or PNG.",
                code='gif_not_allowed'
            )
    except UnidentifiedImageError:
        # This error means Pillow couldn't identify the image.
        # Django's ImageField will likely catch this more specifically if it's not a valid image.
        # You might want to raise a more generic error or let Django handle it.
        # For now, let's pass, assuming Django's own validation will run.
        pass
    except Exception as e:
        # Catch other potential errors during image processing
        logger.error(f"Error during GIF validation: {e}")
        # Depending on policy, you might re-raise or raise a ValidationError
        # For now, pass to let other validations proceed.
        pass