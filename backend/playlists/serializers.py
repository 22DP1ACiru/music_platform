from rest_framework import serializers
from django.contrib.auth.models import User # User model is needed if you use PrimaryKeyRelatedField for owner_id
from .models import Playlist
from music.serializers import TrackSerializer

class PlaylistSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True) # For GET responses (displaying username)
    # owner_id field is removed as perform_create handles setting the owner.
    
    tracks = TrackSerializer(many=True, read_only=True)
    track_count = serializers.IntegerField(read_only=True) # Populated by annotation in viewset

    class Meta:
        model = Playlist
        fields = [
            'id',
            'title',
            'owner', # This field will be handled by read_only_fields for input
            'tracks',
            'track_count',
            'cover_art',
            'description',
            'is_public',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'owner', # Makes 'owner' field not required during POST/PUT input validation.
                     # The ViewSet's perform_create will set it.
            'created_at', 
            'updated_at', 
            'track_count',
            'tracks' # Tracks are typically managed via separate actions (add_track, remove_track)
        ]
        # No custom create() method needed here if perform_create handles the owner
        # and other fields are standard. If you were to allow setting owner by ID
        # without perform_create, then owner_id would be needed.