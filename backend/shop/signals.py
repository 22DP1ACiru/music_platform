# backend/shop/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone # Import timezone
from music.models import Release
from .models import Product 
# CURRENCY_CHOICES is not directly used in this signal, but it's fine to keep if models.py needs it.

@receiver(post_save, sender=Release)
def create_or_update_product_from_release(sender, instance, created, **kwargs):
    """
    Signal to create or update a Product when a Release is saved.
    This product is what users will "buy".
    """
    if instance.pricing_model in [Release.PricingModel.PAID, Release.PricingModel.NAME_YOUR_PRICE]:
        # Ensure both datetimes are comparable.
        # instance.release_date should be aware if USE_TZ=True.
        # instance.created_at is aware.
        # For 'is_active', we typically compare release_date to the current time.
        # However, the original logic compared to created_at, which might be specific.
        # Let's refine the 'is_active' logic to be more standard:
        # A product is active if the release is published AND its release_date is now or in the past.
        
        is_effectively_published = instance.is_published and instance.release_date <= timezone.now()

        product_defaults = {
            'name': instance.title,
            'description': f"Digital version of the release: {instance.title} by {instance.artist.name}",
            'product_type': Product.PRODUCT_TYPES[0][0], # 'RELEASE'
            'price': instance.price if instance.pricing_model == Release.PricingModel.PAID else instance.minimum_price_nyp or 0.00,
            'currency': instance.currency or 'USD', # Default to USD if not set
            'is_active': is_effectively_published, 
        }
        
        product, product_created = Product.objects.update_or_create(
            release=instance,
            defaults=product_defaults
        )

        if product_created:
            print(f"Created Product '{product.name}' for Release '{instance.title}'")
        else:
            # Check if any significant field changed to print update message
            changed_fields = []
            for key, value in product_defaults.items():
                if getattr(product, key) != value:
                    changed_fields.append(key)
            if changed_fields:
                print(f"Updated Product '{product.name}' for Release '{instance.title}'. Changed: {', '.join(changed_fields)}")

    elif hasattr(instance, 'product_info'): # Check if relation exists
        # If pricing model is now FREE or something else, deactivate/delete the product
        try:
            product_to_remove = Product.objects.get(release=instance)
            if product_to_remove.is_active:
                 product_to_remove.is_active = False
                 product_to_remove.save(update_fields=['is_active'])
                 print(f"Deactivated Product for Release '{instance.title}' as it's no longer priced.")
        except Product.DoesNotExist:
            pass # No product existed, nothing to do