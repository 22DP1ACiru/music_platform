from rest_framework import serializers
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload
from rest_framework.reverse import reverse
from decimal import Decimal

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
    stream_url = serializers.SerializerMethodField() 

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'track_number', 
            'audio_file', 
            'stream_url', 
            'duration_in_seconds',
            'codec_name',
            'bit_rate',
            'sample_rate',
            'channels',
            'is_lossless',
            'release', 
            'release_title', 'artist_name',
            'genres_data', 
            'genre_names', 
            'created_at'
        ]
        read_only_fields = [
            'release_title', 'artist_name', 'duration_in_seconds', 
            'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless', # New read-only
            'genres_data', 'stream_url'
        ]

    def get_stream_url(self, obj: Track) -> str | None:
        request = self.context.get('request')
        if request is None or obj.pk is None: 
            return None
        try:
            return reverse('track-stream', kwargs={'track_id': obj.pk}, request=request)
        except Exception: 
            return None


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
        genre_names = validated_data.pop('genre_names', None)
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
    
    # Important: Ensure tracks are preloaded in the viewset for this to be efficient
    tracks = TrackSerializer(many=True, read_only=True) 
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)
    pricing_model_display = serializers.CharField(source='get_pricing_model_display', read_only=True) 
    available_download_formats = serializers.SerializerMethodField() 

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 'release_type', 'release_type_display', 'release_date',
            'cover_art', 
            'genres_data', 
            'genre_names', 
            'is_published', 'is_visible',
            'tracks',
            'download_file', 
            'pricing_model', 
            'pricing_model_display',
            'price', 
            'currency', 
            'minimum_price_nyp',
            'available_download_formats',
            'created_at', 'updated_at'
         ]
        read_only_fields = ['is_visible', 'release_type_display', 'genres_data', 'artist', 'pricing_model_display', 'available_download_formats'] 

    def get_available_download_formats(self, obj: Release):
        formats = []
        # The `obj.tracks` here will be instances of TrackSerializer output if context is a list view,
        # or actual Track model instances if it's a detail view and tracks are prefetched.
        # For ReleaseDetailView, `obj.tracks.all()` would be better to access model instances.
        # However, since `tracks` is a field in this serializer, it should be populated with
        # serialized track data, which includes the new metadata fields.
        
        # If `obj.tracks` is already serialized data (list of dicts from TrackSerializer):
        serialized_tracks = self.fields['tracks'].to_representation(obj.tracks.all()) if hasattr(obj.tracks, 'all') else obj.tracks


        if not serialized_tracks:
            return []

        all_tracks_are_lossless_uploads = True
        # Use a flag to see if any track is *not* marked as lossless or has unknown status
        for track_data in serialized_tracks:
            if track_data.get('is_lossless') is False or track_data.get('is_lossless') is None:
                all_tracks_are_lossless_uploads = False
                break
        
        # Common original format (simple check for now: if all are mp3)
        all_mp3_original = True
        for track_data in serialized_tracks:
            if track_data.get('codec_name') != 'mp3': # or check original_format if you had that
                all_mp3_original = False
                break

        # 1. ORIGINAL_ZIP - Always offer
        formats.append({
            'value': GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.value,
            'label': GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.label
        })

        # 2. MP3 options
        # Offer 320k unless all originals are already lower bitrate MP3s (e.g. all 192k)
        # This is a simplified check. A more precise check would involve looking at actual bit_rate.
        can_offer_mp3_320 = True # Assume yes initially
        # if all_mp3_original: # if all are mp3s, check if offering 320 makes sense
            # Example: if all tracks have bit_rate <= 192000, maybe don't offer 320k
            # For now, let's always offer it and let Celery handle not up-converting quality.
        if can_offer_mp3_320:
            formats.append({
                'value': GeneratedDownload.DownloadFormatChoices.MP3_320.value,
                'label': GeneratedDownload.DownloadFormatChoices.MP3_320.label
            })
        formats.append({
            'value': GeneratedDownload.DownloadFormatChoices.MP3_192.value,
            'label': GeneratedDownload.DownloadFormatChoices.MP3_192.label
        })
        
        # 3. Lossless options (FLAC, WAV) - only if all original uploads were lossless
        if all_tracks_are_lossless_uploads:
            formats.append({
                'value': GeneratedDownload.DownloadFormatChoices.FLAC.value,
                'label': GeneratedDownload.DownloadFormatChoices.FLAC.label
            })
            formats.append({
                'value': GeneratedDownload.DownloadFormatChoices.WAV.value,
                'label': GeneratedDownload.DownloadFormatChoices.WAV.label
            })
        
        # Deduplicate and order logic (optional, if above logic could create dupes)
        final_formats = []
        seen_values = set()
        # Define preferred order
        preferred_order = [
            GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.value,
            GeneratedDownload.DownloadFormatChoices.FLAC.value,
            GeneratedDownload.DownloadFormatChoices.WAV.value,
            GeneratedDownload.DownloadFormatChoices.MP3_320.value,
            GeneratedDownload.DownloadFormatChoices.MP3_192.value,
        ]
        # Add available formats in preferred order
        for p_val in preferred_order:
            for fmt in formats:
                if fmt['value'] == p_val and p_val not in seen_values:
                    final_formats.append(fmt)
                    seen_values.add(p_val)
        # Add any other formats not in preferred order (if any)
        for fmt in formats:
            if fmt['value'] not in seen_values:
                 final_formats.append(fmt)
                 seen_values.add(fmt['value'])

        return final_formats


    def validate(self, data):
        pricing_model = data.get('pricing_model', getattr(self.instance, 'pricing_model', None))
        price = data.get('price', getattr(self.instance, 'price', None))
        currency = data.get('currency', getattr(self.instance, 'currency', None))
        minimum_price_nyp = data.get('minimum_price_nyp', getattr(self.instance, 'minimum_price_nyp', None))
        
        if 'pricing_model' not in data and self.instance:
            pricing_model = self.instance.pricing_model
        
        if pricing_model == Release.PricingModel.PAID:
            if price is None: 
                raise serializers.ValidationError({"price": "Price is required for 'Paid' model."})
            if isinstance(price, Decimal) and price < Decimal('0.00'):
                 raise serializers.ValidationError({"price": "Price cannot be negative."})
            elif not isinstance(price, Decimal) and float(price) < 0.00: 
                 raise serializers.ValidationError({"price": "Price cannot be negative."})

            if not currency: 
                raise serializers.ValidationError({"currency": "Currency is required for 'Paid' model."})
        elif pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if minimum_price_nyp is not None:
                if isinstance(minimum_price_nyp, Decimal) and minimum_price_nyp < Decimal('0.00'):
                    raise serializers.ValidationError({"minimum_price_nyp": "Minimum 'Name Your Price' cannot be negative."})
                elif not isinstance(minimum_price_nyp, Decimal) and float(minimum_price_nyp) < 0.00:
                    raise serializers.ValidationError({"minimum_price_nyp": "Minimum 'Name Your Price' cannot be negative."})
        
        return data

    def create(self, validated_data):
        genre_names = validated_data.pop('genre_names', [])
        if validated_data.get('pricing_model') == Release.PricingModel.PAID:
            if validated_data.get('price') is None or validated_data.get('currency') is None:
                raise serializers.ValidationError("Price and Currency are required for 'Paid' releases.")
        
        release = Release.objects.create(**validated_data) 
        
        genres_to_set = []
        for name in genre_names:
            genre, created = Genre.objects.get_or_create(name__iexact=name.strip(), defaults={'name': name.strip()})
            genres_to_set.append(genre)
        if genres_to_set: 
            release.genres.set(genres_to_set)
        return release

    def update(self, instance, validated_data):
        genre_names = validated_data.pop('genre_names', None) 
        
        cover_art_data = validated_data.get('cover_art', Ellipsis) 
        if cover_art_data is None: 
            instance.cover_art = None
            validated_data.pop('cover_art') 
        elif cover_art_data is not Ellipsis and cover_art_data is not False : 
             instance.cover_art = cover_art_data
             validated_data.pop('cover_art')

        download_file_data = validated_data.get('download_file', Ellipsis)
        if download_file_data is None: 
            instance.download_file = None
            if 'download_file' in validated_data: validated_data.pop('download_file')
        elif download_file_data is not Ellipsis and download_file_data is not False:
            instance.download_file = download_file_data
            if 'download_file' in validated_data: validated_data.pop('download_file')
        
        pricing_model = validated_data.get('pricing_model', instance.pricing_model)

        if pricing_model != Release.PricingModel.PAID:
            validated_data['price'] = None 
        else: 
            if 'price' not in validated_data and instance.price is None:
                raise serializers.ValidationError({"price": "Price is required when switching to 'Paid' model."})
            if 'currency' not in validated_data and instance.currency is None:
                 validated_data['currency'] = 'USD' 
        
        if pricing_model != Release.PricingModel.NAME_YOUR_PRICE:
            validated_data['minimum_price_nyp'] = None

        instance = super().update(instance, validated_data) 

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

class GeneratedDownloadRequestSerializer(serializers.Serializer):
    requested_format = serializers.ChoiceField(choices=GeneratedDownload.DownloadFormatChoices.choices)

class GeneratedDownloadStatusSerializer(serializers.ModelSerializer):
    release_title = serializers.CharField(source='release.title', read_only=True)
    download_url = serializers.SerializerMethodField()
    requested_format_display = serializers.CharField(source='get_requested_format_display', read_only=True)


    class Meta:
        model = GeneratedDownload
        fields = [
            'id', 'unique_identifier', 'release', 'release_title', 'user', 
            'requested_format', 'requested_format_display', 'status', 'celery_task_id',
            'download_url', 
            'created_at', 'updated_at', 'expires_at', 'failure_reason'
        ]
        read_only_fields = fields 

    def get_download_url(self, obj: GeneratedDownload):
        request = self.context.get('request')
        if obj.status == GeneratedDownload.StatusChoices.READY and obj.download_file and request:
            return reverse('generated-download-file', kwargs={'download_uuid': str(obj.unique_identifier)}, request=request)
        return None