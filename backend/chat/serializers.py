from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from users.serializers import UserSerializer # Assuming a simple UserSerializer exists

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachment_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', 
            'sender', 
            'text',
            'attachment', 
            'attachment_url', 
            'message_type',
            'timestamp', 
            'is_read'
        ]
        read_only_fields = ['id', 'timestamp', 'sender', 'attachment_url', 'conversation']
        extra_kwargs = {
            'attachment': {'write_only': True, 'required': False}, 
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
        message_type = data.get('message_type', Message.MessageType.TEXT)
        text = data.get('text')
        attachment = data.get('attachment')

        if message_type == Message.MessageType.TEXT and not text:
            raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE) and not attachment:
            raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not attachment:
             raise serializers.ValidationError("Message must have either text or an attachment.")

        if attachment and not text and message_type != Message.MessageType.TEXT:
            data['text'] = None 
        
        if attachment:
            if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' # Default
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try:
                        main_type = attachment.content_type.split('/')[0]
                    except IndexError:
                        # content_type might not have '/', use the whole string or default
                        pass # main_type remains default or could be set to attachment.content_type

                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    latest_message = MessageSerializer(read_only=True, source='messages.last')
    unread_count = serializers.SerializerMethodField()
    initiator = UserSerializer(read_only=True)
    other_participant_username = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 'initiator',
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 'initiator']

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0
        
    def get_other_participant_username(self, obj):
        user = self.context.get('request').user
        if user and obj.participants.count() == 2:
            other_participant = obj.get_other_participant(user)
            return other_participant.username if other_participant else None
        return None

class CreateMessageSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(write_only=True, required=True)
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attachment = serializers.FileField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)

    def validate_recipient_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Recipient user does not exist.")
        request = self.context.get('request')
        if request and request.user.id == value:
            raise serializers.ValidationError("You cannot send a message to yourself.")
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
                main_type = 'application/octet-stream' # Default
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try:
                        main_type = attachment.content_type.split('/')[0]
                    except IndexError:
                        pass # main_type remains default or could be set to attachment.content_type
                
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file."})
        return data