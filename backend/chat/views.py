from django.db.models import Q, Count, Max, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes
from django.http import FileResponse, Http404, HttpResponseForbidden
import os
import mimetypes 
import logging 

from .models import Conversation, Message 
from music.models import Artist 
from .serializers import (
    ConversationSerializer, MessageSerializer, CreateMessageSerializer
)
from .permissions import IsConversationParticipant, IsMessageSenderOrParticipantReadOnly 

User = get_user_model()
logger = logging.getLogger(__name__) 

@api_view(['GET'])
@drf_permission_classes([permissions.IsAuthenticated]) 
def serve_chat_attachment(request, message_pk):
    message = get_object_or_404(Message, pk=message_pk)
    conversation = message.conversation

    if not request.user in conversation.participants.all():
        return Response({"detail": "You do not have permission to access this file."}, status=status.HTTP_403_FORBIDDEN)

    if not message.attachment or not message.attachment.name:
        return Response({"detail": "Attachment not found for this message."}, status=status.HTTP_404_NOT_FOUND)

    try:
        filename_for_download = message.original_attachment_filename or os.path.basename(message.attachment.name)
        
        content_type, encoding = mimetypes.guess_type(filename_for_download)
        if content_type is None:
            content_type = 'application/octet-stream'

        response = FileResponse(message.attachment.open('rb'), content_type=content_type)
        
        if request.query_params.get('download') == 'true':
            response['Content-Disposition'] = f'attachment; filename="{filename_for_download}"'
        else:
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
        ).select_related(
            'initiator_user__profile', 
            'initiator_user__artist_profile', 
            'initiator_artist_profile',    
            'related_artist_recipient'     
        ).prefetch_related(
            'participants__profile',                 
            'participants__artist_profile',          
            'messages__sender_user__profile',        
            'messages__sender_user__artist_profile', 
            'messages__sending_artist'               
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
        requesting_user = request.user
        
        chosen_initiator_identity_type = validated_data.get('initiator_identity_type', Conversation.IdentityType.USER)
        chosen_initiator_artist_profile_instance = validated_data.get('initiator_artist_profile_instance', None)

        recipient_user_id = validated_data.get('recipient_user_id')
        recipient_artist_id = validated_data.get('recipient_artist_id')
        
        target_recipient_user_model = None 
        target_related_artist_recipient_instance = None 

        if recipient_user_id:
            try:
                target_recipient_user_model = User.objects.get(id=recipient_user_id)
                if requesting_user.id == target_recipient_user_model.id:
                     return Response({"error": "You cannot send a message to yourself as a user."}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({"error": "Recipient user not found."}, status=status.HTTP_404_NOT_FOUND)
        elif recipient_artist_id:
            try:
                target_related_artist_recipient_instance = Artist.objects.select_related('user').get(id=recipient_artist_id)
                target_recipient_user_model = target_related_artist_recipient_instance.user # User who owns the target artist
                if requesting_user.id == target_recipient_user_model.id and chosen_initiator_identity_type == Conversation.IdentityType.USER:
                    return Response({"error": "You cannot send a message from your user account to your own artist profile."}, status=status.HTTP_400_BAD_REQUEST)
                if chosen_initiator_identity_type == Conversation.IdentityType.ARTIST and \
                   chosen_initiator_artist_profile_instance and \
                   chosen_initiator_artist_profile_instance == target_related_artist_recipient_instance:
                    return Response({"error": "An artist profile cannot send a message to itself."}, status=status.HTTP_400_BAD_REQUEST)
            except Artist.DoesNotExist: return Response({"error": "Recipient artist not found."}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist: return Response({"error": "Artist owner user not found. This should not happen."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else: return Response({"error": "No recipient specified."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent initiating a message from an artist profile to its own user account
        if chosen_initiator_identity_type == Conversation.IdentityType.ARTIST and \
           chosen_initiator_artist_profile_instance and \
           target_recipient_user_model == requesting_user and \
           not target_related_artist_recipient_instance: 
            return Response({"error": "You cannot send a message from your artist profile to your own user account."}, status=status.HTTP_400_BAD_REQUEST)

        # --- REVISED LOGIC FOR FINDING/CREATING UNIQUE CONVERSATION ---
        user1 = requesting_user
        user2 = target_recipient_user_model

        # Build the base query for participants: must contain user1 AND user2.
        base_query = Conversation.objects.filter(participants=user1).filter(participants=user2)

        # Further filter by the target artist recipient context
        if target_related_artist_recipient_instance:
            base_query = base_query.filter(
                related_artist_recipient=target_related_artist_recipient_instance
            )
        else: # Standard User-to-User DM (or Artist-to-User DM where target is a User)
            base_query = base_query.filter(
                related_artist_recipient__isnull=True
            )
        
        # Now, from these candidates, find one that ONLY has these two participants.
        conversation = None
        # Efficiently check if any candidate strictly has only 2 participants.
        # This avoids iterating in Python if possible.
        # We are looking for a conversation that includes user1, includes user2,
        # matches target_related_artist_recipient_instance, and has participant_count == 2.
        
        # The annotate and filter for count should be applied on the base_query itself.
        final_candidate_query = base_query.annotate(
            p_count=Count('participants')
        ).filter(p_count=2)
        
        conversation = final_candidate_query.first()
        
        if not conversation:
            conversation = Conversation.objects.create(
                initiator_user=requesting_user, 
                initiator_identity_type=chosen_initiator_identity_type,
                initiator_artist_profile=chosen_initiator_artist_profile_instance,
                is_accepted=False, 
                related_artist_recipient=target_related_artist_recipient_instance 
            )
            conversation.participants.add(user1, user2)
            logger.info(f"Created new conversation (ID: {conversation.id}) between {user1.username} and {user2.username}, target_artist: {target_related_artist_recipient_instance.name if target_related_artist_recipient_instance else 'N/A'}")
        else:
            logger.info(f"Found existing conversation (ID: {conversation.id}) between {user1.username} and {user2.username}, target_artist: {target_related_artist_recipient_instance.name if target_related_artist_recipient_instance else 'N/A'}")

        new_message = Message( 
            conversation=conversation,
            sender_user=requesting_user,
            sender_identity_type=chosen_initiator_identity_type, 
            sending_artist=chosen_initiator_artist_profile_instance,
            text=validated_data.get('text'),
            attachment=validated_data.get('attachment'),
            message_type=validated_data.get('message_type', Message.MessageType.TEXT),
        )
        new_message.save()
        
        conv_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(conv_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reply', serializer_class=MessageSerializer)
    def send_reply(self, request, pk=None):
        conversation = self.get_object() 
        requesting_user = request.user
        
        message_sender_identity_type: Message.SenderIdentity
        message_sending_artist_instance: Artist | None = None

        # Determine the identity for this reply message.
        # If the user has an artist profile that is relevant to this conversation context,
        # they might want to choose. For now, let's keep it simpler:
        
        # If I am the original initiator of this conversation.
        if conversation.initiator_user == requesting_user:
            # Reply with the same identity type used to initiate the conversation.
            if conversation.initiator_identity_type == Conversation.IdentityType.ARTIST:
                message_sender_identity_type = Message.SenderIdentity.ARTIST
                message_sending_artist_instance = conversation.initiator_artist_profile
            else: # USER
                message_sender_identity_type = Message.SenderIdentity.USER
                message_sending_artist_instance = None
        else: 
            # I am replying to a conversation someone else started.
            # If this conversation is directed TO MY ARTIST profile:
            if conversation.related_artist_recipient and \
               hasattr(requesting_user, 'artist_profile') and \
               requesting_user.artist_profile == conversation.related_artist_recipient:
                # I should reply AS this Artist.
                message_sender_identity_type = Message.SenderIdentity.ARTIST
                message_sending_artist_instance = conversation.related_artist_recipient # My artist profile
            else:
                # It's a User-to-User DM, or an Artist DMed me (as User). I reply as User.
                message_sender_identity_type = Message.SenderIdentity.USER
                message_sending_artist_instance = None
        
        message_data_for_serializer = {
            'text': request.data.get('text'),
            'attachment': request.data.get('attachment'), 
            'message_type': request.data.get('message_type', Message.MessageType.TEXT),
        }
        
        message_serializer_context = {'request': request} 
        message_serializer = MessageSerializer(data=message_data_for_serializer, context=message_serializer_context)
        
        if message_serializer.is_valid():
            message = message_serializer.save(
                sender_user=requesting_user, 
                conversation=conversation,
                sender_identity_type=message_sender_identity_type, 
                sending_artist=message_sending_artist_instance     
            )
            conv_serializer = ConversationSerializer(conversation, context={'request': request})
            return Response(conv_serializer.data, status=status.HTTP_201_CREATED)
        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        conversation = self.get_object() 
        messages = conversation.messages.select_related('sender_user', 'sending_artist').all().order_by('timestamp')
        
        can_mark_read = False
        if conversation.is_accepted:
            can_mark_read = True
        elif conversation.initiator_user != request.user: 
            can_mark_read = True

        if can_mark_read:
            messages_to_mark_read = messages.filter(is_read=False).exclude(sender_user=request.user)
            if messages_to_mark_read.exists(): 
                 count_updated = messages_to_mark_read.update(is_read=True)
                 logger.info(f"Marked {count_updated} messages as read in conversation {conversation.id} for user {request.user.username}")
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='accept-request')
    def accept_request(self, request, pk=None):
        conversation = self.get_object() 
        
        if conversation.initiator_user == request.user: 
            return Response({"error": "You cannot accept a conversation you initiated."}, status=status.HTTP_400_BAD_REQUEST)
        
        if conversation.is_accepted:
            return Response({"message": "Conversation already accepted."}, status=status.HTTP_200_OK)
        
        conversation.is_accepted = True
        conversation.save(update_fields=['is_accepted', 'updated_at']) 
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    def perform_create(self, serializer): 
        return Response({"detail": "Use 'send-initial-message' action to start a conversation."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)