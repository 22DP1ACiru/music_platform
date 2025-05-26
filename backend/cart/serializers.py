from rest_framework import serializers
from .models import Cart, CartItem
from shop.serializers import ProductSerializer 
from shop.models import Product 
from music.models import Release 
from decimal import Decimal

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True), 
        source='product',
        write_only=True
    )
    # This is the price_override entered by user for NYP in original currency
    price_override_original = serializers.DecimalField(source='price_override', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    
    # Effective price of the item in its original currency
    effective_price_original_currency = serializers.DecimalField(
        source='get_effective_price_in_original_currency', 
        max_digits=10, decimal_places=2, read_only=True
    )
    # Effective price of the item converted to settlement currency (e.g., USD)
    effective_price_settlement_currency = serializers.DecimalField(
        source='get_effective_price_in_settlement_currency', 
        max_digits=10, decimal_places=2, read_only=True, allow_null=True # Allow null if conversion fails
    )
    original_currency = serializers.CharField(source='product.currency', read_only=True)


    class Meta:
        model = CartItem
        fields = [
            'id', 
            'product_id', # For writing
            'product',    # For reading (nested product details)
            'price_override', # For writing NYP price
            'price_override_original',
            'added_at', 
            'effective_price_original_currency', 
            'original_currency',
            'effective_price_settlement_currency'
        ]
        # `price_override` itself is used for input during `add_item`
        # `price_override_original` is just for clearly showing what was stored if needed.
        # For display in cart, we'll primarily use effective_price_settlement_currency.
        read_only_fields = [
            'id', 'product', 'added_at', 
            'effective_price_original_currency', 'original_currency', 
            'effective_price_settlement_currency', 'price_override_original'
        ]

    # Validate method remains the same - it validates price_override against product's original currency min_price
    def validate(self, data):
        product = data.get('product') 
        price_override = data.get('price_override')

        if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if price_override is None:
                raise serializers.ValidationError(
                    {"price_override": "Price must be specified for 'Name Your Price' items added to cart."}
                )
            min_price = product.release.minimum_price_nyp if product.release.minimum_price_nyp is not None else Decimal('0.00')
            if price_override < min_price:
                if product.currency:
                     min_price_display = f"{min_price} {product.currency}"
                else:
                     min_price_display = f"{min_price}"
                raise serializers.ValidationError(
                    {"price_override": f"Entered price {price_override} {product.currency} is below the minimum of {min_price_display}."}
                )
        elif price_override is not None:
            if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                data['price_override'] = None 
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    # These now reflect the cart total in the settlement currency (e.g., USD)
    total_price = serializers.DecimalField(source='get_total_price_in_settlement_currency', max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(source='get_display_currency', read_only=True) # Should be USD
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'currency', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    price_override = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    def validate_product_id(self, value):
        try:
            Product.objects.get(pk=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or is not active.")
        return value

    def validate(self, data):
        product_id = data.get('product_id')
        price_override = data.get('price_override')
        product = Product.objects.get(pk=product_id)

        if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if price_override is None:
                raise serializers.ValidationError(
                    {"price_override": "Price must be specified for 'Name Your Price' items."}
                )
            min_price = product.release.minimum_price_nyp if product.release.minimum_price_nyp is not None else Decimal('0.00')
            if price_override < min_price:
                if product.currency:
                     min_price_display = f"{min_price} {product.currency}"
                else:
                     min_price_display = f"{min_price}"
                raise serializers.ValidationError(
                    {"price_override": f"Entered price {price_override} {product.currency} is below the minimum of {min_price_display}."}
                )
        elif price_override is not None:
             if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                data['price_override'] = None 
        return data