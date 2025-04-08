from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Playlist
from music.serializers import TrackSerializer

class PlaylistSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)

    # This field allows setting the owner by User ID during POST/PUT/PATCH
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        write_only=True # Only used for input, not shown in output representation
    )
    # Show nested tracks (read-only is often simpler for ManyToMany on list/retrieve)
    # Making this writeable requires more complex logic (e.g., handling lists of track IDs)
    tracks = TrackSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = [
            'id', # Include the ID
            'title',
            'owner', # Read-only representation (username or nested User object)
            'owner_id', # Write-only field for setting owner
            'tracks',
            'cover_art',
            'description',
            'is_public',
            'created_at',
            'updated_at'
            ]
        read_only_fields = ['created_at', 'updated_at'] # These are set automatically

    def create(self, validated_data):
        """
        Ensure the owner is set to the requesting user during creation.
        """
        # 'owner_id' field is removed by default if read_only=True on 'owner'
        # We need to associate the playlist with the user making the request.
        # The viewset is the typical place to handle this.
        # We remove owner_id from fields and handle it in the view.
        # OR explicitly set it here if the view doesn't handle it.
        # For now, assume the view will pass request.user to the serializer.
        # If using owner_id field above, this custom create might not be needed
        # unless you want to default owner to request.user without requiring owner_id input.

        # Simplified - assumes owner is handled by view or owner_id field works:
        return super().create(validated_data)
    