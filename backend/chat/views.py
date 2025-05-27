from django.db.models import Q, Count, Max, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes
from django.http import FileResponse, Http404, HttpResponseForbidden
import os
import mimetypes 
import logging # Added logging

from .models import Conversation, Message
from music.models import Artist 
from .serializers import (
    ConversationSerializer, MessageSerializer, CreateMessageSerializer
)
from .permissions import IsConversationParticipant, IsMessageSenderOrParticipantReadOnly 

User = get_user_model()
logger = logging.getLogger(__name__) # Added logger

@api_view(['GET'])
@drf_permission_classes([permissions.IsAuthenticated]) # Keep IsAuthenticated
def serve_chat_attachment(request, message_pk):
    message = get_object_or_404(Message, pk=message_pk)
    conversation = message.conversation

    if not request.user in conversation.participants.all():
        # Using DRF Response for API consistency
        return Response({"detail": "You do not have permission to access this file."}, status=status.HTTP_403_FORBIDDEN)

    if not message.attachment or not message.attachment.name:
        # Using DRF Response
        return Response({"detail": "Attachment not found for this message."}, status=status.HTTP_404_NOT_FOUND)

    try:
        filename_for_download = message.original_attachment_filename or os.path.basename(message.attachment.name)
        
        content_type, encoding = mimetypes.guess_type(filename_for_download)
        if content_type is None:
            content_type = 'application/octet-stream'

        response = FileResponse(message.attachment.open('rb'), content_type=content_type)
        # Content-Disposition for download should ideally be set here for the download action,
        # but for the <audio> tag, we don't want to force download.
        # For the blob approach, the FE controls the "download" part.
        # So, we can make this conditional or have two endpoints.
        # For now, let's assume the FE will handle download triggering.
        # If the 'download' query param is present, force download.
        if request.query_params.get('download') == 'true':
            response['Content-Disposition'] = f'attachment; filename="{filename_for_download}"'
        else:
            # For streaming to <audio> tag, 'inline' or no disposition is better.
            # However, since FE will fetch as blob, this might not be strictly necessary.
            # For safety, let's make it inline if not explicitly downloading.
            response['Content-Disposition'] = f'inline; filename="{filename_for_download}"'

        return response
    except FileNotFoundError:
        return Response({"detail": "File not found in storage."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error serving chat attachment for message {message_pk}: {e}") 
        return Response({"detail": "Error serving file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            participants=user
        ).select_related('initiator', 'related_artist').prefetch_related(
            'participants', 'messages__sender'
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time', '-updated_at')

    def get_permissions(self):
        if self.action in ['list_messages', 'send_reply', 'accept_request', 'retrieve', 'partial_update', 'update', 'destroy']:
            return [permissions.IsAuthenticated(), IsConversationParticipant()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='send-initial-message', serializer_class=CreateMessageSerializer)
    def send_initial_message(self, request):
        create_serializer = CreateMessageSerializer(data=request.data, context={'request': request})
        if not create_serializer.is_valid():
            return Response(create_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = create_serializer.validated_data
        recipient_user_id = validated_data.get('recipient_user_id')
        recipient_artist_id = validated_data.get('recipient_artist_id')
        sender = request.user
        
        target_recipient_user = None
        target_related_artist = None

        if recipient_user_id:
            try:
                target_recipient_user = User.objects.get(id=recipient_user_id)
            except User.DoesNotExist:
                return Response({"error": "Recipient user not found."}, status=status.HTTP_404_NOT_FOUND)
            if sender.id == target_recipient_user.id: 
                 return Response({"error": "You cannot send a message to yourself as a user."}, status=status.HTTP_400_BAD_REQUEST)

        elif recipient_artist_id:
            try:
                target_related_artist = Artist.objects.select_related('user').get(id=recipient_artist_id)
                target_recipient_user = target_related_artist.user
                if sender.id == target_recipient_user.id : 
                     return Response({"error": "You cannot send a message to your own artist profile."}, status=status.HTTP_400_BAD_REQUEST)
            except Artist.DoesNotExist:
                return Response({"error": "Recipient artist not found."}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist: 
                return Response({"error": "Artist owner not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": "No recipient specified."}, status=status.HTTP_400_BAD_REQUEST)
        
        conversation_query = Conversation.objects.filter(
            participants=sender
        ).filter(
            participants=target_recipient_user
        ).annotate(
            num_participants=Count('participants')
        ).filter(
            num_participants=2 
        )

        if target_related_artist:
            conversation_query = conversation_query.filter(related_artist=target_related_artist)
        else:
            conversation_query = conversation_query.filter(related_artist__isnull=True)
        
        conversation = conversation_query.first()
            
        if not conversation:
            conversation = Conversation.objects.create(
                initiator=sender, 
                is_accepted=False,
                related_artist=target_related_artist 
            )
            conversation.participants.add(sender, target_recipient_user)
        
        message_payload = {
            'text': validated_data.get('text'),
            'message_type': validated_data.get('message_type', Message.MessageType.TEXT),
            'attachment': validated_data.get('attachment'), 
            'conversation': conversation.id, 
        }
        message_serializer_context = {'request': request, 'sender': sender, 'conversation': conversation}
        message_serializer = MessageSerializer(data=message_payload, context=message_serializer_context)

        if not message_serializer.is_valid():
             return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message = message_serializer.save(sender=sender, conversation=conversation)

        conv_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(conv_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reply', serializer_class=MessageSerializer)
    def send_reply(self, request, pk=None):
        conversation = self.get_object() 
        
        message_serializer_context = {'request': request, 'sender': request.user, 'conversation': conversation}
        message_serializer = MessageSerializer(data=request.data, context=message_serializer_context)
        
        if message_serializer.is_valid():
            message_serializer.save(sender=request.user, conversation=conversation)
            conv_serializer = ConversationSerializer(conversation, context={'request': request})
            return Response(conv_serializer.data, status=status.HTTP_201_CREATED)
        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        conversation = self.get_object() 
        messages = conversation.messages.all().order_by('timestamp')
        
        can_mark_read = conversation.is_accepted or \
                        (conversation.initiator == request.user) or \
                        (not conversation.is_accepted and conversation.get_other_participant(conversation.initiator) == request.user)

        if can_mark_read:
            messages_to_mark_read = messages.filter(is_read=False).exclude(sender=request.user)
            if messages_to_mark_read.exists(): 
                 messages_to_mark_read.update(is_read=True)
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='accept-request')
    def accept_request(self, request, pk=None):
        conversation = self.get_object() 
        
        if conversation.initiator == request.user:
            return Response({"error": "You cannot accept a conversation you initiated."}, status=status.HTTP_400_BAD_REQUEST)
        if conversation.is_accepted:
            return Response({"message": "Conversation already accepted."}, status=status.HTTP_200_OK)
        
        conversation.is_accepted = True
        conversation.save(update_fields=['is_accepted', 'updated_at'])
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        return Response({"detail": "Use 'send-initial-message' or 'reply' actions."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)