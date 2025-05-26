from rest_framework import serializers
from .models import Order, OrderItem, Product
from music.models import Release 
from library.models import UserLibraryItem 
from django.db import transaction
from decimal import Decimal
from .constants import ORDER_SETTLEMENT_CURRENCY, convert_to_usd

class ProductSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True, allow_null=True)
    track_title = serializers.CharField(source='track.title', read_only=True, allow_null=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    release_id = serializers.PrimaryKeyRelatedField(source='release', read_only=True, allow_null=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True, allow_null=True)
    cover_art = serializers.ImageField(source='release.cover_art', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'description', 
            'product_type', 
            'product_type_display',
            'price', 
            'currency', 
            'is_active',
            'release', 
            'release_id', 
            'track',   
            'release_title',
            'track_title', 
            'artist_name', 
            'cover_art',  
            'created_at', 
            'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'product_type_display', 
            'release_title', 'track_title', 'release_id', 'artist_name', 'cover_art'
        ]


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    price_override = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'))

    def validate_product_id(self, value):
        try:
            Product.objects.get(pk=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or is not active.")
        return value

    def validate(self, data):
        product = Product.objects.get(pk=data['product_id'])
        price_override = data.get('price_override')

        if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if price_override is None:
                raise serializers.ValidationError(
                    {"price_override": "Price must be specified for 'Name Your Price' items."}
                )
            min_price = product.release.minimum_price_nyp if product.release.minimum_price_nyp is not None else Decimal('0.00')
            if price_override < min_price:
                # Compare in original currency before conversion
                # The validation should be against the artist's set minimum in their currency
                if product.currency: # Check if product has a currency
                     min_price_display = f"{min_price} {product.currency}"
                else: # Fallback if product somehow has no currency (shouldn't happen with validation)
                     min_price_display = f"{min_price}"

                raise serializers.ValidationError(
                    {"price_override": f"Entered price {price_override} {product.currency} is below the minimum of {min_price_display}."}
                )
        elif price_override is not None:
            if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                data['price_override'] = None 
        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'items', 'email', 'status', 'status_display', 'total_amount', 'currency', 'created_at', 'updated_at']
        read_only_fields = ('id', 'status', 'status_display', 'total_amount', 'currency', 'created_at', 'updated_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        email_from_payload = validated_data.get('email')
        final_email = email_from_payload
        if user.is_authenticated and not final_email:
            final_email = user.email

        with transaction.atomic():
            order_total_in_settlement_currency = Decimal('0.00')
            
            order = Order.objects.create(
                user=user if user.is_authenticated else None,
                email=final_email,
                status=Order.ORDER_STATUS_CHOICES[0][0], # PENDING
                total_amount=order_total_in_settlement_currency, # Will be updated
                currency=ORDER_SETTLEMENT_CURRENCY # Order will be in USD
            )

            for item_data in items_data:
                product = Product.objects.get(pk=item_data['product_id'])
                quantity = item_data['quantity']
                
                original_price_for_item = product.price 
                original_currency = product.currency

                if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                    # price_override is already validated to be >= minimum_price_nyp in product's original currency
                    original_price_for_item = item_data['price_override']
                
                # Convert this item's price to the order's settlement currency (USD)
                try:
                    price_in_settlement_currency = convert_to_usd(original_price_for_item, original_currency)
                except ValueError as e: # Catch if currency conversion is not possible
                    # This order cannot proceed. Delete the partially created order.
                    order.delete() 
                    raise serializers.ValidationError({"currency_conversion": str(e)})


                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    # Store the price_at_purchase in the order's settlement currency
                    price_at_purchase=price_in_settlement_currency 
                    # Optional: Add fields to OrderItem to store original_price and original_currency for records
                    # original_price=original_price_for_item,
                    # original_currency=original_currency,
                )
                order_total_in_settlement_currency += (price_in_settlement_currency * quantity)
            
            order.total_amount = order_total_in_settlement_currency
            # order.currency is already set to ORDER_SETTLEMENT_CURRENCY
            order.save()

        return order

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price_at_purchase', 'item_total']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_username', 'email', 'total_amount', 
            'currency', 'status', 'status_display', 'created_at', 'updated_at', 
            'payment_gateway_id', 'items'
        ]