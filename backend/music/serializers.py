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

# A field to handle list of genre names for input, and get_or_create them
class GenreListField(serializers.Field):
    def to_representation(self, value):
        # 'value' will be the queryset of Genre objects from the instance
        return [genre.name for genre in value.all()]

    def to_internal_value(self, data):
        # 'data' is expected to be a list of genre names (strings)
        if not isinstance(data, list):
            raise serializers.ValidationError("Expected a list of genre names.")
        
        genre_objects = []
        for genre_name in data:
            if not isinstance(genre_name, str) or not genre_name.strip():
                # Skip empty or non-string genre names, or raise validation error
                # For now, let's skip empty ones silently or raise a more specific error if needed
                continue 
            genre, created = Genre.objects.get_or_create(name__iexact=genre_name.strip(), defaults={'name': genre_name.strip()})
            genre_objects.append(genre)
        return genre_objects


class TrackSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True)
    
    # For reading, show full Genre objects. For writing, we'll use a different approach.
    genres_data = GenreSerializer(source='genres', many=True, read_only=True) 
    # For writing, accept a list of genre names
    genre_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        write_only=True,
        required=False # Make it optional
    )

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'track_number', 'audio_file',
            'duration_in_seconds',
            'release', 
            'release_title', 'artist_name',
            'genres_data', # For reading
            'genre_names', # For writing
            'created_at'
        ]
        read_only_fields = ['release_title', 'artist_name', 'duration_in_seconds', 'genres_data']

    def create(self, validated_data):
        genre_names = validated_data.pop('genre_names', [])
        track = Track.objects.create(**validated_data)
        
        genres_to_set = []
        for name in genre_names:
            genre, _ = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
            genres_to_set.append(genre)
        if genres_to_set:
            track.genres.set(genres_to_set)
        return track

    def update(self, instance, validated_data):
        genre_names = validated_data.pop('genre_names', None) # Use None to detect if field was passed
        
        # Update other fields
        instance.title = validated_data.get('title', instance.title)
        # Add other updatable fields for track if any (e.g., track_number, audio_file if allowed)
        instance.save() # Save other potentially changed fields

        if genre_names is not None: # Only update genres if 'genre_names' was provided
            genres_to_set = []
            for name in genre_names:
                genre, _ = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
                genres_to_set.append(genre)
            instance.genres.set(genres_to_set)
        return instance


class ReleaseSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), source='artist', write_only=True
    )
    
    # For reading, show full Genre objects.
    genres_data = GenreSerializer(source='genres', many=True, read_only=True)
    # For writing, accept a list of genre names
    genre_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        write_only=True,
        required=False # Make it optional
    )
    
    tracks = TrackSerializer(many=True, read_only=True)
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 'release_type', 'release_type_display', 'release_date',
            'cover_art', 
            'genres_data', # For reading genres
            'genre_names', # For writing genres
            'is_published', 'is_visible',
            'tracks', 'created_at', 'updated_at'
         ]
        read_only_fields = ['is_visible', 'release_type_display', 'genres_data']

    def create(self, validated_data):
        genre_names = validated_data.pop('genre_names', [])
        # Tracks are read_only, not created/updated directly through ReleaseSerializer create
        release = Release.objects.create(**validated_data)
        
        genres_to_set = []
        for name in genre_names:
            # Use __iexact for case-insensitive matching, then create with the exact submitted name (or standardized one)
            genre, created = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
            genres_to_set.append(genre)
        if genres_to_set: # Only set if there are genres
            release.genres.set(genres_to_set)
        return release

    def update(self, instance, validated_data):
        genre_names = validated_data.pop('genre_names', None) # Use None to detect if field was passed
        
        # Tracks are read_only, so not handled here for update
        # Update other fields on the release instance
        instance.title = validated_data.get('title', instance.title)
        instance.release_type = validated_data.get('release_type', instance.release_type)
        instance.release_date = validated_data.get('release_date', instance.release_date)
        # Handle cover_art, is_published as well if they are part of validated_data
        if 'cover_art' in validated_data:
             instance.cover_art = validated_data.get('cover_art', instance.cover_art)
        instance.is_published = validated_data.get('is_published', instance.is_published)
        # artist_id is handled by source='artist' if it's in validated_data
        if 'artist' in validated_data: # artist_id comes as 'artist' due to source='artist'
            instance.artist = validated_data.get('artist', instance.artist)

        instance.save()

        if genre_names is not None: # Only update genres if 'genre_names' was provided in the request
            genres_to_set = []
            for name in genre_names:
                genre, created = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
                genres_to_set.append(genre)
            instance.genres.set(genres_to_set) # .set() handles clearing old and adding new
        
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