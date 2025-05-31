from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MaxLengthValidator 
from .models import Conversation, Message
from users.serializers import UserSerializer as FullUserSerializer # Renamed for clarity
from music.models import Artist, Track # Import Track
from music.serializers import TrackSerializer as MusicTrackSerializer # For shared track details
import logging 

User = get_user_model()
MAX_MESSAGE_LENGTH = 1000 
logger = logging.getLogger(__name__) 

class BasicUserSerializer(serializers.ModelSerializer): # For embedding in chat related objects
    class Meta:
        model = User
        fields = ['id', 'username'] # Add other fields like profile picture if needed later

class ArtistChatInfoSerializer(serializers.ModelSerializer): # For embedding artist info
    class Meta:
        model = Artist
        fields = ['id', 'name', 'artist_picture'] 


class MessageSerializer(serializers.ModelSerializer):
    sender_user = BasicUserSerializer(read_only=True) 
    attachment_url = serializers.SerializerMethodField(read_only=True)
    original_attachment_filename = serializers.CharField(read_only=True, allow_null=True)
    
    sender_identity_type = serializers.ChoiceField(choices=Message.SenderIdentity.choices, read_only=True)
    sending_artist_details = ArtistChatInfoSerializer(source='sending_artist', read_only=True, allow_null=True)
    
    shared_track_details = MusicTrackSerializer(source='shared_track', read_only=True, allow_null=True)

    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', 
            'sender_user',  
            'sender_identity_type', 
            'sending_artist_details',
            'text',
            'attachment', 
            'attachment_url', 
            'original_attachment_filename', 
            'message_type',
            'shared_track', # For writing shared_track_id
            'shared_track_details', # For reading shared_track details
            'timestamp', 
            'is_read'
        ]
        read_only_fields = [
            'id', 'timestamp', 'sender_user', 'attachment_url', 
            'original_attachment_filename', 'conversation', 
            'sender_identity_type', 'sending_artist_details',
            'shared_track_details'
        ] 
        extra_kwargs = {
            'attachment': {'write_only': True, 'required': False, 'allow_null': True}, 
            'shared_track': {'write_only': True, 'required': False, 'allow_null': True, 'queryset': Track.objects.all()},
            'text': {
                'required': False, 
                'allow_blank': True, 
                'allow_null': True,
                'validators': [MaxLengthValidator(MAX_MESSAGE_LENGTH)] 
            }
        }

    def get_attachment_url(self, obj: Message):
        if obj.attachment and obj.attachment.name:
            request = self.context.get('request')
            if request:
                from django.urls import reverse
                try:
                    download_url = reverse('chat-attachment-download', kwargs={'message_pk': obj.pk})
                    return request.build_absolute_uri(download_url)
                except Exception as e:
                    logger.error(f"Could not reverse chat-attachment-download URL for message {obj.pk}: {e}")
                    if hasattr(obj.attachment, 'url'):
                         return request.build_absolute_uri(obj.attachment.url)
            elif hasattr(obj.attachment, 'url'):
                return obj.attachment.url 
        return None
    
    def validate(self, data):
        message_type = data.get('message_type', self.instance.message_type if self.instance else Message.MessageType.TEXT)
        text = data.get('text', None) 
        if text is None and self.instance and 'text' not in data: 
             text = self.instance.text
        attachment = data.get('attachment') 
        shared_track = data.get('shared_track')

        if text and len(text) > MAX_MESSAGE_LENGTH:
             raise serializers.ValidationError({"text": f"Text cannot exceed {MAX_MESSAGE_LENGTH} characters."})

        current_attachment_exists = self.instance and self.instance.attachment and self.instance.attachment.name
        new_attachment_provided = attachment is not None

        if message_type == Message.MessageType.TEXT and not text:
            if not new_attachment_provided and not current_attachment_exists and not shared_track: # Modified condition
                 raise serializers.ValidationError({"text": "Message content (text, attachment, or track share) is required."})
        
        if (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE):
            if not new_attachment_provided and not current_attachment_exists: 
                raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
            if shared_track:
                raise serializers.ValidationError({"shared_track": f"{message_type.label} messages cannot also share a track."})

        if message_type == Message.MessageType.TRACK_SHARE:
            if not shared_track:
                raise serializers.ValidationError({"shared_track": "A track must be selected for 'Track Share' messages."})
            if new_attachment_provided or current_attachment_exists:
                raise serializers.ValidationError({"attachment": "Track share messages cannot have a direct file attachment."})
            if text: # Optionally allow text with track shares
                pass # data['text'] = text 
        
        if not text and not new_attachment_provided and not current_attachment_exists and not shared_track:
             raise serializers.ValidationError("Message must have either text, an attachment, or a shared track.")
        
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
    participants = BasicUserSerializer(many=True, read_only=True)
    latest_message = MessageSerializer(read_only=True, source='messages.last') 
    
    initiator_user = BasicUserSerializer(read_only=True)
    initiator_identity_type = serializers.ChoiceField(choices=Conversation.IdentityType.choices, read_only=True)
    initiator_artist_profile_details = ArtistChatInfoSerializer(source='initiator_artist_profile', read_only=True, allow_null=True)

    related_artist_recipient_details = ArtistChatInfoSerializer(source='related_artist_recipient', read_only=True, allow_null=True)
    
    unread_count = serializers.SerializerMethodField()
    other_participant_display_name = serializers.SerializerMethodField() 

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details',
            'related_artist_recipient_details', 
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_display_name'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 
            'participants', 
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details',
            'related_artist_recipient_details', 'other_participant_display_name'
        ] 

    def get_unread_count(self, obj: Conversation):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender_user=user).count()
        return 0
        
    def get_other_participant_display_name(self, obj: Conversation):
        requesting_user = self.context.get('request').user
        if not requesting_user.is_authenticated: return None

        if obj.related_artist_recipient:
            if hasattr(requesting_user, 'artist_profile') and \
               requesting_user.artist_profile and \
               requesting_user.artist_profile == obj.related_artist_recipient:
                if obj.initiator_identity_type == Conversation.IdentityType.ARTIST and obj.initiator_artist_profile:
                    return f"{obj.initiator_artist_profile.name} [Artist]"
                elif obj.initiator_user: 
                    return f"{obj.initiator_user.username} [User]"
                else: 
                    return "Unknown Initiator"
            else:
                return f"{obj.related_artist_recipient.name} [Artist]"
        else:
            other_user_model = obj.participants.exclude(id=requesting_user.id).first()
            if not other_user_model: return "Conversation" 
            if obj.initiator_user == other_user_model and \
               obj.initiator_identity_type == Conversation.IdentityType.ARTIST and \
               obj.initiator_artist_profile:
                return f"{obj.initiator_artist_profile.name} [Artist]"
            else:
                return f"{other_user_model.username} [User]"
        return "Conversation" 


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
    shared_track_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    initiator_identity_type = serializers.ChoiceField(
        choices=Conversation.IdentityType.choices, 
        default=Conversation.IdentityType.USER,
        required=False 
    )
    initiator_artist_profile_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_shared_track_id(self, value):
        if value is not None:
            # Artist should be able to select their own draft tracks to share.
            # This requires context of the requesting user to check ownership.
            # For now, basic existence check. Advanced logic in view.
            if not Track.objects.filter(id=value).exists():
                 raise serializers.ValidationError("Shared track does not exist.")
        return value

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
                artist = Artist.objects.select_related('user').get(id=value)
                request = self.context.get('request')
                if request and request.user == artist.user:
                    initiator_type_from_initial = self.initial_data.get('initiator_identity_type', Conversation.IdentityType.USER)
                    if initiator_type_from_initial == Conversation.IdentityType.USER:
                        raise serializers.ValidationError("You cannot send a message from your user account to your own artist profile.")
                initiator_artist_id_from_initial = self.initial_data.get('initiator_artist_profile_id')
                if initiator_artist_id_from_initial and int(initiator_artist_id_from_initial) == artist.id:
                    raise serializers.ValidationError("An artist profile cannot send a message to itself.")

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

        request_user = self.context.get('request').user
        initiator_identity_type = data.get('initiator_identity_type', Conversation.IdentityType.USER)
        initiator_artist_profile_id = data.get('initiator_artist_profile_id') 

        if initiator_identity_type == Conversation.IdentityType.ARTIST:
            if not initiator_artist_profile_id:
                raise serializers.ValidationError({"initiator_artist_profile_id": "initiator_artist_profile_id must be provided if initiating as ARTIST."})
            try:
                artist_profile = Artist.objects.get(pk=initiator_artist_profile_id, user=request_user)
                data['initiator_artist_profile_instance'] = artist_profile 
            except Artist.DoesNotExist:
                raise serializers.ValidationError({"initiator_artist_profile_id": "Invalid artist ID for initiator or it does not belong to you."})
        elif initiator_identity_type == Conversation.IdentityType.USER:
            if initiator_artist_profile_id:
                raise serializers.ValidationError({"initiator_artist_profile_id": "initiator_artist_profile_id should not be provided if initiating as USER."})
            data['initiator_artist_profile_instance'] = None 

        message_type = data.get('message_type', Message.MessageType.TEXT)
        text = data.get('text')
        attachment = data.get('attachment')
        shared_track_id = data.get('shared_track_id')

        if text and len(text) > MAX_MESSAGE_LENGTH: 
            raise serializers.ValidationError({"text": f"Text cannot exceed {MAX_MESSAGE_LENGTH} characters."})
        
        if message_type == Message.MessageType.TRACK_SHARE:
            if not shared_track_id:
                raise serializers.ValidationError({"shared_track_id": "shared_track_id is required for track share messages."})
            if attachment:
                raise serializers.ValidationError({"attachment": "Track share messages cannot have a file attachment."})
            data['attachment'] = None # Ensure attachment is None for track shares
        elif (message_type == Message.MessageType.AUDIO or message_type == Message.MessageType.VOICE):
            if not attachment:
                raise serializers.ValidationError({"attachment": f"{message_type.label} message must have an attachment."})
            if shared_track_id:
                raise serializers.ValidationError({"shared_track_id": f"{message_type.label} messages cannot also share a track."})
        elif message_type == Message.MessageType.TEXT:
            if not text and not attachment: # Text message can have an attachment as a generic file share
                 raise serializers.ValidationError({"text": "Text message cannot be empty if type is TEXT and no attachment/track is provided."})
            if shared_track_id: # If it's text, it can't be a track share simultaneously (handled by TRACK_SHARE type)
                 raise serializers.ValidationError({"shared_track_id": "Text messages cannot also be a track share of type TEXT."})


        if not text and not attachment and not shared_track_id: 
            raise serializers.ValidationError("Message must have text, an attachment, or a shared track.")
        
        if attachment:
             if message_type in [Message.MessageType.AUDIO, Message.MessageType.VOICE]:
                main_type = 'application/octet-stream' 
                if attachment.content_type and isinstance(attachment.content_type, str):
                    try: main_type = attachment.content_type.split('/')[0]
                    except IndexError: pass 
                if main_type != 'audio':
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data