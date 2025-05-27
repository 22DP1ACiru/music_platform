from django.db.models import Q, Count, Max, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message
from music.models import Artist # Import Artist model
from .serializers import (
    ConversationSerializer, MessageSerializer, CreateMessageSerializer
)
from .permissions import IsConversationParticipant, IsMessageSenderOrParticipantReadOnly 

User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Annotate conversations with the subquery for last message time.
        # Also fetch related artist information.
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
            if sender.id == target_recipient_user.id: # Self-check already in serializer, but good to have defense
                 return Response({"error": "You cannot send a message to yourself as a user."}, status=status.HTTP_400_BAD_REQUEST)

        elif recipient_artist_id:
            try:
                target_related_artist = Artist.objects.select_related('user').get(id=recipient_artist_id)
                target_recipient_user = target_related_artist.user
                if sender.id == target_recipient_user.id : # Check if user is trying to send message to their own artist profile
                     return Response({"error": "You cannot send a message to your own artist profile."}, status=status.HTTP_400_BAD_REQUEST)
            except Artist.DoesNotExist:
                return Response({"error": "Recipient artist not found."}, status=status.HTTP_404_NOT_FOUND)
            except User.DoesNotExist: # Should not happen if artist.user is mandatory
                return Response({"error": "Artist owner not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # This case should be caught by serializer validation, but as a safeguard:
            return Response({"error": "No recipient specified."}, status=status.HTTP_400_BAD_REQUEST)

        # Find existing conversation between sender and target_recipient_user,
        # considering the target_related_artist context.
        # For a 1-on-1 DM, there should be exactly two participants.
        # If target_related_artist is specified, the conversation must match that context.
        # If target_related_artist is None, the conversation must also have related_artist=None.
        
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
                related_artist=target_related_artist # Set related_artist here
            )
            conversation.participants.add(sender, target_recipient_user)
        else:
            # Conversation exists. Logic in Message.save() handles acceptance if applicable.
            pass

        message_data = {
            'text': validated_data.get('text'),
            'message_type': validated_data.get('message_type', Message.MessageType.TEXT),
            'attachment': validated_data.get('attachment'),
        }
        
        message = Message(
            sender=sender,
            conversation=conversation,
            text=message_data['text'],
            message_type=message_data['message_type'],
            attachment=message_data['attachment']
        )
        
        try:
            message.full_clean() 
        except Exception as e: 
             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        message.save() 

        conv_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(conv_serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'], url_path='reply', serializer_class=MessageSerializer)
    def send_reply(self, request, pk=None):
        conversation = self.get_object() 
        
        message_serializer = MessageSerializer(data=request.data, context={'request': request})
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
            # Only mark as read if there are messages to mark and the conversation is accepted,
            # OR if the current user is the initiator (they can "read" their own pending messages in terms of UI state),
            # OR if the current user is the recipient of a pending request (they can see the first messages from initiator).
            # Actual "unread" status for notifications should primarily depend on `is_accepted`.
            if messages_to_mark_read.exists(): # Check if there's anything to update
                 messages_to_mark_read.update(is_read=True)
                 # Refresh conversation object to get latest unread count if it's used later
                 # For now, just updating is fine.

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
        # This method is part of ModelViewSet. For DMs, use 'send_initial_message'.
        # If direct conversation creation is allowed (e.g. for group chats later),
        # this is where you'd set the initiator.
        # For now, we can prevent direct POST to /conversations/
        return Response({"detail": "Use 'send-initial-message' or 'reply' actions."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # perform_update and perform_destroy can remain as they are if you don't need specific logic for them yet.
    # For now, updating a conversation's core fields (other than acceptance) isn't a primary user action.
    # Deleting a conversation should be handled carefully (soft delete? what happens to messages?).
    # Standard destroy will hard delete the conversation and cascade to messages.