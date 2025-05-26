from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Product
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer
from library.models import UserLibraryItem # To check if item is already owned

class CartViewSet(viewsets.GenericViewSet): # Not ModelViewSet as we have custom actions
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer # Default for documentation

    def get_queryset(self):
        # This queryset is not directly used by list/retrieve, but good practice
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-cart')
    def my_cart(self, request):
        """
        Retrieve the current authenticated user's cart.
        Creates a cart if one doesn't exist.
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=AddToCartSerializer, url_path='add-item')
    def add_item(self, request):
        """
        Add a product to the user's cart.
        If the item is already in the cart, this action currently does nothing (idempotent for existing).
        Could be changed to update quantity if quantity > 1 was supported.
        """
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = AddToCartSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            price_override = serializer.validated_data.get('price_override')

            product = get_object_or_404(Product, pk=product_id, is_active=True)

            # Prevent adding if already in library
            if product.release and UserLibraryItem.objects.filter(user=request.user, release=product.release).exists():
                return Response(
                    {"detail": f"'{product.name}' is already in your library and cannot be added to the cart."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check cart currency consistency (simplified: first item sets currency)
            if cart.items.exists():
                current_cart_currency = cart.items.first().product.currency
                if product.currency != current_cart_currency:
                    return Response(
                        {"detail": f"Cannot add item with currency {product.currency} to cart with currency {current_cart_currency}. Please clear cart or checkout existing items first."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'price_override': price_override}
            )

            if not created: # Item already exists
                # If it's an NYP item and a new price_override is provided, update it.
                if product.release and product.release.pricing_model == Release.PricingModel.NAME_YOUR_PRICE and price_override is not None:
                    if cart_item.price_override != price_override:
                        cart_item.price_override = price_override
                        cart_item.save()
                        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)
                return Response(
                    {"detail": f"'{product.name}' is already in your cart."},
                    status=status.HTTP_200_OK # Or 409 Conflict, but 200 is fine for idempotency
                )
            
            return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<product_id>[0-9]+)')
    def remove_item(self, request, product_id=None):
        """
        Remove a product from the user's cart.
        Uses product_id for removal.
        """
        cart = get_object_or_404(Cart, user=request.user)
        product = get_object_or_404(Product, pk=product_id)
        
        cart_item = get_object_or_404(CartItem, cart=cart, product=product)
        cart_item.delete()
        
        # Check if cart became empty, which might affect currency "memory" if implemented that way.
        # For now, just return updated cart.
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='clear') # Using POST for action, could be DELETE
    def clear_cart(self, request):
        """
        Remove all items from the user's cart.
        """
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)