from django.db import models
from django.conf import settings
# from music.models import Release # Use string reference to avoid circular import

class UserLibraryItem(models.Model):
    """
    Represents a Release that a User has added to their library.
    """
    ACQUISITION_CHOICES = [
        ('FREE', 'Free Acquisition'),
        ('PURCHASED', 'Purchased'),
        ('NYP', 'Name Your Price'), 
        # Could add 'GIFTED', 'PROMO', etc. in the future
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='library_items'
    )
    release = models.ForeignKey(
        'music.Release', # String reference to music.Release model
        on_delete=models.CASCADE, 
        related_name='library_entries'
    )
    acquired_at = models.DateTimeField(auto_now_add=True)
    acquisition_type = models.CharField(
        max_length=20, 
        choices=ACQUISITION_CHOICES, 
        default='FREE' # Default, can be updated upon purchase
    )
    # You could add a reference to an OrderItem if acquired via purchase
    # order_item = models.OneToOneField('shop.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)


    def __str__(self):
        return f"'{self.release.title}' in {self.user.username}'s library"

    class Meta:
        ordering = ['-acquired_at']
        unique_together = ('user', 'release') # User can only have a release once in their library
        app_label = 'library' # Explicitly set app_label