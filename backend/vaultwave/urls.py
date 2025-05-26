from django.contrib import admin
from django.urls import path, include # Ensure include is imported
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, UserProfileViewSet, RegisterView
from music.views import (
    GenreViewSet, ArtistViewSet, ReleaseViewSet,
    TrackViewSet, CommentViewSet, HighlightViewSet,
    stream_track_audio, GeneratedDownloadStatusViewSet
)
from playlists.views import PlaylistViewSet
# from shop.views import ProductViewSet # Example if you add ProductViewSet (currently not used)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

router = DefaultRouter() # This is the main API router - DEFINED HERE

router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')

router.register(r'genres', GenreViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'releases', ReleaseViewSet, basename='release') # For public release listings & details
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'comments', CommentViewSet)
router.register(r'highlights', HighlightViewSet)

router.register(r'playlists', PlaylistViewSet, basename='playlist')
# router.register(r'products', ProductViewSet, basename='product') # If you add ProductViewSet

# For checking download status of ANY generated download for the user
router.register(r'generated-download-status', GeneratedDownloadStatusViewSet, basename='generated-download-status')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)), # Include all router-generated URLs under /api/

    path('api/library/', include('library.urls')),

    path('api/music/', include('music.urls')), # For specific non-router music paths like direct file serving
    path('api/tracks/<int:track_id>/stream/', stream_track_audio, name='track-stream'),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), # For browsable API login
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/register/', RegisterView.as_view(), name='register'),

    path('api/shop/', include('shop.urls')), # Added shop URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)