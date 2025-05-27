from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MaxLengthValidator 
from .models import Conversation, Message
from users.serializers import UserSerializer 
from music.models import Artist 

User = get_user_model()
MAX_MESSAGE_LENGTH = 1000 

class ArtistChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture'] 

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachment_url = serializers.SerializerMethodField(read_only=True)
    # Expose the original filename
    original_attachment_filename = serializers.CharField(read_only=True, allow_null=True) 

    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', 
            'sender', 
            'text',
            'attachment', 
            'attachment_url', 
            'original_attachment_filename', # Added
            'message_type',
            'timestamp', 
            'is_read'
        ]
        read_only_fields = ['id', 'timestamp', 'sender', 'attachment_url', 'original_attachment_filename', 'conversation'] 
        extra_kwargs = {
            'attachment': {'write_only': True, 'required': False}, 
            'text': {
                'required': False, 
                'allow_blank': True, 
                'allow_null': True,
                'validators': [MaxLengthValidator(MAX_MESSAGE_LENGTH)] 
            }
        }

    def get_attachment_url(self, obj):
        # This will now point to our dedicated download view
        if obj.attachment and obj.attachment.name:
            request = self.context.get('request')
            if request:
                from django.urls import reverse
                try:
                    # Ensure 'chat-attachment-download' is the name of your new URL
                    download_url = reverse('chat-attachment-download', kwargs={'message_pk': obj.pk})
                    return request.build_absolute_uri(download_url)
                except Exception as e:
                    # Fallback to direct media URL if reverse fails (e.g., URL not configured yet)
                    logger.error(f"Could not reverse chat-attachment-download URL: {e}")
                    if hasattr(obj.attachment, 'url'):
                         return request.build_absolute_uri(obj.attachment.url)
            elif hasattr(obj.attachment, 'url'): # No request context, return relative URL
                return obj.attachment.url
        return None
    
    def create(self, validated_data):
        attachment_file = validated_data.get('attachment')
        if attachment_file:
            # Store original filename before it gets renamed by upload_to
            validated_data['original_attachment_filename'] = attachment_file.name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        attachment_file = validated_data.get('attachment')
        if attachment_file:
            # If a new file is being uploaded for an existing message
            validated_data['original_attachment_filename'] = attachment_file.name
        elif 'attachment' in validated_data and attachment_file is None:
            # If attachment is explicitly set to None (cleared)
            validated_data['original_attachment_filename'] = None
        # If 'attachment' is not in validated_data, it means it's not being changed,
        # so original_attachment_filename should also not change unless explicitly cleared.
        return super().update(instance, validated_data)


    def validate(self, data):
        message_type = data.get('message_type', self.instance.message_type if self.instance else Message.MessageType.TEXT)
        # Get text considering existing instance or new data
        text = data.get('text', None) # Default to None if not in data
        if text is None and self.instance and 'text' not in data: # If updating and text not provided, use existing
             text = self.instance.text

        attachment = data.get('attachment') 

        if text and len(text) > MAX_MESSAGE_LENGTH:
             raise serializers.ValidationError({"text": f"Text cannot exceed {MAX_MESSAGE_LENGTH} characters."})

        current_attachment_exists = self.instance and self.instance.attachment and self.instance.attachment.name
        new_attachment_provided = attachment is not None


        if message_type == Message.MessageType.TEXT and not text:
            if not new_attachment_provided and not current_attachment_exists:
                 raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT and no attachment is present."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE):
            if not new_attachment_provided and not current_attachment_exists: # If no new file and no existing file
                raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not new_attachment_provided and not current_attachment_exists:
             raise serializers.ValidationError("Message must have either text or an attachment.")
        
        if new_attachment_provided and message_type != Message.MessageType.TEXT:
            if text is not None and not text.strip(): # If text is explicitly empty string for non-text type
                 data['text'] = None # Store as null instead of empty string
        
        if new_attachment_provided: # Only validate new attachments
            if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' 
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try:
                        main_type = attachment.content_type.split('/')[0]
                    except IndexError:
                        pass 
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    latest_message = MessageSerializer(read_only=True, source='messages.last')
    unread_count = serializers.SerializerMethodField()
    initiator = UserSerializer(read_only=True)
    related_artist = ArtistChatSerializer(read_only=True, allow_null=True) 
    other_participant_username = serializers.SerializerMethodField()


    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 'initiator', 'related_artist', 
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 'initiator', 'related_artist'] 

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
    recipient_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    recipient_artist_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    text = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True, 
        validators=[MaxLengthValidator(MAX_MESSAGE_LENGTH)] 
    )
    attachment = serializers.FileField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)

    def validate_recipient_user_id(self, value):
        if value is not None: 
            if not User.objects.filter(id=value).exists():
                raise serializers.ValidationError("Recipient user does not exist.")
            request = self.context.get('request')
            if request and request.user.id == value:
                raise serializers.ValidationError("You cannot send a message to yourself as a user.")
        return value

    def validate_recipient_artist_id(self, value):
        if value is not None: 
            try:
                artist = Artist.objects.get(id=value)
                request = self.context.get('request')
                if request and hasattr(request.user, 'artist_profile') and request.user.artist_profile and request.user.artist_profile.id == artist.id:
                    raise serializers.ValidationError("You cannot send a message to your own artist profile.")
            except Artist.DoesNotExist:
                 raise serializers.ValidationError("Recipient artist does not exist.")
        return value


    def validate(self, data):
        recipient_user_id = data.get('recipient_user_id')
        recipient_artist_id = data.get('recipient_artist_id')

        if not recipient_user_id and not recipient_artist_id:
            raise serializers.ValidationError({
                "recipient_user_id": "Either recipient_user_id or recipient_artist_id must be provided.",
                "recipient_artist_id": "Either recipient_user_id or recipient_artist_id must be provided."
            })
        if recipient_user_id and recipient_artist_id:
            raise serializers.ValidationError({
                 "recipient_user_id": "Provide either recipient_user_id or recipient_artist_id, not both.",
                 "recipient_artist_id": "Provide either recipient_user_id or recipient_artist_id, not both."
            })

        message_type = data.get('message_type', Message.MessageType.TEXT)
        text = data.get('text')
        attachment = data.get('attachment')

        if text and len(text) > MAX_MESSAGE_LENGTH: 
            raise serializers.ValidationError({"text": f"Text cannot exceed {MAX_MESSAGE_LENGTH} characters."})

        if message_type == Message.MessageType.TEXT and not text:
            if not attachment: 
                raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT and no attachment is provided."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE) and not attachment:
            raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not attachment: 
            raise serializers.ValidationError("Message must have either text or an attachment.")
        
        if attachment:
             if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' 
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try:
                        main_type = attachment.content_type.split('/')[0]
                    except IndexError:
                        pass 
                
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file."})
        return data