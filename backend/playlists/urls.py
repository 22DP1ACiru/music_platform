from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlaylistViewSet

router = DefaultRouter()
router.register(r'', PlaylistViewSet, basename='playlist') # Register at the root of this app's router

urlpatterns = [
    path('', include(router.urls)),
]