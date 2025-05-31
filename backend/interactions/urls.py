from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FollowViewSet

router = DefaultRouter()
router.register(r'follows', FollowViewSet, basename='follow')
# Note: for `list_followers` and `list_following`, the pk in URL will be artist_id or user_id respectively.
# Example: /api/interactions/follows/{artist_pk}/followers/
# Example: /api/interactions/follows/{user_pk}/following/
# Example: /api/interactions/follows/my-following/
# Example: /api/interactions/follows/{artist_pk}/is-following/

urlpatterns = [
    path('', include(router.urls)),
]