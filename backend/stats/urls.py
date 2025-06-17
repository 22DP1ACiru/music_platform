from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArtistStatsViewSet, UserStatsViewSet, AdminStatsViewSet

router = DefaultRouter()
router.register(r'artist', ArtistStatsViewSet, basename='artist-stats') 
router.register(r'user', UserStatsViewSet, basename='user-stats')
router.register(r'admin', AdminStatsViewSet, basename='admin-stats')

urlpatterns = [
    path('', include(router.urls)),
]