from rest_framework import serializers
from .models import Cart, CartItem
from shop.serializers import ProductSerializer # Assuming ProductSerializer exists and is suitable
from shop.models import Product # For validation
from music.models import Release # For NYP validation
from decimal import Decimal

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    # product_id is write-only, used when adding items
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True), # Only active products
        source='product',
        write_only=True
    )
    effective_price = serializers.DecimalField(source='get_effective_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'product', 'price_override', 'added_at', 'effective_price']
        read_only_fields = ['id', 'product', 'added_at', 'effective_price']

    def validate(self, data):
        product = data.get('product') # This will be the Product instance from product_id source
        price_override = data.get('price_override')

        if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if price_override is None:
                raise serializers.ValidationError(
                    {"price_override": "Price must be specified for 'Name Your Price' items added to cart."}
                )
            min_price = product.release.minimum_price_nyp if product.release.minimum_price_nyp is not None else Decimal('0.00')
            if price_override < min_price:
                raise serializers.ValidationError(
                    {"price_override": f"Entered price {price_override} is below the minimum of {min_price} {product.currency}."}
                )
        elif price_override is not None:
            # If it's not NYP, an explicit price_override might be an error or should be ignored.
            # For now, let's say if it's not NYP, price_override should not be sent.
            # If it is sent, we could validate it matches product.price or simply ignore it.
            # To be strict, we can raise an error if price_override is sent for non-NYP.
            if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                 raise serializers.ValidationError(
                    {"price_override": "Price override is only applicable for 'Name Your Price' items."}
                )
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(source='get_total_price', max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(source='get_currency', read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'currency', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    price_override = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value, is_active=True)
            # Check if product is already in user's library (optional, prevents re-adding already owned items)
            # request = self.context.get('request')
            # if request and request.user.is_authenticated:
            #   if product.release and UserLibraryItem.objects.filter(user=request.user, release=product.release).exists():
            #       raise serializers.ValidationError("This item is already in your library.")
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or is not active.")
        return value

    def validate(self, data):
        product_id = data.get('product_id')
        price_override = data.get('price_override')
        product = Product.objects.get(pk=product_id) # Already validated by validate_product_id

        if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if price_override is None:
                raise serializers.ValidationError(
                    {"price_override": "Price must be specified for 'Name Your Price' items."}
                )
            min_price = product.release.minimum_price_nyp if product.release.minimum_price_nyp is not None else Decimal('0.00')
            if price_override < min_price:
                raise serializers.ValidationError(
                    {"price_override": f"Entered price {price_override} is below the minimum of {min_price} {product.currency}."}
                )
        elif price_override is not None:
             if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                # If price_override is provided for a non-NYP item, clear it or raise error.
                # For now, let's clear it, the effective price will be the product's price.
                data['price_override'] = None 
                # Alternative: raise serializers.ValidationError({"price_override": "Price override is only for NYP items."})
        return data