from django.db import models
from django.conf import settings
from django.utils import timezone
from shop.models import Product # Product is what's added to cart
from decimal import Decimal

class Cart(models.Model):
    """
    Represents a shopping cart, uniquely associated with a user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_effective_price()
        return total
    
    def get_currency(self):
        # Assumes all items in the cart will have the same currency,
        # derived from the first product. Or enforce a site-wide currency.
        first_item = self.items.first()
        if first_item:
            return first_item.product.currency
        return settings.DEFAULT_CURRENCY if hasattr(settings, 'DEFAULT_CURRENCY') else 'USD'


class CartItem(models.Model):
    """
    Represents an item within a shopping cart.
    For digital goods, quantity is typically 1.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE # If product is removed, cart item is removed
    )
    # For NYP items, this stores the price chosen by the user at the time of adding to cart.
    # For regular priced items, this can be null, and we'd use product.price.
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price set by user for NYP items at the time of adding to cart."
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product') # A product can only be in the cart once
        ordering = ['added_at']

    def __str__(self):
        return f"{self.product.name} in cart for {self.cart.user.username}"

    def get_effective_price(self):
        """
        Returns the price for this cart item.
        Uses price_override if set (for NYP), otherwise uses the product's current price.
        """
        if self.price_override is not None:
            return self.price_override
        # Ensure product.release exists if product_type is RELEASE for pricing_model check
        if self.product.product_type == 'RELEASE' and self.product.release:
            if self.product.release.pricing_model == 'NYP':
                # This case should ideally have price_override set.
                # If not, fallback to product.price (which might be minimum_price_nyp or 0)
                return self.product.price 
            return self.product.price # For PAID or FREE (though FREE shouldn't be in cart this way)
        return self.product.price # Fallback for other product types or if release is not linked