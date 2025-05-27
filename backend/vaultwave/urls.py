from django.contrib import admin
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter # Keep this for other viewsets

from users.views import UserViewSet, UserProfileViewSet, RegisterView
from music.views import (
    GenreViewSet, ArtistViewSet, ReleaseViewSet,
    TrackViewSet, CommentViewSet, HighlightViewSet,
    stream_track_audio, GeneratedDownloadStatusViewSet
)
from playlists.views import PlaylistViewSet
# from cart.views import CartViewSet # We will include cart.urls directly
# from chat.views import ConversationViewSet # Included via chat.urls

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Main router for most apps
router = DefaultRouter() 

router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')

router.register(r'genres', GenreViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'releases', ReleaseViewSet, basename='release') 
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'comments', CommentViewSet)
router.register(r'highlights', HighlightViewSet)

router.register(r'playlists', PlaylistViewSet, basename='playlist')

router.register(r'generated-download-status', GeneratedDownloadStatusViewSet, basename='generated-download-status')

# Chat app's router is included via 'chat.urls' now.
# router.register(r'chat/conversations', ConversationViewSet, basename='conversation')


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Include router-generated URLs for most apps under /api/
    path('api/', include(router.urls)), 
    
    # Include app-specific URLs directly for more control if needed
    path('api/library/', include('library.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/music/', include('music.urls')), 
    path('api/tracks/<int:track_id>/stream/', stream_track_audio, name='track-stream'),
    
    # Add chat app urls
    path('api/chat/', include('chat.urls')), # Ensure this line exists and is correct

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), 
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/register/', RegisterView.as_view(), name='register'),

    path('api/shop/', include('shop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)