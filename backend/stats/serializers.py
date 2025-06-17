from rest_framework import serializers
from music.models import Release, Track, Artist, Genre
from music.serializers import ArtistSerializer, GenreSerializer # Assuming these are your base serializers

class ArtistBasicStatsSerializer(serializers.Serializer):
    total_release_listens = serializers.IntegerField(default=0)
    total_track_listens = serializers.IntegerField(default=0)
    total_sales_count = serializers.IntegerField(default=0)
    total_sales_value_usd = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    current_follower_count = serializers.IntegerField(default=0)

class StatsReleaseSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True, allow_null=True)
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)
    # cover_art will use the model's ImageField and correctly generate a URL with context
    class Meta:
        model = Release
        fields = ['id', 'title', 'cover_art', 'listen_count', 'artist_name', 'release_type_display']
        read_only_fields = fields

class StatsTrackSerializer(serializers.ModelSerializer): # For general track stats display (e.g. artist dashboard)
    release_title = serializers.CharField(source='release.title', read_only=True, allow_null=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True, allow_null=True)
    release_id = serializers.IntegerField(source='release.id', read_only=True, allow_null=True) 
    cover_art = serializers.ImageField(source='release.cover_art', read_only=True, allow_null=True) 
    class Meta:
        model = Track
        fields = ['id', 'title', 'listen_count', 'duration_in_seconds', 
                  'release_title', 'artist_name', 'release_id', 'cover_art'] 
        read_only_fields = fields

class ArtistDashboardStatsSerializer(serializers.Serializer):
    summary = ArtistBasicStatsSerializer() 
    top_releases = StatsReleaseSerializer(many=True, read_only=True) 
    top_tracks = StatsTrackSerializer(many=True, read_only=True) # This one should be fine now     

# --- USER STATS SERIALIZERS ---

class UserListenedTrackStatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    duration_in_seconds = serializers.IntegerField(allow_null=True)
    release_title = serializers.CharField(allow_null=True, required=False)
    artist_name = serializers.CharField(allow_null=True, required=False)
    artist_id = serializers.IntegerField(allow_null=True, required=False)
    release_id = serializers.IntegerField(allow_null=True, required=False)
    # CHANGE HERE: Use CharField or URLField if you are passing the URL string
    cover_art = serializers.CharField(allow_null=True, required=False) 
    # If you want DRF to build the full URL:
    # cover_art = serializers.SerializerMethodField()
    user_listen_count = serializers.IntegerField()

    # If using SerializerMethodField for cover_art:
    # def get_cover_art(self, obj):
    #     request = self.context.get('request')
    #     cover_art_path = obj.get('cover_art') # Assuming 'cover_art' in obj dict is the relative path
    #     if request and cover_art_path:
    #         return request.build_absolute_uri(f'/media/{cover_art_path}') # Adjust /media/ prefix as needed
    #     return None


class UserListenedArtistStatSerializer(serializers.Serializer): 
    id = serializers.IntegerField()
    name = serializers.CharField()
    # CHANGE HERE: Use CharField or URLField if you are passing the URL string
    artist_picture = serializers.CharField(allow_null=True, required=False) 
    # If you want DRF to build the full URL:
    # artist_picture = serializers.SerializerMethodField()
    user_listen_count_for_artist = serializers.IntegerField()

    # If using SerializerMethodField for artist_picture:
    # def get_artist_picture(self, obj):
    #     request = self.context.get('request')
    #     picture_path = obj.get('artist_picture') # Assuming 'artist_picture' in obj dict is the relative path
    #     if request and picture_path:
    #         return request.build_absolute_uri(f'/media/{picture_path}') # Adjust /media/ prefix
    #     return None


class UserListenedGenreStatSerializer(serializers.ModelSerializer): 
    user_listen_count_for_genre = serializers.IntegerField() 
    class Meta:
        model = Genre
        fields = ['id', 'name', 'user_listen_count_for_genre']


class UserListeningHabitsSerializer(serializers.Serializer):
    top_listened_tracks = UserListenedTrackStatSerializer(many=True)
    top_listened_artists = UserListenedArtistStatSerializer(many=True)
    top_listened_genres = UserListenedGenreStatSerializer(many=True)
    total_listen_events_count = serializers.IntegerField(default=0)

class PlatformActivitySummarySerializer(serializers.Serializer):
    total_registered_users = serializers.IntegerField(default=0)
    total_artists = serializers.IntegerField(default=0)
    total_releases = serializers.IntegerField(default=0)
    total_tracks = serializers.IntegerField(default=0)
    total_listen_events = serializers.IntegerField(default=0)
    total_sales_count = serializers.IntegerField(default=0) # Across all orders
    total_sales_value_usd = serializers.DecimalField(max_digits=12, decimal_places=2, default=0.00) # Across all orders

class AdminDashboardStatsSerializer(serializers.Serializer):
    platform_summary = PlatformActivitySummarySerializer()
    most_popular_releases = StatsReleaseSerializer(many=True, read_only=True) # Top N by listen_count
    most_popular_tracks = StatsTrackSerializer(many=True, read_only=True)   # Top N by listen_count
    most_popular_genres = GenreSerializer(many=True, read_only=True)