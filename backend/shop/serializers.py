from rest_framework import serializers
from .models import Order, OrderItem, Product
from music.models import Release # For creating library item
from library.models import UserLibraryItem # For creating library item
from django.db import transaction
from decimal import Decimal # Import Decimal

class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    # Add a field for frontend to optionally send the price for NYP
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
            # If it's not NYP, frontend shouldn't send price_override.
            # Or, you could ignore it, or validate it matches product.price.
            # For simplicity, let's disallow it for non-NYP items if sent.
            # (This part is optional, depends on how strict you want to be)
            # if product.release and product.release.pricing_model != Release.PricingModel.NAME_YOUR_PRICE:
            #     raise serializers.ValidationError(
            #         {"price_override": "Price override is only for 'Name Your Price' items."}
            #     )
            pass # Allow price_override for now, will be ignored if not NYP in OrderCreateSerializer logic

        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)


    class Meta:
        model = Order
        fields = ['id', 'items', 'email', 'status', 'total_amount', 'currency', 'created_at']
        read_only_fields = ('id', 'status', 'total_amount', 'currency', 'created_at')

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
                status=Order.ORDER_STATUS_CHOICES[0][0], # PENDING
                total_amount=Decimal('0.00'), 
                currency='USD' 
            )

            current_total = Decimal('0.00')
            order_currency = None

            for item_data in items_data:
                product = Product.objects.get(pk=item_data['product_id'])
                quantity = item_data['quantity']
                price_for_this_item = product.price # Default to product's listed price

                if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                    # For NYP, the validated price_override from item_data is used
                    price_for_this_item = item_data['price_override'] 
                
                if order_currency is None:
                    order_currency = product.currency
                elif order_currency != product.currency:
                    order.delete() # Clean up partially created order
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
            
            # SIMULATE SUCCESSFUL PAYMENT
            order.status = Order.ORDER_STATUS_CHOICES[2][0] # COMPLETED
            order.payment_gateway_id = "simulated_payment_success"
            order.save()

            if order.status == Order.ORDER_STATUS_CHOICES[2][0] and user.is_authenticated:
                for item_data in items_data:
                    product_instance = Product.objects.get(pk=item_data['product_id']) # Re-fetch for clarity
                    if product_instance.release:
                        acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[1][0] # PURCHASED
                        if product_instance.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                             acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[2][0] # NYP
                        elif product_instance.release.pricing_model == Release.PricingModel.FREE:
                             # This case shouldn't happen via order creation for FREE, 
                             # but good to be defensive or handle it if a "free checkout" is implemented
                             acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[0][0] # FREE

                        library_item, created = UserLibraryItem.objects.get_or_create(
                            user=user,
                            release=product_instance.release,
                            defaults={'acquisition_type': acquisition_type}
                        )
                        if not created and library_item.acquisition_type != acquisition_type:
                             library_item.acquisition_type = acquisition_type
                             library_item.save(update_fields=['acquisition_type'])
                        print(f"Added/Updated {product_instance.release.title} to {user.username}'s library (Type: {acquisition_type}).")
        return order

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price_at_purchase', 'item_total']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_username', 'email', 'total_amount', 
            'currency', 'status', 'created_at', 'updated_at', 
            'payment_gateway_id', 'items'
        ]