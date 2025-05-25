from rest_framework import serializers
from .models import Genre, Artist, Release, Track, Comment, Highlight

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']

class ArtistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_id = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Artist
        fields = ['id', 'user', 'user_id', 'name', 'bio', 'artist_picture', 'location', 'website_url']


class TrackSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True)
    
    genres_data = GenreSerializer(source='genres', many=True, read_only=True) 
    genre_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        write_only=True,
        required=False 
    )

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'track_number', 'audio_file',
            'duration_in_seconds',
            'release', 
            'release_title', 'artist_name',
            'genres_data', 
            'genre_names', 
            'created_at'
        ]
        read_only_fields = ['release_title', 'artist_name', 'duration_in_seconds', 'genres_data']
        # track_number is intentionally not read_only here to allow it to be set on create/update

    def create(self, validated_data):
        genre_names = validated_data.pop('genre_names', [])
        # track_number should be in validated_data if sent from frontend
        track = Track.objects.create(**validated_data) # This will call Track.save()
        
        genres_to_set = []
        for name in genre_names:
            genre, _ = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
            genres_to_set.append(genre)
        if genres_to_set:
            track.genres.set(genres_to_set)
        return track

    def update(self, instance, validated_data):
        genre_names = validated_data.pop('genre_names', None)
        
        # Let the parent ModelSerializer.update handle field assignments from validated_data
        # This includes 'title', 'track_number', and 'audio_file' if they are provided.
        # The instance.save() call within super().update() will trigger our custom Track.save()
        instance = super().update(instance, validated_data)

        if genre_names is not None: 
            genres_to_set = []
            for name in genre_names:
                genre, _ = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
                genres_to_set.append(genre)
            instance.genres.set(genres_to_set)
        
        return instance


class ReleaseSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), source='artist', write_only=True, required=False 
    )
    
    genres_data = GenreSerializer(source='genres', many=True, read_only=True)
    genre_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        write_only=True,
        required=False
    )
    
    tracks = TrackSerializer(many=True, read_only=True) # Tracks are managed separately
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 'release_type', 'release_type_display', 'release_date',
            'cover_art', 
            'genres_data', 
            'genre_names', 
            'is_published', 'is_visible',
            'tracks', 'created_at', 'updated_at'
         ]
        read_only_fields = ['is_visible', 'release_type_display', 'genres_data', 'artist'] 

    def create(self, validated_data):
        genre_names = validated_data.pop('genre_names', [])
        release = Release.objects.create(**validated_data) # This will call Release.save()
        
        genres_to_set = []
        for name in genre_names:
            genre, created = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
            genres_to_set.append(genre)
        if genres_to_set: 
            release.genres.set(genres_to_set)
        return release

    def update(self, instance, validated_data):
        genre_names = validated_data.pop('genre_names', None) 
        
        # Handle cover_art specifically: if it's an empty string, clear it.
        # If it's a file, update it. If not present, leave it.
        cover_art_data = validated_data.pop('cover_art', Ellipsis) # Ellipsis is a unique sentinel
        if cover_art_data is not Ellipsis: # cover_art was in validated_data
            if cover_art_data == '' or cover_art_data is None:
                instance.cover_art = None
            else:
                instance.cover_art = cover_art_data
        
        # Let super().update handle other field assignments
        instance = super().update(instance, validated_data) # This calls instance.save()

        if genre_names is not None: 
            genres_to_set = []
            for name in genre_names:
                genre, created = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
                genres_to_set.append(genre)
            instance.genres.set(genres_to_set)
        
        return instance


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField() 

    class Meta:
        model = Comment
        fields = ['id', 'track', 'user', 'text', 'timestamp_seconds', 'created_at', 'updated_at']
        read_only_fields = ['user']

class HighlightSerializer(serializers.ModelSerializer):
    release = ReleaseSerializer(read_only=True) 
    highlighted_by = serializers.StringRelatedField()

    class Meta:
        model = Highlight
        fields = ['id', 'release', 'highlighted_by', 'highlighted_at', 'is_active', 'order']