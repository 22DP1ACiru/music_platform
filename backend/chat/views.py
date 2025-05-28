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
        
        # Current action's sender details
        current_sender_user = request.user
        current_sender_identity_type = validated_data.get('initiator_identity_type', Conversation.IdentityType.USER)
        current_sender_artist_profile = validated_data.get('initiator_artist_profile_instance', None)

        # Current action's recipient details
        recipient_user_id = validated_data.get('recipient_user_id')
        recipient_artist_id = validated_data.get('recipient_artist_id')
        
        actual_recipient_user_model = None # The User model instance of the other party
        targeted_recipient_artist_profile = None # If recipient is an Artist profile, this is it
        
        if recipient_user_id:
            try: actual_recipient_user_model = User.objects.get(id=recipient_user_id)
            except User.DoesNotExist: return Response({"error": "Recipient user not found."}, status=status.HTTP_404_NOT_FOUND)
        elif recipient_artist_id:
            try:
                targeted_recipient_artist_profile = Artist.objects.select_related('user').get(id=recipient_artist_id)
                actual_recipient_user_model = targeted_recipient_artist_profile.user 
            except Artist.DoesNotExist: return Response({"error": "Recipient artist not found."}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist: return Response({"error": "Artist owner user not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else: return Response({"error": "No recipient specified."}, status=status.HTTP_400_BAD_REQUEST)

        # --- Self-messaging Validations ---
        if current_sender_user == actual_recipient_user_model: # Both underlying users are the same
            is_sender_user_identity = current_sender_identity_type == Conversation.IdentityType.USER
            is_sender_artist_identity = current_sender_identity_type == Conversation.IdentityType.ARTIST
            is_recipient_artist_target = targeted_recipient_artist_profile is not None

            if is_sender_user_identity and not is_recipient_artist_target: # User to Self User
                return Response({"error": "You cannot send a message to yourself as a user."}, status=status.HTTP_400_BAD_REQUEST)
            if is_sender_user_identity and is_recipient_artist_target and targeted_recipient_artist_profile.user == current_sender_user: # User to Own Artist
                return Response({"error": "You cannot send a message from your user account to your own artist profile."}, status=status.HTTP_400_BAD_REQUEST)
            if is_sender_artist_identity and current_sender_artist_profile and not is_recipient_artist_target: # Artist to Own User
                return Response({"error": "You cannot send a message from your artist profile to your own user account."}, status=status.HTTP_400_BAD_REQUEST)
            if is_sender_artist_identity and current_sender_artist_profile and is_recipient_artist_target and current_sender_artist_profile == targeted_recipient_artist_profile: # Artist to Self Artist
                return Response({"error": "An artist profile cannot send a message to itself."}, status=status.HTTP_400_BAD_REQUEST)
        
        # --- Find Existing Conversation ---
        # A conversation is uniquely defined by the two Users involved and the "channel type"
        # Channel type is determined by:
        #   - Who initiated AS what identity (User or specific Artist)
        #   - Who was targeted AS what identity (User or specific Artist)

        # First, get all conversations involving *exactly* these two users
        conversations_between_users = Conversation.objects.annotate(
            p_count=Count('participants')
        ).filter(
            p_count=2,
            participants=current_sender_user
        ).filter(
            participants=actual_recipient_user_model
        )

        found_conversation = None
        for conv_candidate in conversations_between_users:
            # Case A: current_sender initiated this candidate conv, check if identities match
            if conv_candidate.initiator_user == current_sender_user and \
               conv_candidate.initiator_identity_type == current_sender_identity_type and \
               conv_candidate.initiator_artist_profile == current_sender_artist_profile and \
               conv_candidate.related_artist_recipient == targeted_recipient_artist_profile:
                found_conversation = conv_candidate
                break
            
            # Case B: actual_recipient_user_model initiated this candidate conv.
            # Check if the candidate's initiation matches the *inverse* of the current send attempt.
            #   - candidate's initiator_user must be actual_recipient_user_model
            #   - candidate's initiator_identity_type must match how actual_recipient_user_model is being targeted now
            #   - candidate's initiator_artist_profile must match targeted_recipient_artist_profile (if any)
            #   - candidate's related_artist_recipient must match current_sender_artist_profile (if any)
            
            # Determine the identity of the actual_recipient_user_model if they were the initiator
            recipient_as_initiator_identity_type = Conversation.IdentityType.ARTIST if targeted_recipient_artist_profile else Conversation.IdentityType.USER
            recipient_as_initiator_artist_profile = targeted_recipient_artist_profile # This is their artist profile if they are an artist target

            if conv_candidate.initiator_user == actual_recipient_user_model and \
               conv_candidate.initiator_identity_type == recipient_as_initiator_identity_type and \
               conv_candidate.initiator_artist_profile == recipient_as_initiator_artist_profile and \
               conv_candidate.related_artist_recipient == current_sender_artist_profile: # Target was current sender's artist (if any)
                found_conversation = conv_candidate
                break
        
        if not found_conversation:
            found_conversation = Conversation.objects.create(
                initiator_user=current_sender_user, 
                initiator_identity_type=current_sender_identity_type,
                initiator_artist_profile=current_sender_artist_profile,
                is_accepted=False, 
                related_artist_recipient=targeted_recipient_artist_profile 
            )
            found_conversation.participants.add(current_sender_user, actual_recipient_user_model)
            logger.info(f"CREATED New Conversation (ID: {found_conversation.id}): "
                        f"Initiator: {current_sender_user.username} (as {current_sender_identity_type}, ArtistID: {current_sender_artist_profile.id if current_sender_artist_profile else 'N/A'}), "
                        f"Recipient User: {actual_recipient_user_model.username}, Recipient Artist Target: {targeted_recipient_artist_profile.name if targeted_recipient_artist_profile else 'N/A (User Target)'}")
        else:
            logger.info(f"FOUND Existing Conversation (ID: {found_conversation.id})")

        new_message = Message( 
            conversation=found_conversation,
            sender_user=current_sender_user,
            sender_identity_type=current_sender_identity_type, 
            sending_artist=current_sender_artist_profile,
            text=validated_data.get('text'),
            attachment=validated_data.get('attachment'),
            message_type=validated_data.get('message_type', Message.MessageType.TEXT),
        )
        new_message.save()
        
        conv_serializer = ConversationSerializer(found_conversation, context={'request': request})
        return Response(conv_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reply', serializer_class=MessageSerializer)
    def send_reply(self, request, pk=None):
        conversation = self.get_object() 
        requesting_user = request.user
        
        message_sender_identity_type: Message.SenderIdentity
        message_sending_artist_instance: Artist | None = None
        
        if conversation.initiator_user == requesting_user:
            if conversation.initiator_identity_type == Conversation.IdentityType.ARTIST:
                message_sender_identity_type = Message.SenderIdentity.ARTIST
                message_sending_artist_instance = conversation.initiator_artist_profile
            else: 
                message_sender_identity_type = Message.SenderIdentity.USER
                message_sending_artist_instance = None
        else: 
            if conversation.related_artist_recipient and \
               hasattr(requesting_user, 'artist_profile') and \
               requesting_user.artist_profile == conversation.related_artist_recipient:
                message_sender_identity_type = Message.SenderIdentity.ARTIST
                message_sending_artist_instance = conversation.related_artist_recipient
            else:
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