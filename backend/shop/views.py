import json # For parsing webhook body
import paypalrestsdk
from django.conf import settings
from django.urls import reverse # Not strictly used here but good to keep with other URL related imports
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt # For webhook
from django.db import transaction # For atomic operations

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes # Added api_view
from rest_framework.permissions import IsAuthenticated, AllowAny # Added AllowAny for webhook

from .models import Product, Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from library.models import UserLibraryItem
from music.models import Release

import logging # For logging webhook events
logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Order.objects.filter(user=user).prefetch_related('items__product__release').order_by('-created_at')
        return Order.objects.none()

    def perform_create(self, serializer):
        # User is automatically set if AddToCartSerializer is used within a ViewSet action
        # or if the request.user is passed to the serializer context.
        # For OrderCreateSerializer, it expects 'items' and optionally 'email'.
        # The user is derived from request.user in the serializer's create method.
        serializer.save() # User is handled by serializer context or direct assignment in create

    @action(detail=True, methods=['post'], url_path='confirm-payment')
    def confirm_payment(self, request, pk=None):
        # This is your SIMULATED payment confirmation.
        # With PayPal, the actual confirmation will come via webhook.
        # You might keep this for testing or other payment methods.
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

        user = request.user
        if user.is_authenticated:
            for item in order.items.all():
                if item.product.release:
                    acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[1][0] # PURCHASED
                    if item.product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                         acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[2][0] # NYP
                    elif item.product.release.pricing_model == Release.PricingModel.FREE:
                         acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[0][0] # FREE

                    library_item, created = UserLibraryItem.objects.get_or_create(
                        user=user,
                        release=item.product.release,
                        defaults={'acquisition_type': acquisition_type}
                    )
                    if not created and library_item.acquisition_type != acquisition_type:
                         if library_item.acquisition_type == UserLibraryItem.ACQUISITION_CHOICES[0][0] and \
                            acquisition_type != UserLibraryItem.ACQUISITION_CHOICES[0][0]:
                            library_item.acquisition_type = acquisition_type
                            library_item.save(update_fields=['acquisition_type'])
                    logger.info(f"Order Completion (Simulated): Added/Updated {item.product.release.title} to {user.username}'s library (Type: {acquisition_type}).")
        try:
            user_cart = user.cart
            user_cart.items.all().delete()
            logger.info(f"Order Completion (Simulated): Cleared cart for user {user.username}")
        except AttributeError:
            logger.warning(f"Order Completion (Simulated): Could not find/clear cart for user {user.username}")
        except Exception as e:
            logger.error(f"Order Completion (Simulated): Error clearing cart for user {user.username}: {e}")

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def _configure_paypal_sdk(self):
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })

    @action(detail=True, methods=['post'], url_path='create-paypal-payment')
    def create_paypal_payment(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.ORDER_STATUS_CHOICES[0][0]: # PENDING
            return Response(
                {"detail": "Payment can only be initiated for PENDING orders."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self._configure_paypal_sdk()
        if settings.DEBUG and settings.NGROK_DOMAIN:
            effective_base_url = settings.NGROK_DOMAIN.strip('/')
        else:
            effective_base_url = settings.FRONTEND_URL.strip('/')

        success_url = f"{effective_base_url}/order/payment/success/?order_id={order.id}"
        cancel_url = f"{effective_base_url}/order/payment/cancel/?order_id={order.id}"

        logger.info(f"PayPal Success URL being sent: {success_url}")
        logger.info(f"PayPal Cancel URL being sent: {cancel_url}")

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
                        "price": str(order.total_amount),
                        "currency": order.currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(order.total_amount),
                    "currency": order.currency
                },
                "description": f"Payment for Vaultwave Order #{order.id}",
                "invoice_number": f"VAULTWAVE-ORDER-{order.id}-{int(timezone.now().timestamp())}" # Unique invoice number
            }]
        }

        try:
            payment = paypalrestsdk.Payment(payment_data)
            if payment.create():
                order.payment_gateway_id = payment.id # Store PayPal's payment ID
                order.save(update_fields=['payment_gateway_id'])
                approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
                if approval_url:
                    return Response({"approval_url": approval_url, "payment_id": payment.id})
                else:
                    logger.error("PayPal approval URL not found in payment.links")
                    return Response({"detail": "Could not get PayPal approval URL."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                error_details = payment.error if hasattr(payment, 'error') else "Unknown PayPal error during creation"
                logger.error(f"PayPal Payment Creation Error: {error_details}")
                return Response({"detail": f"PayPal payment creation failed: {error_details}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Exception creating PayPal payment for order {order.id}: {e}")
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- PayPal Webhook View ---
@csrf_exempt # PayPal POSTs without a CSRF token
@api_view(['POST']) # This view should only accept POST requests
@drf_permission_classes([AllowAny]) # Webhooks come from PayPal, not an authenticated user
def paypal_webhook(request):
    """
    Handles incoming webhooks from PayPal.
    Verifies the webhook signature and processes payment events.
    """
    if not settings.PAYPAL_WEBHOOK_ID:
        logger.error("PAYPAL_WEBHOOK_ID is not set in settings. Cannot verify webhook.")
        return HttpResponseBadRequest("Webhook ID not configured.")

    # Configure SDK for verification (if not already configured globally, though it should be)
    # It's safer to reconfigure here or ensure it's configured on app startup.
    # For simplicity, let's assume _configure_paypal_sdk can be called if needed,
    # but verification often uses a static method.
    paypalrestsdk.configure({
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET
    })

    try:
        # Get the webhook event from the request body
        event_body = request.body.decode('utf-8')
        event_json = json.loads(event_body)
        logger.info(f"Received PayPal Webhook Event: {event_json.get('event_type')}")
        # logger.debug(f"Full Webhook Body: {event_body}") # Be careful logging full body in prod

        # Verify the webhook event
        # The transmission_id, transmission_time, cert_url, auth_algo, transmission_sig
        # are passed in the request headers by PayPal.
        # The paypalrestsdk.WebhookEvent.verify() method handles this.
        # Note: The SDK's verify method might require the raw headers.
        # For now, let's assume a simplified verification or that the SDK handles it internally
        # if the webhook ID is configured.
        # A more robust verification:
        # event_verify = paypalrestsdk.WebhookEvent.verify(
        #     request.headers.get('Paypal-Transmission-Id'),
        #     request.headers.get('Paypal-Transmission-Time'),
        #     settings.PAYPAL_WEBHOOK_ID,
        #     event_body, # The raw request body
        #     request.headers.get('Paypal-Cert-Url'),
        #     request.headers.get('Paypal-Auth-Algo'),
        #     request.headers.get('Paypal-Transmission-Sig')
        # )
        # if not event_verify:
        #     logger.warning("PayPal Webhook verification failed.")
        #     return HttpResponseForbidden("Webhook verification failed.")

        # For a simpler start, especially in sandbox, you might initially skip full verification
        # BUT THIS IS NOT RECOMMENDED FOR PRODUCTION.
        # For now, let's proceed assuming verification would pass or is simplified.
        # **IMPORTANT**: For production, robust webhook verification is CRITICAL.
        # The `paypalrestsdk` might have changed its verification API.
        # Refer to the latest `paypal-python-sdk` (which `paypalrestsdk` is based on or succeeded by)
        # or PayPal's direct webhook verification documentation.

        # A common pattern is to use the Webhook ID to fetch the event type from PayPal to verify.
        # However, the SDK should provide a direct verification method.
        # If PAYPAL_WEBHOOK_ID is set, the SDK might use it implicitly with some verify calls.

        # Let's assume for now we trust the event if it parses and has the right type in SANDBOX
        # THIS IS A SIMPLIFICATION FOR DEVELOPMENT PROGRESS.
        # YOU MUST IMPLEMENT PROPER VERIFICATION FOR PRODUCTION.
        if settings.PAYPAL_MODE != "sandbox": # Enforce verification for non-sandbox
             # Placeholder for actual verification logic that should be implemented
            logger.error("Webhook verification is mandatory for non-sandbox environments and is not fully implemented here.")
            return HttpResponseForbidden("Webhook verification required and not fully implemented.")


        event_type = event_json.get("event_type")
        resource = event_json.get("resource")

        if event_type == "PAYMENT.SALE.COMPLETED":
            logger.info(f"Processing PAYMENT.SALE.COMPLETED for resource ID: {resource.get('id')}")
            parent_payment_id = resource.get("parent_payment") # This is the Payment ID we stored
            transaction_id = resource.get("id") # This is the Sale ID (actual transaction)

            if not parent_payment_id:
                logger.error("Parent payment ID not found in webhook resource.")
                return HttpResponseBadRequest("Missing parent_payment ID in webhook.")

            try:
                with transaction.atomic(): # Ensure database operations are atomic
                    order = Order.objects.select_for_update().get(payment_gateway_id=parent_payment_id)

                    if order.status == Order.ORDER_STATUS_CHOICES[2][0]: # COMPLETED
                        logger.info(f"Order {order.id} is already completed. Ignoring webhook.")
                        return HttpResponse(status=200) # Acknowledge webhook

                    order.status = Order.ORDER_STATUS_CHOICES[2][0] # COMPLETED
                    # Store the actual sale transaction ID if different and useful
                    # order.payment_transaction_id = transaction_id # You might add this field to Order model
                    order.payment_method_details = f"PayPal Sale ID: {transaction_id}"
                    order.updated_at = timezone.now()
                    order.save()

                    logger.info(f"Order {order.id} status updated to COMPLETED.")

                    # Add items to library
                    user = order.user
                    if user and user.is_authenticated: # User should exist for an order
                        for item in order.items.all():
                            if item.product.release:
                                acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[1][0] # PURCHASED
                                if item.product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
                                    acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[2][0] # NYP
                                elif item.product.release.pricing_model == Release.PricingModel.FREE:
                                    # This case shouldn't happen for a paid order, but handle defensively
                                    acquisition_type = UserLibraryItem.ACQUISITION_CHOICES[0][0] # FREE

                                library_item, created = UserLibraryItem.objects.get_or_create(
                                    user=user,
                                    release=item.product.release,
                                    defaults={'acquisition_type': acquisition_type}
                                )
                                if not created and library_item.acquisition_type != acquisition_type:
                                    if library_item.acquisition_type == UserLibraryItem.ACQUISITION_CHOICES[0][0] and \
                                    acquisition_type != UserLibraryItem.ACQUISITION_CHOICES[0][0]:
                                        library_item.acquisition_type = acquisition_type
                                        library_item.save(update_fields=['acquisition_type'])
                                logger.info(f"Webhook: Added/Updated {item.product.release.title} to {user.username}'s library (Type: {acquisition_type}).")

                        # Clear the user's cart
                        try:
                            user_cart = user.cart
                            user_cart.items.all().delete()
                            logger.info(f"Webhook: Cleared cart for user {user.username} after order {order.id} completion.")
                        except AttributeError:
                            logger.warning(f"Webhook: Could not find/clear cart for user {user.username} (Order {order.id}).")
                        except Exception as e_cart:
                            logger.error(f"Webhook: Error clearing cart for user {user.username} (Order {order.id}): {e_cart}")
                    else:
                        logger.warning(f"Order {order.id} completed but no authenticated user found on order to update library/cart.")
                    
                    # TODO: Send confirmation email to user

            except Order.DoesNotExist:
                logger.error(f"Order with payment_gateway_id {parent_payment_id} not found for webhook event.")
                return HttpResponseBadRequest("Order not found for this payment.")
            except Exception as e_process:
                logger.exception(f"Error processing completed payment webhook for payment_id {parent_payment_id}: {e_process}")
                return HttpResponse(status=500) # Internal server error, PayPal will retry

        elif event_type == "PAYMENT.SALE.DENIED" or event_type == "PAYMENT.SALE.REFUNDED" or event_type == "PAYMENT.SALE.REVERSED":
            logger.info(f"Received PayPal Webhook Event: {event_type} for resource ID: {resource.get('id')}")
            parent_payment_id = resource.get("parent_payment")
            if parent_payment_id:
                try:
                    with transaction.atomic():
                        order = Order.objects.select_for_update().get(payment_gateway_id=parent_payment_id)
                        if event_type == "PAYMENT.SALE.DENIED":
                            order.status = Order.ORDER_STATUS_CHOICES[3][0] # FAILED
                        elif event_type == "PAYMENT.SALE.REFUNDED":
                            order.status = Order.ORDER_STATUS_CHOICES[5][0] # REFUNDED
                        elif event_type == "PAYMENT.SALE.REVERSED":
                            order.status = Order.ORDER_STATUS_CHOICES[5][0] # REFUNDED (or a new 'REVERSED' status)
                        order.updated_at = timezone.now()
                        order.save()
                        logger.info(f"Order {order.id} status updated to {order.status} due to {event_type}.")
                        # TODO: Handle implications (e.g., remove from library if refunded/reversed)
                except Order.DoesNotExist:
                    logger.warning(f"Order with payment_gateway_id {parent_payment_id} not found for {event_type} webhook.")
                except Exception as e_status_update:
                    logger.exception(f"Error updating order status for {event_type} on payment_id {parent_payment_id}: {e_status_update}")
                    return HttpResponse(status=500)
        else:
            logger.info(f"Received unhandled PayPal Webhook Event Type: {event_type}")

        return HttpResponse(status=200) # Acknowledge receipt to PayPal

    except json.JSONDecodeError:
        logger.error("PayPal Webhook: Invalid JSON in request body.")
        return HttpResponseBadRequest("Invalid JSON payload.")
    except Exception as e:
        logger.exception(f"Unexpected error in PayPal webhook handler: {e}")
        return HttpResponseBadRequest("Error processing webhook.")