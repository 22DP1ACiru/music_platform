from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Product, Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer # Add OrderItemCreateSerializer indirectly via OrderCreateSerializer
from rest_framework.permissions import IsAuthenticated

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        # Users can only see their own orders
        user = self.request.user
        if user.is_authenticated:
            return Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
        return Order.objects.none() # Should not happen due to IsAuthenticated

    def perform_create(self, serializer):
        # User is automatically set from the request context in the serializer
        serializer.save()

    # Add other actions if needed, like retrieving a specific order, cancelling (if applicable), etc.
    # Default list, retrieve, create are provided by ModelViewSet.
    # Update/delete of orders might be restricted.