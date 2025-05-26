from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
# You can add ProductViewSet later if you want to list products directly via API

urlpatterns = [
    path('', include(router.urls)),
]