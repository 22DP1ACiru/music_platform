from rest_framework import serializers
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload, ListenEvent 
from rest_framework.reverse import reverse
from decimal import Decimal
from django.utils.dateparse import parse_datetime 
from django.utils.translation import gettext_lazy as _ 
from rest_framework.validators import UniqueValidator 

class ListenSegmentLogSerializer(serializers.Serializer):
    segment_start_timestamp_utc = serializers.DateTimeField(
        help_text="ISO 8601 UTC timestamp when the unmuted segment started playing."
    )
    segment_duration_ms = serializers.IntegerField(
        min_value=0, 
        help_text="Duration of the unmuted segment in milliseconds."
    )

    def validate_segment_start_timestamp_utc(self, value):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise serializers.ValidationError("Timestamp must be timezone-aware (UTC).")
        return value


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
    release_cover_art = serializers.ImageField(source='release.cover_art', read_only=True, allow_null=True)
    release_id = serializers.IntegerField(source='release.id', read_only=True)
    artist_id = serializers.IntegerField(source='release.artist.id', read_only=True)
    genres_data = GenreSerializer(source='genres', many=True, read_only=True) 
    genre_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        write_only=True,
        required=False 
    )
    stream_url = serializers.SerializerMethodField() 
    listen_count = serializers.IntegerField(read_only=True) 

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
            'release_id', 
            'artist_id', 
            'release_title', 
            'artist_name',
            'release_cover_art', 
            'genres_data', 
            'genre_names', 
            'listen_count', 
            'created_at'
        ]
        read_only_fields = [
            'release_id', 'artist_id', 'release_title', 'artist_name', 'release_cover_art', 
            'duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 
            'channels', 'is_lossless', 'genres_data', 'stream_url', 
            'listen_count' 
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
    
    product_info_id = serializers.IntegerField(source='product_info.id', read_only=True, allow_null=True)
    listen_count = serializers.IntegerField(read_only=True) 

    class Meta:
        model = Release
        fields = [
            'id', 'title', 'artist', 'artist_id', 
            'product_info_id', 
            'release_type', 'release_type_display', 'release_date',
            'cover_art', 
            'genres_data', 
            'genre_names', 
            'is_published', 'is_visible',
            'tracks',
            'pricing_model', 
            'pricing_model_display',
            'price', 
            'currency', 
            'minimum_price_nyp',
            'available_download_formats',
            'listen_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'is_visible', 'release_type_display', 'genres_data', 'artist', 
            'pricing_model_display', 'available_download_formats',
            'product_info_id', 'listen_count' 
        ]

    def get_available_download_formats(self, obj: Release):
        formats = []
        serialized_tracks = self.fields['tracks'].to_representation(obj.tracks.all()) if hasattr(obj.tracks, 'all') else obj.tracks

        if not serialized_tracks: return []

        all_tracks_are_lossless_uploads = True
        for track_data in serialized_tracks:
            if track_data.get('is_lossless') is False or track_data.get('is_lossless') is None:
                all_tracks_are_lossless_uploads = False
                break
        
        all_mp3_original = True
        for track_data in serialized_tracks:
            if track_data.get('codec_name') != 'mp3': 
                all_mp3_original = False
                break

        formats.append({'value': GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.value, 'label': GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.label})
        
        can_offer_mp3_320 = True 
        if can_offer_mp3_320:
            formats.append({'value': GeneratedDownload.DownloadFormatChoices.MP3_320.value, 'label': GeneratedDownload.DownloadFormatChoices.MP3_320.label})
        formats.append({'value': GeneratedDownload.DownloadFormatChoices.MP3_192.value, 'label': GeneratedDownload.DownloadFormatChoices.MP3_192.label})
        
        if all_tracks_are_lossless_uploads:
            formats.append({'value': GeneratedDownload.DownloadFormatChoices.FLAC.value, 'label': GeneratedDownload.DownloadFormatChoices.FLAC.label})
            formats.append({'value': GeneratedDownload.DownloadFormatChoices.WAV.value, 'label': GeneratedDownload.DownloadFormatChoices.WAV.label})
        
        final_formats = []
        seen_values = set()
        preferred_order = [
            GeneratedDownload.DownloadFormatChoices.ORIGINAL_ZIP.value,
            GeneratedDownload.DownloadFormatChoices.FLAC.value,
            GeneratedDownload.DownloadFormatChoices.WAV.value,
            GeneratedDownload.DownloadFormatChoices.MP3_320.value,
            GeneratedDownload.DownloadFormatChoices.MP3_192.value,
        ]
        for p_val in preferred_order:
            for fmt in formats:
                if fmt['value'] == p_val and p_val not in seen_values:
                    final_formats.append(fmt)
                    seen_values.add(p_val)
        for fmt in formats:
            if fmt['value'] not in seen_values:
                 final_formats.append(fmt)
                 seen_values.add(p_val)
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
    effective_title = serializers.CharField(source='get_effective_title', read_only=True)
    effective_image_url = serializers.SerializerMethodField(read_only=True)
    release_artist_name = serializers.CharField(source='release.artist.name', read_only=True, allow_null=True) 
    release_title = serializers.CharField(source='release.title', read_only=True, allow_null=True)

    release = serializers.PrimaryKeyRelatedField(
        queryset=Release.objects.all(), 
        allow_null=True, 
        required=False 
    )
    created_by = serializers.StringRelatedField(read_only=True)
    
    order = serializers.IntegerField(
        validators=[
            UniqueValidator(
                queryset=Highlight.objects.all(),
                message=_("Highlight with this order already exists.")
            )
        ]
    )
    link_url = serializers.URLField(required=False, allow_blank=True, allow_null=True) # New field

    class Meta:
        model = Highlight
        fields = [
            'id', 
            'release', 
            'release_title', 
            'release_artist_name',
            'effective_title', 
            'title', 
            'subtitle', 
            'description', 
            'custom_carousel_image',
            'effective_image_url', 
            'link_url', # Added to fields
            'order',
            'display_start_datetime', 
            'display_end_datetime',   
            'is_active',
            'created_by', 
            'created_at', 
            'updated_at', 
        ]
        read_only_fields = [
            'effective_title', 'effective_image_url', 'release_artist_name', 'release_title',
            'created_by', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'custom_carousel_image': {'required': False, 'allow_null': True},
            'title': {'required': False, 'allow_blank': True, 'max_length': 70},
            'subtitle': {'required': False, 'allow_blank': True, 'max_length': 64},
            'description': {'required': False, 'allow_blank': True, 'max_length': 255},
            'display_end_datetime': {'required': False, 'allow_null': True},
            'link_url': {'required': False, 'allow_blank': True, 'allow_null': True} # Added
        }
    
    def get_effective_image_url(self, obj: Highlight):
        request = self.context.get('request')
        image_url = obj.get_effective_image_url()
        if image_url and request:
            return request.build_absolute_uri(image_url)
        return None

    def validate(self, data):
        release = data.get('release', getattr(self.instance, 'release', None))
        title = data.get('title', getattr(self.instance, 'title', None))
        custom_image = data.get('custom_carousel_image', getattr(self.instance, 'custom_carousel_image', None))
        link_url = data.get('link_url', getattr(self.instance, 'link_url', None))

        # If no Release is linked, a Title, Image, and Link URL are now required
        if not release:
            if not title:
                raise serializers.ValidationError({
                    "title": _("A Title is required if no Release is selected for the Highlight.")
                })
            if not custom_image and not (self.instance and self.instance.custom_carousel_image):
                # Check if we're updating and there's an existing image
                if not (self.instance and self.instance.custom_carousel_image and 'custom_carousel_image' not in self.initial_data):
                    raise serializers.ValidationError({
                        "custom_carousel_image": _("A Custom Image is required if no Release is selected.")
                    })
            if not link_url:
                raise serializers.ValidationError({
                    "link_url": _("A Link URL is required if no Release is selected for the Highlight.")
                })
        return data

    def validate_order(self, value):
        queryset = Highlight.objects.all() 
        if self.instance: 
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.filter(order=value).exists():
            raise serializers.ValidationError(_("Highlight with this order already exists."))
        return value


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