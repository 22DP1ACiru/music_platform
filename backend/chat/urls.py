from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet #, MessageViewSet (if you add it)

router = DefaultRouter()
# Register ConversationViewSet. URLs will be like /api/chat/conversations/, /api/chat/conversations/{pk}/
router.register(r'conversations', ConversationViewSet, basename='conversation')

# If you want direct access to messages outside of a conversation context (less common for typical chat)
# router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]