from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, UserProfileViewSet
from music.views import (
    GenreViewSet, ArtistViewSet, ReleaseViewSet,
    TrackViewSet, CommentViewSet, HighlightViewSet
)
from playlists.views import PlaylistViewSet

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='userprofile')

router.register(r'genres', GenreViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'releases', ReleaseViewSet, basename='release')
router.register(r'tracks', TrackViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'highlights', HighlightViewSet)

router.register(r'playlists', PlaylistViewSet, basename='playlist')


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include(router.urls)),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)