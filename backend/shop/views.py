import paypalrestsdk
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
from django.conf import settings
from django.urls import reverse

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
    
    def _configure_paypal_sdk(self): # Helper method
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE, # "sandbox" or "live"
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })

    @action(detail=True, methods=['post'], url_path='create-paypal-payment')
    def create_paypal_payment(self, request, pk=None):
        order = self.get_object() # Gets the order instance

        if order.status != Order.ORDER_STATUS_CHOICES[0][0]: # PENDING
            return Response(
                {"detail": "Payment can only be initiated for PENDING orders."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self._configure_paypal_sdk()

        # Ensure order currency is supported by PayPal or convert if necessary.
        # For simplicity, let's assume order.currency is something PayPal accepts (e.g., USD, EUR).
        # Your orders are already in ORDER_SETTLEMENT_CURRENCY which is USD.

        # Construct return URLs (these will be frontend routes)
        # Ensure FRONTEND_URL in settings.py is correct (e.g., http://localhost:5341)
        base_return_url = settings.FRONTEND_URL.strip('/')
        
        # It's good practice to include the order ID in the return URLs
        # so your frontend can potentially fetch order status on return,
        # though webhook is the source of truth for completion.
        success_url = f"{base_return_url}/order/payment/success/?order_id={order.id}"
        cancel_url = f"{base_return_url}/order/payment/cancel/?order_id={order.id}"

        payment_data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": success_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Order #{order.id} from Vaultwave",
                        "sku": f"ORDER-{order.id}",
                        "price": str(order.total_amount), # Must be string
                        "currency": order.currency, # e.g., "USD"
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(order.total_amount), # Must be string
                    "currency": order.currency
                },
                "description": f"Payment for Vaultwave Order #{order.id}"
            }]
        }

        try:
            payment = paypalrestsdk.Payment(payment_data)
            if payment.create():
                # Store payment ID on order for reference (optional but good)
                order.payment_gateway_id = payment.id # PayPal's payment ID
                order.save(update_fields=['payment_gateway_id'])

                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = str(link.href)
                
                if approval_url:
                    return Response({"approval_url": approval_url, "payment_id": payment.id})
                else:
                    return Response({"detail": "Could not get PayPal approval URL."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # Log more details from payment.error if possible
                error_details = payment.error if hasattr(payment, 'error') else "Unknown PayPal error"
                print(f"PayPal Payment Creation Error: {error_details}")
                return Response({"detail": f"PayPal payment creation failed: {error_details}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Exception creating PayPal payment: {e}")
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)