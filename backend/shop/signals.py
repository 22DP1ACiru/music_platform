from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from music.models import Release
from .models import Product

@receiver(post_save, sender=Release)
def create_or_update_product_from_release(sender, instance: Release, created: bool, **kwargs):
    """
    Signal to create or update a Product when a Release is saved.
    This product is what users will "buy" if the release is priced.
    """
    if instance.pricing_model in [Release.PricingModel.PAID, Release.PricingModel.NAME_YOUR_PRICE]:
        # A product is active if the release is published AND its release_date is now or in the past.
        is_effectively_published = instance.is_published and (instance.release_date <= timezone.now())

        product_defaults = {
            'name': instance.title,
            'description': f"Digital version of the release: {instance.title} by {instance.artist.name}",
            'product_type': Product.PRODUCT_TYPES[0][0], # 'RELEASE'
            'price': instance.price if instance.pricing_model == Release.PricingModel.PAID else (instance.minimum_price_nyp if instance.minimum_price_nyp is not None else 0.00),
            'currency': instance.currency or 'USD', # Default to USD if currency is not set on release
            'is_active': is_effectively_published,
        }
        
        product, product_created = Product.objects.update_or_create(
            release=instance,
            defaults=product_defaults
        )

        if product_created:
            print(f"Shop Signal: Created Product '{product.name}' for Release '{instance.title}'")
        else:
            changed_fields = []
            for key, value in product_defaults.items():
                if getattr(product, key) != value:
                    changed_fields.append(key)
            if changed_fields:
                print(f"Shop Signal: Updated Product '{product.name}' for Release '{instance.title}'. Changed: {', '.join(changed_fields)}")

    elif hasattr(instance, 'product_info') and instance.product_info is not None:
        # If pricing model changed to FREE (or something else not sellable directly as this Product type),
        # deactivate or delete the associated Product. Deactivating is safer.
        product_to_manage = instance.product_info
        if product_to_manage.is_active:
            product_to_manage.is_active = False
            product_to_manage.save(update_fields=['is_active'])
            print(f"Shop Signal: Deactivated Product for Release '{instance.title}' as it's no longer PAID/NYP.")
    elif not hasattr(instance, 'product_info') or instance.product_info is None:
        # If it's FREE and no product_info exists (e.g. was created as FREE), do nothing.
        pass