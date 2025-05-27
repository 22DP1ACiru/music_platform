from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from users.serializers import UserSerializer # Assuming a simple UserSerializer exists

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    # sender_id field for write operations is good if sender is not always request.user
    # but for chat, sender is always request.user when creating a message.
    # So, we'll set it in the view.
    attachment_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', # Usually set by view context or when creating message within a conversation
            'sender', 
            'text',
            'attachment', 
            'attachment_url', # For displaying attachment URL
            'message_type',
            'timestamp', 
            'is_read'
        ]
        read_only_fields = ['id', 'timestamp', 'sender', 'attachment_url', 'conversation'] # 'conversation' often set by view
        extra_kwargs = {
            # 'conversation': {'write_only': True, 'required': False}, # Make it not required in general serializer
            'attachment': {'write_only': True, 'required': False}, # Attachment is not always required
            'text': {'required': False, 'allow_blank': True, 'allow_null': True}
        }

    def get_attachment_url(self, obj):
        if obj.attachment and hasattr(obj.attachment, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None

    def validate(self, data):
        message_type = data.get('message_type', Message.MessageType.TEXT) # Default to TEXT if not provided
        text = data.get('text')
        attachment = data.get('attachment')

        if message_type == Message.MessageType.TEXT and not text:
            raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE) and not attachment:
            raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not attachment:
             raise serializers.ValidationError("Message must have either text or an attachment.")

        # Ensure text is None if only attachment is provided and type is not TEXT
        if attachment and not text and message_type != Message.MessageType.TEXT:
            data['text'] = None 
        
        # You might add validation for attachment file types here
        # e.g., if message_type is AUDIO, check file extension using attachment.name.
        if attachment:
            # Basic check: if message_type is AUDIO or VOICE, it should be an audio file.
            # This is a simplistic check, mimetypes or more robust checks are better.
            if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = getattr(attachment.content_type, 'split', lambda x: ['application/octet-stream']('/'))[0]
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    # We won't typically create conversations directly via this serializer's POST.
    # DM requests will be initiated by sending a message to a user.
    
    latest_message = MessageSerializer(read_only=True, source='messages.last') # Show latest message preview
    unread_count = serializers.SerializerMethodField()
    initiator = UserSerializer(read_only=True)
    other_participant_username = serializers.SerializerMethodField()


    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 'initiator',
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_username' # Helpful for frontend display
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 'initiator']
        # `is_accepted` might be updatable via a specific action.

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            # Count messages in this conversation not sent by the current user and are unread
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0 # Or None, depending on how you want to handle unauthenticated access to this (if ever)
        
    def get_other_participant_username(self, obj):
        user = self.context.get('request').user
        if user and obj.participants.count() == 2: # Assuming 1-on-1 chats mainly
            other_participant = obj.get_other_participant(user)
            return other_participant.username if other_participant else None
        return None

class CreateMessageSerializer(serializers.Serializer): # Not a ModelSerializer
    """
    Serializer for creating a new message, potentially initiating a conversation.
    """
    recipient_id = serializers.IntegerField(write_only=True, required=True)
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attachment = serializers.FileField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)

    def validate_recipient_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Recipient user does not exist.")
        # Prevent sending messages to oneself, if that's a requirement
        # request = self.context.get('request')
        # if request and request.user.id == value:
        #     raise serializers.ValidationError("You cannot send a message to yourself.")
        return value

    def validate(self, data):
        message_type = data.get('message_type', Message.MessageType.TEXT)
        text = data.get('text')
        attachment = data.get('attachment')

        if message_type == Message.MessageType.TEXT and not text:
            raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE) and not attachment:
            raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not attachment:
            raise serializers.ValidationError("Message must have either text or an attachment.")
        
        if attachment:
             if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = getattr(attachment.content_type, 'split', lambda x: ['application/octet-stream']('/'))[0]
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file."})
        return data