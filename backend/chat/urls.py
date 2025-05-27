from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, serve_chat_attachment # Import the new view

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
    # New URL for downloading chat attachments
    path('messages/<int:message_pk>/download/', serve_chat_attachment, name='chat-attachment-download'),
]