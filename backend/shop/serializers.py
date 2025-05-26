from rest_framework import serializers
from .models import Order, OrderItem, Product
from music.models import Release # For NYP validation and library item
from library.models import UserLibraryItem # For creating library item
from django.db import transaction
from decimal import Decimal 

class ProductSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True, allow_null=True)
    track_title = serializers.CharField(source='track.title', read_only=True, allow_null=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    release_id = serializers.PrimaryKeyRelatedField(source='release', read_only=True, allow_null=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True, allow_null=True) # Added for cart display
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
            'artist_name',
            'cover_art',
            'track_title',
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'product_type_display', 'release_title', 'track_title', 'release_id']


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
                raise serializers.ValidationError(
                    {"price_override": f"Entered price is below the minimum of {min_price} {product.currency}."}
                )
        elif price_override is not None:
            if not (product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE):
                data['price_override'] = None 
        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    # Expose order details for response after creation
    status_display = serializers.CharField(source='get_status_display', read_only=True)


    class Meta:
        model = Order
        fields = ['id', 'items', 'email', 'status', 'status_display', 'total_amount', 'currency', 'created_at', 'updated_at'] # Added updated_at
        read_only_fields = ('id', 'status', 'status_display', 'total_amount', 'currency', 'created_at', 'updated_at') # status is now read_only here

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        email_from_payload = validated_data.get('email')
        final_email = email_from_payload
        if user.is_authenticated and not final_email:
            final_email = user.email

        with transaction.atomic():
            order = Order.objects.create(
                user=user if user.is_authenticated else None,
                email=final_email,
                status=Order.ORDER_STATUS_CHOICES[0][0], # PENDING (This is the key change here)
                total_amount=Decimal('0.00'), 
                currency='USD' 
            )

            current_total = Decimal('0.00')
            order_currency = None

            for item_data in items_data:
                product = Product.objects.get(pk=item_data['product_id'])
                quantity = item_data['quantity']
                price_for_this_item = product.price 

                if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                    price_for_this_item = item_data['price_override'] 
                
                if order_currency is None:
                    order_currency = product.currency
                elif order_currency != product.currency:
                    order.delete() 
                    raise serializers.ValidationError(
                        {"currency": "All items in an order must have the same currency."}
                    )

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price_at_purchase=price_for_this_item 
                )
                current_total += (price_for_this_item * quantity)
            
            order.total_amount = current_total
            order.currency = order_currency or 'USD'
            order.save() # Save the order with PENDING status and calculated total

            # REMOVED: Automatic setting to COMPLETED and library addition
            # This will now happen in a separate "confirm_payment" step
            # order.status = Order.ORDER_STATUS_CHOICES[2][0] # COMPLETED
            # order.payment_gateway_id = "simulated_payment_success_pending_confirmation" 
            # order.save()
            # Library addition logic will also move

        return order

class OrderItemSerializer(serializers.ModelSerializer):
    # product_name = serializers.CharField(source='product.name', read_only=True) # Redundant if using ProductSerializer
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