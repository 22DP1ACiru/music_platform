from rest_framework import serializers
from .models import Notification
from users.serializers import BasicUserSerializer # Assuming BasicUserSerializer for user info
from music.serializers import ArtistSerializer, ReleaseSerializer # For related object details
from chat.serializers import ConversationSerializer # For chat details

class NotificationSerializer(serializers.ModelSerializer):
    recipient = BasicUserSerializer(read_only=True)
    actor_user = BasicUserSerializer(read_only=True, allow_null=True)
    actor_artist = ArtistSerializer(read_only=True, allow_null=True) # Simplified artist info

    # Target object serializers (read-only, include essential info)
    target_release_summary = serializers.SerializerMethodField(read_only=True)
    target_artist_summary = serializers.SerializerMethodField(read_only=True)
    # Potentially add more for other targets like conversation

    class Meta:
        model = Notification
        fields = [
            'id', 
            'recipient', 
            'actor_user', 
            'actor_artist',
            'verb', 
            'description', 
            'notification_type', 
            'is_read', 
            'created_at',
            'target_release_summary',
            'target_artist_summary',
            'target_conversation', # Keep as ID for now, or create summary serializer
            'target_order',      # Keep as ID
            'is_artist_channel',
            # Raw FKs for debugging or simple linking on frontend if needed
            'target_release', 'target_artist_profile', 'target_user_profile' 
        ]
        read_only_fields = fields # All fields are typically read-only for notifications API

    def get_target_release_summary(self, obj: Notification):
        if obj.target_release:
            # Use a lightweight ReleaseSummarySerializer if available, or construct manually
            return {
                "id": obj.target_release.id,
                "title": obj.target_release.title,
                "cover_art": obj.target_release.cover_art.url if obj.target_release.cover_art else None
            }
        return None

    def get_target_artist_summary(self, obj: Notification):
        if obj.target_artist_profile:
            return {
                "id": obj.target_artist_profile.id,
                "name": obj.target_artist_profile.name,
                "artist_picture": obj.target_artist_profile.artist_picture.url if obj.target_artist_profile.artist_picture else None
            }
        return None