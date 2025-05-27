from rest_framework import permissions

class IsConversationParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True
        # Instance must have an attribute named `participants`.
        return request.user in obj.participants.all()

class IsMessageSenderOrParticipantReadOnly(permissions.BasePermission):
    """
    Custom permission for messages.
    - Allows sender to do more (e.g., edit/delete if implemented).
    - Allows other participants to view.
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a Message instance
        # Allow read access if user is a participant of the message's conversation
        if request.method in permissions.SAFE_METHODS:
            return request.user in obj.conversation.participants.all()
        
        # Write permissions only allowed to the sender of the message
        return obj.sender == request.user