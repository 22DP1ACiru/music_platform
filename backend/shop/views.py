from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action # Ensure action is imported
from .models import Product, Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer 
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404 # For get_object_or_404
from django.utils import timezone # For updating timestamp
from library.models import UserLibraryItem # For adding to library
from music.models import Release # For accessing Release model details

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Order.objects.filter(user=user).prefetch_related('items__product__release').order_by('-created_at') # Added prefetch_related for release
        return Order.objects.none() 

    def perform_create(self, serializer):
        serializer.save(user=self.request.user) # Pass user to serializer context implicitly

    @action(detail=True, methods=['post'], url_path='confirm-payment')
    def confirm_payment(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        if order.status != Order.ORDER_STATUS_CHOICES[0][0]: # Not 'PENDING'
            return Response(
                {"detail": f"Order is already {order.get_status_display()} and cannot be processed further here."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simulate successful payment
        order.status = Order.ORDER_STATUS_CHOICES[2][0] # 'COMPLETED'
        order.payment_gateway_id = f"simulated_payment_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        order.updated_at = timezone.now()
        order.save()

        # Add items to library after "payment"
        user = request.user
        if user.is_authenticated: # Should always be true due to permission_classes
            for item in order.items.all():
                if item.product.release:
                    acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[1][0] # PURCHASED
                    if item.product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                         acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[2][0] # NYP
                    # FREE items shouldn't normally go through paid order flow, but handle defensively
                    elif item.product.release.pricing_model == Release.PricingModel.FREE:
                         acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[0][0] # FREE

                    library_item, created = UserLibraryItem.objects.get_or_create(
                        user=user,
                        release=item.product.release,
                        defaults={'acquisition_type': acquisition_type}
                    )
                    if not created and library_item.acquisition_type != acquisition_type:
                         # If it existed as FREE and now purchased, update type
                         if library_item.acquisition_type == UserLibraryItem.ACQUISITION_CHOICES[0][0] and \
                            acquisition_type != UserLibraryItem.ACQUISITION_CHOICES[0][0]:
                            library_item.acquisition_type = acquisition_type
                            library_item.save(update_fields=['acquisition_type'])
                    print(f"Order Completion: Added/Updated {item.product.release.title} to {user.username}'s library (Type: {acquisition_type}).")
        
        # Clear the user's cart after successful order completion
        try:
            user_cart = user.cart # Assumes OneToOneField related_name='cart' on User model to Cart
            user_cart.items.all().delete()
            print(f"Order Completion: Cleared cart for user {user.username}")
        except AttributeError: # user.cart might not exist if related_name is different or not setup
            print(f"Order Completion: Could not find/clear cart for user {user.username}")
        except Exception as e:
            print(f"Order Completion: Error clearing cart for user {user.username}: {e}")


        serializer = self.get_serializer(order)
        return Response(serializer.data)