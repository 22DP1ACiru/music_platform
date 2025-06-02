from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter 

from users.views import UserViewSet, UserProfileViewSet, RegisterView
from music.views import (
    GenreViewSet, ArtistViewSet, ReleaseViewSet,
    TrackViewSet, CommentViewSet, HighlightViewSet, 
    stream_track_audio, GeneratedDownloadStatusViewSet
)
from interactions.views import FollowViewSet # New import
from notifications.views import NotificationViewSet # New import

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
router.register(r'highlights', HighlightViewSet, basename='highlight') 

router.register(r'generated-download-status', GeneratedDownloadStatusViewSet, basename='generated-download-status')

# New routers for interactions and notifications
router.register(r'interactions', FollowViewSet, basename='interaction-follow') # Base name 'interaction-follow' for clarity
router.register(r'notifications', NotificationViewSet, basename='notification')


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/', include(router.urls)), 
    
    path('api/playlists/', include('playlists.urls')), 
    path('api/library/', include('library.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/music/', include('music.urls')), 
    path('api/tracks/<int:track_id>/stream/', stream_track_audio, name='track-stream'),
    
    path('api/chat/', include('chat.urls')), 
    # interactions and notifications are now part of the main router

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), 
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/register/', RegisterView.as_view(), name='register'),

    path('api/shop/', include('shop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)