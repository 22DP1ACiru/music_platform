from rest_framework import serializers
from .models import Genre, Artist, Release, Track, Comment, Highlight

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']

class ArtistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Artist
        fields = ['id', 'user', 'name', 'bio', 'artist_picture', 'location', 'website_url']

class TrackSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'track_number', 'audio_file', 'duration_seconds',
            'release', 'release_title', 'artist_name', # 'release' gives the ID
            'genre', # Genre ID
            'created_at'
        ]
        read_only_fields = ['release_title', 'artist_name'] # These are derived

class ReleaseSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True) # Show nested artist info (read-only on list/retrieve)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), source='artist', write_only=True
    ) # Allow setting artist by ID on create/update
    genre = GenreSerializer(read_only=True) # Show nested genre info
    genre_id = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(), source='genre', write_only=True, allow_null=True
    ) # Allow setting genre by ID
    tracks = TrackSerializer(many=True, read_only=True) # Show nested tracks on retrieve

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 'release_type', 'release_date',
            'cover_art', 'genre', 'genre_id', 'is_published', 'is_visible',
            'tracks', 'created_at', 'updated_at'
         ]
        read_only_fields = ['is_visible'] # Calculated field

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField() # Show username

    class Meta:
        model = Comment
        fields = ['id', 'track', 'user', 'text', 'timestamp_seconds', 'created_at', 'updated_at']
        read_only_fields = ['user'] # User should be set automatically based on request

class HighlightSerializer(serializers.ModelSerializer):
    release = ReleaseSerializer(read_only=True) # Show nested release info
    highlighted_by = serializers.StringRelatedField()

    class Meta:
        model = Highlight
        fields = ['id', 'release', 'highlighted_by', 'highlighted_at', 'is_active', 'order']