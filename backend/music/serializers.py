from rest_framework import serializers
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload # Added GeneratedDownload
from rest_framework.reverse import reverse # Import reverse
from decimal import Decimal # For validation

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
            'release', 
            'release_title', 'artist_name',
            'genres_data', 
            'genre_names', 
            'created_at'
        ]
        read_only_fields = [
            'release_title', 'artist_name', 'duration_in_seconds', 
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
    
    tracks = TrackSerializer(many=True, read_only=True) 
    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)
    pricing_model_display = serializers.CharField(source='get_pricing_model_display', read_only=True) 
    available_download_formats = serializers.SerializerMethodField() 

    # The 'download_file' (FileField) is for musician-uploaded ZIPs.
    # If we are fully replacing this with on-demand, we can remove it from fields for musician forms.
    # However, keeping it in the model/serializer allows admins to manage it or for legacy data.
    # For now, we'll keep it here but the frontend form will stop sending it.
    # If frontend sends `null` or omits it, it will be handled by model's save/clean.

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 'release_type', 'release_type_display', 'release_date',
            'cover_art', 
            'genres_data', 
            'genre_names', 
            'is_published', 'is_visible',
            'tracks', 
            'download_file', # Musician-uploaded ZIP (kept for legacy/admin, form will omit)
            'pricing_model', 
            'pricing_model_display',
            'price', 
            'currency', 
            'minimum_price_nyp',
            'available_download_formats',
            'created_at', 'updated_at'
         ]
        read_only_fields = ['is_visible', 'release_type_display', 'genres_data', 'artist', 'pricing_model_display', 'available_download_formats'] 
        # If 'download_file' is to be writeable by admin or specific scenarios, don't make it read_only.
        # If musician form should NOT be able to set it, control this in the view/form handling.

    def get_available_download_formats(self, obj: Release):
        # Logic to determine available formats based on uploaded track types
        # For simplicity now, return all. Enhance later.
        # This should check if all tracks are lossless to offer FLAC/WAV, etc.
        # If any track is lossy, then offering WAV/FLAC from that lossy source is not ideal.

        # Basic example:
        # has_lossless_tracks = any(t.audio_file.name.lower().endswith(('.wav', '.flac')) for t in obj.tracks.all() if t.audio_file)
        # formats = [{'value': GeneratedDownload.DownloadFormatChoices.MP3_320, 'label': GeneratedDownload.DownloadFormatChoices.MP3_320.label}]
        # if has_lossless_tracks:
        #     formats.append({'value': GeneratedDownload.DownloadFormatChoices.FLAC, 'label': GeneratedDownload.DownloadFormatChoices.FLAC.label})
        # return formats
        
        return [
            {'value': fmt.value, 'label': fmt.label}
            for fmt in GeneratedDownload.DownloadFormatChoices
        ]


    def validate(self, data):
        pricing_model = data.get('pricing_model', getattr(self.instance, 'pricing_model', None))
        price = data.get('price', getattr(self.instance, 'price', None))
        currency = data.get('currency', getattr(self.instance, 'currency', None))
        minimum_price_nyp = data.get('minimum_price_nyp', getattr(self.instance, 'minimum_price_nyp', None))
        
        # download_file is the musician-uploaded one. This validation might be removed if the field is deprecated from forms.
        # download_file = data.get('download_file', getattr(self.instance, 'download_file', None))

        if 'pricing_model' not in data and self.instance:
            pricing_model = self.instance.pricing_model
        
        if pricing_model == Release.PricingModel.PAID:
            if price is None: 
                raise serializers.ValidationError({"price": "Price is required for 'Paid' model."})
            # Price can be 0.00 for PAID model (e.g. "pay what you want starting from $0, but it's a 'purchase'")
            # Let's adjust to allow 0, but not negative.
            if isinstance(price, Decimal) and price < Decimal('0.00'):
                 raise serializers.ValidationError({"price": "Price cannot be negative."})
            elif not isinstance(price, Decimal) and float(price) < 0.00: # Handle string input before conversion
                 raise serializers.ValidationError({"price": "Price cannot be negative."})

            if not currency: 
                raise serializers.ValidationError({"currency": "Currency is required for 'Paid' model."})
        elif pricing_model == Release.PricingModel.NAME_YOUR_PRICE:
            if minimum_price_nyp is not None:
                if isinstance(minimum_price_nyp, Decimal) and minimum_price_nyp < Decimal('0.00'):
                    raise serializers.ValidationError({"minimum_price_nyp": "Minimum 'Name Your Price' cannot be negative."})
                elif not isinstance(minimum_price_nyp, Decimal) and float(minimum_price_nyp) < 0.00:
                    raise serializers.ValidationError({"minimum_price_nyp": "Minimum 'Name Your Price' cannot be negative."})
        
        # If on-demand ZIPs are the primary way, this validation for musician-uploaded 'download_file' becomes less critical
        # or might be removed if the field is removed from the forms.
        # if download_file and not pricing_model:
        #      raise serializers.ValidationError({'pricing_model': "A pricing model must be selected if a musician-uploaded download file is provided."})

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

        # Handle musician-uploaded download_file (if still part of the form/API)
        # If we remove it from the form, this part might not receive 'download_file' in validated_data
        download_file_data = validated_data.get('download_file', Ellipsis)
        if download_file_data is None: # Explicitly passed as null
            instance.download_file = None
            if 'download_file' in validated_data: validated_data.pop('download_file')
        elif download_file_data is not Ellipsis and download_file_data is not False:
            instance.download_file = download_file_data
            if 'download_file' in validated_data: validated_data.pop('download_file')
        # If download_file_data is Ellipsis, it means it wasn't in the request, so no change to instance.download_file from here.


        pricing_model = validated_data.get('pricing_model', instance.pricing_model)

        if pricing_model != Release.PricingModel.PAID:
            validated_data['price'] = None 
        else: 
            if 'price' not in validated_data and instance.price is None:
                 # If switching to PAID and price isn't provided, it's an issue.
                 # Backend model validation should catch this, but serializer can be more proactive.
                raise serializers.ValidationError({"price": "Price is required when switching to 'Paid' model."})
            if 'currency' not in validated_data and instance.currency is None:
                 validated_data['currency'] = 'USD' # Default currency if switching to PAID and not provided
        
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

# --- Serializers for GeneratedDownload ---
class GeneratedDownloadRequestSerializer(serializers.Serializer):
    requested_format = serializers.ChoiceField(choices=GeneratedDownload.DownloadFormatChoices.choices)
    # quality_options = serializers.JSONField(required=False) # If you add this later

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