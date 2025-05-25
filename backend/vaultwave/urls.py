from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, UserProfileViewSet, RegisterView
from music.views import (
    GenreViewSet, ArtistViewSet, ReleaseViewSet,
    TrackViewSet, CommentViewSet, HighlightViewSet,
    stream_track_audio # <-- IMPORT THE NEW STREAM VIEW
)
from playlists.views import PlaylistViewSet

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')

router.register(r'genres', GenreViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'releases', ReleaseViewSet, basename='release')
router.register(r'tracks', TrackViewSet) # This handles /api/tracks/ and /api/tracks/{id}/ for CRUD
router.register(r'comments', CommentViewSet)
router.register(r'highlights', HighlightViewSet)

router.register(r'playlists', PlaylistViewSet, basename='playlist')


urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Router-generated API Endpoints ---
    path('api/', include(router.urls)),

    # --- Custom API Endpoints for music app ---
    # Add the track streaming URL directly here, prefixed with 'api/'
    path('api/tracks/<int:track_id>/stream/', stream_track_audio, name='track-stream'), # <-- ADDED HERE

    # --- Browsable API ---
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # --- JWT Authentication ---
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # --- User Registration ---
    path('api/register/', RegisterView.as_view(), name='register'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)