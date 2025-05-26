from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LibraryViewSet

router = DefaultRouter()
# The base_name 'library' will generate URL names like 'library-list', 'library-detail', 'library-add-item-to-library'
router.register(r'', LibraryViewSet, basename='library-item') 

urlpatterns = [
    path('', include(router.urls)),
]