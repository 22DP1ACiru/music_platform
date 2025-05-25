from django.db import models
# from django.contrib.auth.models import User # Not used directly, settings.AUTH_USER_MODEL is preferred
from django.conf import settings
from django.db.models.signals import pre_save, post_delete # For file deletion signals
from django.dispatch import receiver # For file deletion signals
# import os # No longer needed here
# from music.models import validate_image_not_gif # Use utility validator
import logging # Import Python's logging module

# Import from the new utility module
from vaultwave.utils import (
    delete_file_if_changed,
    delete_file_on_instance_delete,
    validate_image_not_gif_utility
)

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
        validators=[validate_image_not_gif_utility] # Use utility validator
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
# Use the imported utility functions

@receiver(pre_save, sender=UserProfile)
def userprofile_pre_save_delete_old_picture(sender, instance, **kwargs):
    delete_file_if_changed(sender, instance, 'profile_picture')

@receiver(post_delete, sender=UserProfile)
def userprofile_post_delete_cleanup_picture(sender, instance, **kwargs):
    delete_file_on_instance_delete(instance.profile_picture)