from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MaxLengthValidator 
from .models import Conversation, Message
from users.serializers import UserSerializer as FullUserSerializer # Renamed for clarity
from music.models import Artist 
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
            'timestamp', 
            'is_read'
        ]
        read_only_fields = [
            'id', 'timestamp', 'sender_user', 'attachment_url', 
            'original_attachment_filename', 'conversation', 
            'sender_identity_type', 'sending_artist_details'
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

    def get_attachment_url(self, obj: Message):
        if obj.attachment and obj.attachment.name:
            request = self.context.get('request')
            if request:
                from django.urls import reverse
                try:
                    # Ensure your URL name matches what's in chat/urls.py
                    download_url = reverse('chat-attachment-download', kwargs={'message_pk': obj.pk})
                    return request.build_absolute_uri(download_url)
                except Exception as e:
                    logger.error(f"Could not reverse chat-attachment-download URL for message {obj.pk}: {e}")
                    # Fallback if URL reversing fails, but direct .url might not be secure for private files
                    if hasattr(obj.attachment, 'url'):
                         return request.build_absolute_uri(obj.attachment.url)
            # Fallback if no request context (e.g. in shell or tests without request factory)
            elif hasattr(obj.attachment, 'url'):
                return obj.attachment.url # This might expose media root if not careful with S3/private files
        return None
    
    def create(self, validated_data):
        # sender_user, conversation, sender_identity_type, sending_artist
        # are passed to .save() in the view, not part of `validated_data` here.
        
        # original_attachment_filename is handled by the model's save method
        # if an attachment is present.
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Updates are less common for messages, but if implemented:
        # original_attachment_filename is handled by model's save method.
        return super().update(instance, validated_data)

    def validate(self, data):
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
        
        if new_attachment_provided and message_type != Message.MessageType.TEXT: # For AUDIO/VOICE
            if text is not None and not text.strip(): # If text is provided but empty for audio/voice, make it null
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
    participants = BasicUserSerializer(many=True, read_only=True)
    latest_message = MessageSerializer(read_only=True, source='messages.last') # Get the last message
    
    initiator_user = BasicUserSerializer(read_only=True)
    initiator_identity_type = serializers.ChoiceField(choices=Conversation.IdentityType.choices, read_only=True)
    initiator_artist_profile_details = ArtistChatInfoSerializer(source='initiator_artist_profile', read_only=True, allow_null=True)

    related_artist_recipient_details = ArtistChatInfoSerializer(source='related_artist_recipient', read_only=True, allow_null=True)
    
    unread_count = serializers.SerializerMethodField()
    # This field is crucial for the frontend to display the "chat with" name
    other_participant_display_name = serializers.SerializerMethodField() 

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'is_accepted', 
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details',
            'related_artist_recipient_details', 
            'created_at', 'updated_at', 'latest_message', 'unread_count',
            'other_participant_display_name' # Use this instead of other_participant_username
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'latest_message', 'unread_count', 
            'participants', # Participants are set by the backend on creation
            'initiator_user', 'initiator_identity_type', 'initiator_artist_profile_details',
            'related_artist_recipient_details', 'other_participant_display_name'
        ] 

    def get_unread_count(self, obj: Conversation):
        user = self.context['request'].user
        if user.is_authenticated:
            # Count unread messages not sent by the current user
            return obj.messages.filter(is_read=False).exclude(sender_user=user).count()
        return 0
        
    def get_other_participant_display_name(self, obj: Conversation):
        requesting_user = self.context.get('request').user
        if not requesting_user.is_authenticated: return None

        # Case 1: Conversation is directed TO an artist profile
        if obj.related_artist_recipient:
            # If I (requesting_user) am the owner of this target artist profile
            # (i.e., this conversation is a DM sent TO MY artist profile)
            # Then the "other party" is the initiator of the conversation.
            # We need to display the initiator's identity.
            if hasattr(requesting_user, 'artist_profile') and \
               requesting_user.artist_profile and \
               requesting_user.artist_profile == obj.related_artist_recipient:
                
                if obj.initiator_identity_type == Conversation.IdentityType.ARTIST and obj.initiator_artist_profile:
                    return f"{obj.initiator_artist_profile.name} [Artist]"
                elif obj.initiator_user: # Initiator was a User
                    return f"{obj.initiator_user.username} [User]"
                else: # Should ideally not happen if data is consistent
                    return "Unknown Initiator"
            else:
                # I am NOT the owner of the target artist profile.
                # This means either I DMed them, or it's an Artist-to-Artist DM where I am the initiator.
                # In either case, the "other party" context for display is the target artist.
                return f"{obj.related_artist_recipient.name} [Artist]"
        else:
            # Case 2: Standard User-to-User DM context (related_artist_recipient is null)
            # Find the other User model among participants.
            other_user_model = obj.participants.exclude(id=requesting_user.id).first()
            if not other_user_model: return "Conversation" # Fallback, should not happen in a 2-party convo

            # If this other user model *is* the initiator of the conversation,
            # AND they initiated it as an Artist.
            if obj.initiator_user == other_user_model and \
               obj.initiator_identity_type == Conversation.IdentityType.ARTIST and \
               obj.initiator_artist_profile:
                return f"{obj.initiator_artist_profile.name} [Artist]"
            else:
                # Conditions:
                # 1. Standard User-to-User DM (other user is initiator or recipient, but as User).
                # 2. An Artist initiated to me (requesting_user, as User), so other_user_model is that Artist's owner,
                #    but initiator_identity_type is USER for that initiator_user.
                # 3. I (as User) initiated to another User.
                # In all these sub-cases, the other_user_model is displayed as a User.
                return f"{other_user_model.username} [User]"
        
        return "Conversation" # Ultimate fallback


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
    
    initiator_identity_type = serializers.ChoiceField(
        choices=Conversation.IdentityType.choices, 
        default=Conversation.IdentityType.USER,
        required=False 
    )
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
                artist = Artist.objects.select_related('user').get(id=value)
                request = self.context.get('request')
                # Prevent sending from User account to own Artist Profile
                if request and request.user == artist.user:
                     # Get initiator_identity_type from initial data if present, else context or default
                    initiator_type_from_initial = self.initial_data.get('initiator_identity_type', Conversation.IdentityType.USER)
                    if initiator_type_from_initial == Conversation.IdentityType.USER:
                        raise serializers.ValidationError("You cannot send a message from your user account to your own artist profile.")
                # Prevent sending from Artist Profile to itself (Artist X to Artist X)
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
                # Ensure the artist profile belongs to the requesting user
                artist_profile = Artist.objects.get(pk=initiator_artist_profile_id, user=request_user)
                data['initiator_artist_profile_instance'] = artist_profile 
            except Artist.DoesNotExist:
                raise serializers.ValidationError({"initiator_artist_profile_id": "Invalid artist ID for initiator or it does not belong to you."})
        elif initiator_identity_type == Conversation.IdentityType.USER:
            if initiator_artist_profile_id:
                raise serializers.ValidationError({"initiator_artist_profile_id": "initiator_artist_profile_id should not be provided if initiating as USER."})
            data['initiator_artist_profile_instance'] = None # Explicitly set to None

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
                    raise serializers.ValidationError({"attachment": "Uploaded file does not appear to be an audio file for this message type."})
        return data