from django.db.models import Q, Count, Max
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer, MessageSerializer, CreateMessageSerializer
)
from .permissions import IsConversationParticipant, IsMessageSenderOrParticipantReadOnly # Updated permission

User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    # Default permission: user must be authenticated. Object-level permissions handled by IsConversationParticipant.
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Return conversations where the user is a participant.
        # Further filtering for "pending requests I sent/received" vs "accepted chats"
        # can be done here or by separate endpoints/filters on frontend.
        # Show:
        # 1. Accepted conversations.
        # 2. Pending requests initiated by me.
        # 3. Pending requests where I am a participant but not the initiator (requests to me).
        return Conversation.objects.filter(
            Q(participants=user) & 
            (
                Q(is_accepted=True) | 
                Q(initiator=user) | # Pending requests sent by me
                (Q(is_accepted=False) & ~Q(initiator=user)) # Pending requests received by me
            )
        ).distinct().prefetch_related('participants', 'messages__sender').annotate(
            last_message_time=Max('messages__timestamp') # For ordering
        ).order_by('-last_message_time', '-updated_at')


    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list_messages', 'send_reply', 'accept_request', 'retrieve', 'partial_update', 'update', 'destroy']:
            # For actions on a specific conversation, ensure user is a participant.
            return [permissions.IsAuthenticated(), IsConversationParticipant()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='send-initial-message', serializer_class=CreateMessageSerializer)
    def send_initial_message(self, request):
        """
        Send a message to a user. Creates a new conversation (DM request) if one doesn't exist,
        or adds to an existing one if it's already accepted or if sender is replying to a request to them.
        """
        create_serializer = CreateMessageSerializer(data=request.data, context={'request': request})
        if not create_serializer.is_valid():
            return Response(create_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = create_serializer.validated_data
        recipient_id = validated_data['recipient_id']
        sender = request.user

        if sender.id == recipient_id:
            return Response({"error": "You cannot send a message to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({"error": "Recipient not found."}, status=status.HTTP_404_NOT_FOUND)

        # Try to find an existing 1-on-1 conversation (pending or accepted)
        # Corrected line: Chain filter calls for multiple participants
        conversation = Conversation.objects.filter(
            participants=sender
        ).filter(
            participants=recipient
        ).annotate(
            num_participants=Count('participants')
        ).filter(
            num_participants=2 # Ensures it's exactly a 2-person conversation
        ).first()
            
        is_new_conversation = False
        if not conversation:
            # Create a new conversation, initiated by sender, initially not accepted
            conversation = Conversation.objects.create(initiator=sender, is_accepted=False)
            conversation.participants.add(sender, recipient)
            is_new_conversation = True
        else:
            # Conversation exists. If sender is the recipient of a pending request, sending a message accepts it.
            # This is handled by Message.save() method.
            pass


        message_data = {
            'text': validated_data.get('text'),
            'message_type': validated_data.get('message_type', Message.MessageType.TEXT),
            'attachment': validated_data.get('attachment'),
            # sender will be set in save() override of MessageSerializer or here
            # conversation will be set
        }
        
        # Use MessageSerializer to create the message
        # We need to pass the conversation instance to the message
        # The MessageSerializer expects `conversation` to be an ID or instance.
        # It's better to set it directly here.
        
        message_serializer_context = {'request': request}
        message = Message(
            sender=sender,
            conversation=conversation,
            text=message_data['text'],
            message_type=message_data['message_type'],
            attachment=message_data['attachment']
        )
        
        # Validate message content before saving (MessageSerializer can do this if data is passed to it)
        # Or rely on Message.save() internal validation
        try:
            message.full_clean() # This calls model's clean() method
        except Exception as e: # Django's ValidationError
             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        message.save() # This will trigger conversation.update_timestamp() and acceptance logic

        # Return the conversation details (which includes latest message)
        conv_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(conv_serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'], url_path='reply', serializer_class=MessageSerializer)
    def send_reply(self, request, pk=None):
        conversation = self.get_object() # Checks IsConversationParticipant
        
        # Message.save() handles auto-acceptance if applicable.
        # It also handles updating the conversation timestamp.
        
        message_serializer = MessageSerializer(data=request.data, context={'request': request})
        if message_serializer.is_valid():
            # Pass sender and conversation directly to save to ensure they are set
            message_serializer.save(sender=request.user, conversation=conversation)
            
            # Return the full conversation to update the client
            conv_serializer = ConversationSerializer(conversation, context={'request': request})
            return Response(conv_serializer.data, status=status.HTTP_201_CREATED)
        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        conversation = self.get_object() # Checks IsConversationParticipant
        messages = conversation.messages.all().order_by('timestamp')
        
        # Mark messages as read by the current user (if they are not the sender)
        # and if the conversation is accepted or if the user is the initiator (can read their own pending).
        # More simply: if user can view the conversation, they can read messages.
        # The acceptance part: a message isn't really "unread" for recipient if request isn't accepted.
        # However, once accepted, or if it's the user reading their own sent messages, they are "read".
        
        # Only mark as read if conversation is accepted OR if the user is the initiator (viewing their pending request)
        # OR if the user is the recipient of a pending request (they can see the first message)
        can_mark_read = conversation.is_accepted or \
                        (conversation.initiator == request.user) or \
                        (not conversation.is_accepted and conversation.get_other_participant(conversation.initiator) == request.user)

        if can_mark_read:
            messages_to_mark_read = messages.filter(is_read=False).exclude(sender=request.user)
            updated_count = messages_to_mark_read.update(is_read=True)
            if updated_count > 0 and conversation.is_accepted:
                 # Potentially trigger notification to sender that messages were read, if desired.
                 pass

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='accept-request')
    def accept_request(self, request, pk=None):
        conversation = self.get_object() # User must be a participant
        
        # Only non-initiator can accept.
        if conversation.initiator == request.user:
            return Response({"error": "You cannot accept a conversation you initiated."}, status=status.HTTP_400_BAD_REQUEST)
        if conversation.is_accepted:
            return Response({"message": "Conversation already accepted."}, status=status.HTTP_200_OK)
        
        conversation.is_accepted = True
        conversation.save(update_fields=['is_accepted', 'updated_at'])
        
        # Optionally mark initiator's messages as read by this user upon acceptance
        # conversation.messages.filter(sender=conversation.initiator, is_read=False).update(is_read=True)
        
        serializer = self.get_serializer(conversation) # Return updated conversation
        return Response(serializer.data)

    # To delete a message (example, if IsMessageSenderOrParticipantReadOnly is adapted)
    # @action(detail=True, methods=['delete'], url_path='messages/(?P<message_pk>[0-9]+)', permission_classes=[IsMessageSenderOrParticipantReadOnly])
    # def delete_message(self, request, pk=None, message_pk=None):
    #     conversation = self.get_object()
    #     message = get_object_or_404(Message, pk=message_pk, conversation=conversation)
    #     self.check_object_permissions(request, message) # Check if user is sender
    #     if message.sender != request.user:
    #          return Response({"error": "You can only delete your own messages."}, status=status.HTTP_403_FORBIDDEN)
    #     message.delete()
    #     return Response(status=status.HTTP_204_NO_CONTENT)

    # perform_create, perform_update, perform_destroy for Conversation model itself:
    # Standard POST to /conversations/ for creating might be disabled if all convos are DMs via send_initial_message.
    # Updating a conversation (e.g. changing participants for group chat - not yet supported)
    # Deleting a conversation - should it delete all messages? Or just participant's link to it?
    # For now, let's assume these are not primary actions for 1-on-1 DMs.
    
    def perform_create(self, serializer):
        # This method is part of ModelViewSet. For DMs, use 'send_initial_message'.
        # If direct conversation creation is allowed (e.g. for group chats later),
        # this is where you'd set the initiator.
        # For now, we can prevent direct POST to /conversations/
        return Response({"detail": "Use 'send-initial-message' to start a conversation."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        # Similarly, direct PUT/PATCH to a conversation might be restricted.
        # Actions like 'accept_request' handle specific state changes.
        instance = serializer.save()
        # Custom logic after update if needed

    def perform_destroy(self, instance):
        # Logic for deleting a conversation. Consider implications (e.g., soft delete, archiving)
        # For now, default is hard delete.
        instance.delete()