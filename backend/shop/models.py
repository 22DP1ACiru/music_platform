from django.db import models
from django.conf import settings
# from music.models import Release, Track # This line causes the circular import if music.models imports from shop.models
# Instead, use string reference for ForeignKey if needed, or ensure one-way dependency.
# For Product model, Release and Track are OneToOneField, so string reference is fine.

from vaultwave.constants import CURRENCY_CHOICES # Import from the new constants file

class Product(models.Model):
    """
    Represents something that can be sold, e.g., a digital release or track.
    """
    PRODUCT_TYPES = [
        ('RELEASE', 'Digital Release'),
        ('TRACK', 'Digital Track'),
        # ('MERCH', 'Merchandise'), # Future: physical goods
        # ('SUBSCRIPTION', 'Subscription Tier'), # Future: subscriptions
    ]

    name = models.CharField(max_length=255, help_text="Display name of the product")
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    
    # Link to the actual music content if it's a digital music product
    # Using string reference 'music.Release' and 'music.Track' avoids direct import issues here
    release = models.OneToOneField('music.Release', on_delete=models.SET_NULL, null=True, blank=True, related_name='product_info')
    track = models.OneToOneField('music.Track', on_delete=models.SET_NULL, null=True, blank=True, related_name='product_info')
    # For merch, you might have different fields or another linked model.

    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    is_active = models.BooleanField(default=True, help_text="Is this product currently available for sale?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_product_type_display()}) - {self.price} {self.currency}"

    class Meta:
        ordering = ['name']


class Order(models.Model):
    """
    Represents a customer's order.
    """
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'), # e.g. payment verification
        ('COMPLETED', 'Completed'),   # Payment successful, access granted/shipped
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    email = models.EmailField(blank=True, null=True, help_text="Email for order confirmation, especially if user is null")
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD') 
    
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    payment_gateway_id = models.CharField(max_length=255, blank=True, null=True, help_text="Transaction ID from payment gateway")
    payment_method_details = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., 'Visa ending in 1234'")


    def __str__(self):
        user_identifier = "Guest"
        if self.user:
            user_identifier = self.user.username
        elif self.email:
            user_identifier = self.email
        return f"Order {self.id} by {user_identifier} - Status: {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    """
    Represents an item within an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items') 
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the single item at the time of purchase")

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"

    @property
    def item_total(self):
        return self.quantity * self.price_at_purchase