from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MaxLengthValidator 
from .models import Conversation, Message
from users.serializers import UserSerializer 
from music.models import Artist 
# from music.serializers import ArtistSerializer as FullArtistSerializer # Not strictly needed here now
import logging 

User = get_user_model()
MAX_MESSAGE_LENGTH = 1000 
logger = logging.getLogger(__name__) 

class ArtistChatSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture'] 

class SendingArtistSerializer(serializers.ModelSerializer): # For message.sending_artist
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture']

class InitiatorArtistSerializer(serializers.ModelSerializer): # For conversation.initiator_artist_profile
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture']


class MessageSerializer(serializers.ModelSerializer):
    sender_user = UserSerializer(read_only=True) 
    attachment_url = serializers.SerializerMethodField(read_only=True)
    original_attachment_filename = serializers.CharField(read_only=True, allow_null=True)
    
    # These are now read_only as they are derived from conversation context or set on creation
    sender_identity_type = serializers.ChoiceField(choices=Message.SenderIdentity.choices, read_only=True)
    sending_artist_details = SendingArtistSerializer(source='sending_artist', read_only=True, allow_null=True)

    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', 
            'sender_user',  
            'sender_identity_type', 
            'sending_artist_details',
            'text',
            'attachment', # Still writeable for upload
            'attachment_url', 
            'original_attachment_filename', 
            'message_type',
            'timestamp', 
            'is_read'
        ]
        # sender_identity_type and sending_artist_id are no longer direct inputs here
        # They will be set by the view based on conversation context.
        read_only_fields = [
            'id', 'timestamp', 'sender_user', 'attachment_url', 
            'original_attachment_filename', 'conversation', 
            'sender_identity_type', 'sending_artist_details' # Make these read-only
        ] 
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
        if obj.attachment and obj.attachment.name:
            request = self.context.get('request')
            if request:
                from django.urls import reverse
                try:
                    download_url = reverse('chat-attachment-download', kwargs={'message_pk': obj.pk})
                    return request.build_absolute_uri(download_url)
                except Exception as e:
                    logger.error(f"Could not reverse chat-attachment-download URL: {e}")
                    if hasattr(obj.attachment, 'url'):
                         return request.build_absolute_uri(obj.attachment.url)
            elif hasattr(obj.attachment, 'url'):
                return obj.attachment.url
        return None
    
    # create and update are simplified as identity is set by the view now before calling .save() on serializer instance
    def create(self, validated_data):
        attachment_file = validated_data.get('attachment')
        if attachment_file:
            validated_data['original_attachment_filename'] = attachment_file.name
        # sender_user, conversation, sender_identity_type, sending_artist are passed to .save() in the view
        return super().create(validated_data)

    def update(self, instance, validated_data): # Updates are less common for messages
        attachment_file = validated_data.get('attachment')
        if attachment_file:
            validated_data['original_attachment_filename'] = attachment_file.name
        elif 'attachment' in validated_data and attachment_file is None:
            validated_data['original_attachment_filename'] = None
        return super().update(instance, validated_data)

    def validate(self, data): # Basic content validation remains
        message_type = data.get('message_type', self.instance.message_type if self.instance else Message.MessageType.TEXT)
        text = data.get('text', None) 
        if text is None and self.instance and 'text' not in data: 
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
            if not new_attachment_provided and not current_attachment_exists: 
                raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
        
        if not text and not new_attachment_provided and not current_attachment_exists:
             raise serializers.ValidationError("Message must have either text or an attachment.")
        
        if new_attachment_provided and message_type != Message.MessageType.TEXT:
            if text is not None and not text.strip(): 
                 data['text'] = None 
        
        if new_attachment_provided: 
            if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' 
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try:
                        main_type = attachment.content_type.split('/')[0]
                    except IndexError: pass 
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    latest_message = MessageSerializer(read_only=True, source='messages.last') 
    
    # Initiator details
    initiator_user = UserSerializer(read_only=True)
    initiator_identity_type = serializers.ChoiceField(choices=Conversation.IdentityType.choices, read_only=True)
    initiator_artist_profile_details = InitiatorArtistSerializer(source='initiator_artist_profile', read_only=True, allow_null=True)

    # Recipient artist context
    related_artist_recipient_details = ArtistChatSerializer(source='related_artist_recipient', read_only=True, allow_null=True)
    
    unread_count = serializers.SerializerMethodField()
    other_participant_username = serializers.SerializerMethodField() # May need adjustment based on new identities

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details', # New initiator fields
            'related_artist_recipient_details', # Updated recipient artist field
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_username'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details',
            'related_artist_recipient_details'
        ] 

    def get_unread_count(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender_user=user).count()
        return 0
        
    def get_other_participant_username(self, obj): # This needs careful re-evaluation
        requesting_user = self.context.get('request').user
        if not requesting_user.is_authenticated: return None

        other_user_model = obj.get_other_participant(requesting_user)
        if not other_user_model: return None # Should not happen in a 2-party convo

        # If this conversation was initiated by an Artist towards me (as User)
        if obj.initiator_user == other_user_model and \
           obj.initiator_identity_type == Conversation.IdentityType.ARTIST and \
           obj.initiator_artist_profile:
            return f"{obj.initiator_artist_profile.name} [Artist]"
        
        # If this conversation is directed towards an Artist (related_artist_recipient)
        # and I am not that artist's owner (i.e., I am a User DMing an Artist)
        if obj.related_artist_recipient and \
           (not hasattr(requesting_user, 'artist_profile') or requesting_user.artist_profile != obj.related_artist_recipient):
            return f"{obj.related_artist_recipient.name} [Artist]"

        # Default to the other user's username (standard User-to-User or User receiving from Artist)
        return f"{other_user_model.username} [User]"


class CreateMessageSerializer(serializers.Serializer): # For INITIATING a new conversation
    recipient_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    recipient_artist_id = serializers.IntegerField(write_only=True, required=False, allow_null=True) # This is related_artist_recipient
    
    text = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True, 
        validators=[MaxLengthValidator(MAX_MESSAGE_LENGTH)] 
    )
    attachment = serializers.FileField(required=False, allow_null=True)
    message_type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)
    
    # Initiator's identity for THIS new conversation
    initiator_identity_type = serializers.ChoiceField(
        choices=Conversation.IdentityType.choices, 
        default=Conversation.IdentityType.USER,
        required=False 
    )
    # If initiator_identity_type is ARTIST, this ID must be provided
    initiator_artist_profile_id = serializers.IntegerField(required=False, allow_null=True)


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
                    raise serializers.ValidationError("You cannot send a message to your own artist profile as a recipient.")
            except Artist.DoesNotExist:
                 raise serializers.ValidationError("Recipient artist does not exist.")
        return value

    def validate(self, data):
        recipient_user_id = data.get('recipient_user_id')
        recipient_artist_id = data.get('recipient_artist_id')

        if not recipient_user_id and not recipient_artist_id:
            raise serializers.ValidationError({
                "recipient_user_id": "Either recipient_user_id or recipient_artist_id must be provided.",
                "recipient_artist_id": "Either recipient_user_id or recipient_artist_id must be provided."})
        if recipient_user_id and recipient_artist_id:
            raise serializers.ValidationError({
                 "recipient_user_id": "Provide either recipient_user_id or recipient_artist_id, not both.",
                 "recipient_artist_id": "Provide either recipient_user_id or recipient_artist_id, not both."})

        # Validate initiator identity
        request_user = self.context.get('request').user
        initiator_identity_type = data.get('initiator_identity_type', Conversation.IdentityType.USER)
        initiator_artist_profile_id = data.get('initiator_artist_profile_id') 

        if initiator_identity_type == Conversation.IdentityType.ARTIST:
            if not initiator_artist_profile_id:
                raise serializers.ValidationError({"initiator_artist_profile_id": "initiator_artist_profile_id must be provided if initiating as ARTIST."})
            try:
                artist_profile = Artist.objects.get(pk=initiator_artist_profile_id, user=request_user)
                data['initiator_artist_profile_instance'] = artist_profile # Store instance for the view
            except Artist.DoesNotExist:
                raise serializers.ValidationError({"initiator_artist_profile_id": "Invalid artist ID for initiator or it does not belong to you."})
        elif initiator_identity_type == Conversation.IdentityType.USER:
            if initiator_artist_profile_id:
                raise serializers.ValidationError({"initiator_artist_profile_id": "initiator_artist_profile_id should not be provided if initiating as USER."})
            data['initiator_artist_profile_instance'] = None 

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
                    try: main_type = attachment.content_type.split('/')[0]
                    except IndexError: pass 
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file."})
        return data

# For sending REPLIES, the payload is simpler, MessageSerializer is used directly by the view.
# The view will determine the sender_identity_type and sending_artist for the new message based on Conversation context.