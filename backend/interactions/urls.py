from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FollowViewSet

router = DefaultRouter()
router.register(r'follows', FollowViewSet, basename='follow')
# The custom URL paths in FollowViewSet actions like 'artist/(?P<artist_pk>[0-9]+)/followers'
# will be correctly appended to '/api/interactions/follows/'.
# e.g. /api/interactions/follows/artist/1/followers/

urlpatterns = [
    path('', include(router.urls)),
]