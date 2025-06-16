from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArtistStatsViewSet, UserStatsViewSet # Add UserStatsViewSet

router = DefaultRouter()
router.register(r'artist', ArtistStatsViewSet, basename='artist-stats') 
router.register(r'user', UserStatsViewSet, basename='user-stats') # New registration

urlpatterns = [
    path('', include(router.urls)),
]