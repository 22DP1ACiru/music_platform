from django.db import models
from django.contrib.auth.models import User # Not used directly, settings.AUTH_USER_MODEL is preferred
from django.conf import settings
from django.db.models.signals import pre_save, post_delete # For file deletion signals
from django.dispatch import receiver # For file deletion signals
import os # For file deletion
from music.models import validate_image_not_gif # Import the validator
import logging # Import Python's logging module

# Get an instance of a logger
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger

def profile_pic_path(instance, filename):
    user_id_for_path = instance.user.id if instance.user else "unknown_user"
    return f'profile_pics/{user_id_for_path}/{filename}'

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='profile'    
    )
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=profile_pic_path, 
        null=True,
        blank=True,
        validators=[validate_image_not_gif] # Added GIF validator
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
        return f"{self.user.username}'s Profile"

# --- Signal Receivers for Deleting Old Files ---
# Using the helper from music.models for DRY principle, ensure it's importable
# or redefine a similar helper here. For simplicity, assuming _delete_file_if_changed
# and _delete_file_on_instance_delete are accessible or re-implemented.
# To avoid circular import issues, let's define them here if this app is standalone.

def _userprofile_delete_file_if_changed(sender, instance, field_name):
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = getattr(old_instance, field_name)
    new_file = getattr(instance, field_name)

    if old_file and old_file != new_file:
        if hasattr(old_file, 'path') and os.path.isfile(old_file.path):
            try:
                os.remove(old_file.path)
                logger.info(f"UserProfile Signal: Deleted old file (local): {old_file.path}")
            except Exception as e:
                logger.error(f"UserProfile Signal: Error deleting old file (local) {old_file.path}: {e}")
        elif hasattr(old_file, 'name') and old_file.name and hasattr(old_file, 'storage') and old_file.storage.exists(old_file.name):
             try:
                old_file.storage.delete(old_file.name)
                logger.info(f"UserProfile Signal: Deleted old file from storage: {old_file.name}")
             except Exception as e:
                logger.error(f"UserProfile Signal: Error deleting old file {old_file.name} from storage: {e}")


def _userprofile_delete_file_on_instance_delete(instance_file_field):
    if instance_file_field:
        if hasattr(instance_file_field, 'path') and os.path.isfile(instance_file_field.path):
            try:
                os.remove(instance_file_field.path)
                logger.info(f"UserProfile Signal: Deleted file on instance delete (local): {instance_file_field.path}")
            except Exception as e:
                logger.error(f"UserProfile Signal: Error deleting file {instance_file_field.path} on instance delete (local): {e}")
        elif hasattr(instance_file_field, 'name') and instance_file_field.name and hasattr(instance_file_field, 'storage') and instance_file_field.storage.exists(instance_file_field.name):
            try:
                instance_file_field.storage.delete(instance_file_field.name)
                logger.info(f"UserProfile Signal: Deleted file from storage on instance delete: {instance_file_field.name}")
            except Exception as e:
                logger.error(f"UserProfile Signal: Error deleting file {instance_file_field.name} from storage on instance delete: {e}")


@receiver(pre_save, sender=UserProfile)
def userprofile_pre_save_delete_old_picture(sender, instance, **kwargs):
    _userprofile_delete_file_if_changed(sender, instance, 'profile_picture')

@receiver(post_delete, sender=UserProfile)
def userprofile_post_delete_cleanup_picture(sender, instance, **kwargs):
    _userprofile_delete_file_on_instance_delete(instance.profile_picture)