from django.db import models
from django.conf import settings
from django.utils import timezone
from shop.models import Product
from decimal import Decimal
from shop.constants import ORDER_SETTLEMENT_CURRENCY, convert_to_usd 

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

    def get_total_price_in_settlement_currency(self): # Renamed for clarity
        total_in_settlement_currency = Decimal('0.00')
        for item in self.items.all():
            item_price_in_original_currency = item.get_effective_price_in_original_currency()
            item_original_currency = item.product.currency
            try:
                price_in_settlement_currency = convert_to_usd( # Or a more generic convert_to_settlement_currency
                    item_price_in_original_currency, 
                    item_original_currency
                )
                total_in_settlement_currency += price_in_settlement_currency
            except ValueError:
                # Handle cases where conversion isn't possible for an item
                # This indicates a data issue or missing exchange rate
                # For now, we might skip this item in total or raise an error for the cart display
                # Depending on strictness, you might want to prevent such items from being in cart.
                # For display, returning a partial sum or an error indicator might be options.
                # Let's assume for now conversion is always possible for items in cart.
                # If not, this method would need more robust error handling.
                pass # Or log an error, or add to a list of unconvertible items
        return total_in_settlement_currency.quantize(Decimal('0.01'))
    
    def get_display_currency(self): # Renamed for clarity
        # The cart will always display totals in the order settlement currency
        return ORDER_SETTLEMENT_CURRENCY


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
        on_delete=models.CASCADE 
    )
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price set by user for NYP items at the time of adding to cart (in product's original currency)."
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product') 
        ordering = ['added_at']

    def __str__(self):
        return f"{self.product.name} in cart for {self.cart.user.username}"

    def get_effective_price_in_original_currency(self): # Renamed for clarity
        """
        Returns the price for this cart item IN ITS ORIGINAL PRODUCT CURRENCY.
        Uses price_override if set (for NYP), otherwise uses the product's current price.
        """
        if self.product.release and self.product.release.pricing_model == 'NYP':
            # For NYP, price_override *must* be set when item is added to cart.
            # If it's None here, it indicates an issue or an item added before validation was strict.
            return self.price_override if self.price_override is not None else self.product.price # Fallback
        return self.product.price # For PAID or FREE (original product price)
    
    def get_effective_price_in_settlement_currency(self): # New method for display if needed per item
        """Returns the price of this item converted to the settlement currency."""
        original_price = self.get_effective_price_in_original_currency()
        original_currency = self.product.currency
        try:
            return convert_to_usd(original_price, original_currency)
        except ValueError:
            return None # Or some indicator of conversion failure