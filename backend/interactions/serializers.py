from rest_framework import serializers
from .models import Follow
from users.serializers import BasicUserSerializer
from music.serializers import ArtistSerializer as FullArtistSerializer # Renamed to avoid conflict if you use Artist locally
from music.models import Artist

class FollowSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)
    artist = FullArtistSerializer(read_only=True) # Use the renamed import for clarity
    # For write operations, we'll likely use artist_id
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), source='artist', write_only=True # Now Artist is defined
    )

    class Meta:
        model = Follow
        fields = ['id', 'user', 'artist', 'artist_id', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate_artist_id(self, value):
        # Prevent following oneself if user is also the artist owner (edge case)
        request_user = self.context['request'].user
        if value.user == request_user:
            raise serializers.ValidationError("You cannot follow your own artist profile.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        artist = validated_data['artist']
        
        follow, created = Follow.objects.get_or_create(user=user, artist=artist)
        if not created:
            # Optionally, you could raise an error if already following,
            # or just return the existing follow instance.
            # For now, get_or_create handles idempotency.
            pass
        return follow

class FollowerSerializer(serializers.ModelSerializer):
    """Serializer for displaying followers of an artist."""
    user = BasicUserSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'user', 'created_at']


class FollowingSerializer(serializers.ModelSerializer):
    """Serializer for displaying artists a user is following."""
    artist = FullArtistSerializer(read_only=True) # Use the renamed import

    class Meta:
        model = Follow
        fields = ['id', 'artist', 'created_at']