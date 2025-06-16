from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArtistStatsViewSet

router = DefaultRouter()
# Using basename because we are using ViewSet and not ModelViewSet
router.register(r'artist', ArtistStatsViewSet, basename='artist-stats') 

urlpatterns = [
    path('', include(router.urls)),
]