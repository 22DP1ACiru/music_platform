from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet

router = DefaultRouter()
# Register CartViewSet at the root of this app's router (empty string for prefix)
# Actions within CartViewSet will now be directly under /api/cart/
# e.g., my-cart action becomes /api/cart/my-cart/
# e.g., add-item action becomes /api/cart/add-item/
router.register(r'', CartViewSet, basename='cart') # Use r'' for the prefix

urlpatterns = [
    path('', include(router.urls)), # Include the router directly at the app's root
]