from rest_framework import serializers
# Remove these as they are not directly used here if we use the specific Stats...Serializers
# from music.serializers import ReleaseSerializer, TrackSerializer 
from music.models import Release, Track # <--- ADD THIS LINE

class ArtistBasicStatsSerializer(serializers.Serializer):
    total_release_listens = serializers.IntegerField(default=0)
    total_track_listens = serializers.IntegerField(default=0)
    total_sales_count = serializers.IntegerField(default=0)
    total_sales_value_usd = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    current_follower_count = serializers.IntegerField(default=0)

class StatsReleaseSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True, allow_null=True)
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True) # Ensure this is correct if get_release_type_display exists on model or add to fields
    class Meta:
        model = Release
        fields = ['id', 'title', 'cover_art', 'listen_count', 'artist_name', 'release_type_display']
        read_only_fields = fields


class StatsTrackSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True, allow_null=True)
    artist_name = serializers.CharField(source='release.artist.name', read_only=True, allow_null=True)
    class Meta:
        model = Track
        fields = ['id', 'title', 'listen_count', 'duration_in_seconds', 'release_title', 'artist_name']
        read_only_fields = fields


class ArtistDashboardStatsSerializer(serializers.Serializer):
    summary = ArtistBasicStatsSerializer() 
    top_releases = StatsReleaseSerializer(many=True, read_only=True) 
    top_tracks = StatsTrackSerializer(many=True, read_only=True)     