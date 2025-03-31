from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# This function will be used to set the upload path for profile pictures
# The path will be dynamic and include the user ID
# This allows for better organization of files and avoids name collisions
def profile_pic_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/profile_pics/<user_id>/<filename>
    return f'profile_pics/{instance.user.id}/{filename}'

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # If User is deleted, delete Profile
        related_name='profile'    # Access profile from user: user.profile
    )
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=profile_pic_path, # Use the function for dynamic path
        null=True,
        blank=True
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