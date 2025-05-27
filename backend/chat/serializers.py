from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from users.serializers import UserSerializer # Assuming a simple UserSerializer exists
from music.models import Artist # Import Artist for the new serializer

User = get_user_model()

# New simple serializer for artist context in conversations
class ArtistChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture'] # Basic info needed for chat context

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
            # If message_type is AUDIO or VOICE and only attachment is provided, text can be null
            data['text'] = None 
        
        if attachment:
            # This validation relies on the file object having `content_type`
            # For raw file uploads, this might be part of the request parsing (e.g. `request.FILES['attachment'].content_type`)
            # DRF handles this and provides it on the `UploadedFile` object.
            if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' # Default if content_type is missing or malformed
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
    related_artist = ArtistChatSerializer(read_only=True, allow_null=True) # Add related_artist
    other_participant_username = serializers.SerializerMethodField()


    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 'initiator', 'related_artist', # Added related_artist
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 'initiator', 'related_artist'] # Added related_artist

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0
        
    def get_other_participant_username(self, obj):
        # This method primarily makes sense for 1-on-1 chats
        user = self.context.get('request').user
        if user and obj.participants.count() == 2: # Assuming DM context
            other_participant = obj.get_other_participant(user)
            # If there's a related_artist and the other participant is the owner of that artist,
            # we might want to display the artist name. For now, keep it simple.
            # Frontend can use related_artist.name if initiator != request.user and related_artist is present.
            return other_participant.username if other_participant else None
        return None


class CreateMessageSerializer(serializers.Serializer):
    recipient_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    recipient_artist_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attachment = serializers.FileField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)

    def validate_recipient_user_id(self, value):
        if value is not None: # Only validate if provided
            if not User.objects.filter(id=value).exists():
                raise serializers.ValidationError("Recipient user does not exist.")
            request = self.context.get('request')
            if request and request.user.id == value:
                raise serializers.ValidationError("You cannot send a message to yourself as a user.")
        return value

    def validate_recipient_artist_id(self, value):
        if value is not None: # Only validate if provided
            try:
                artist = Artist.objects.get(id=value)
                request = self.context.get('request')
                # Check if user is trying to send message to their own artist profile
                if request and hasattr(request.user, 'artist_profile') and request.user.artist_profile.id == artist.id:
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

        if message_type == Message.MessageType.TEXT and not text:
            raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT."})
        
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