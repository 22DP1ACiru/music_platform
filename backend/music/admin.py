from django.contrib import admin
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload, ListenEvent 
from django.utils import timezone 
from django.db import models 
import logging 

logger = logging.getLogger(__name__)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'location')
    search_fields = ('name', 'user__username', 'location')
    fields = ('user', 'name', 'bio', 'artist_picture', 'location', 'website_url')

class TrackInline(admin.TabularInline):
    model = Track
    extra = 1 
    fields = ('track_number', 'title', 'audio_file', 'duration_in_seconds', 
              'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless', 'listen_count') 
    readonly_fields = ('duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless', 'listen_count')

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_type', 'pricing_model', 'price', 'currency', 'release_date', 'is_published', 'is_visible', 'listen_count')
    list_filter = ('release_type', 'is_published', 'artist', 'pricing_model', 'currency') 
    search_fields = ('title', 'artist__name', 'genres__name') 
    inlines = [TrackInline]
    filter_horizontal = ('genres',) 
    readonly_fields = ('listen_count',) 
    fieldsets = (
        (None, {
            'fields': ('title', 'artist', 'release_type', 'release_date', 'cover_art', 'genres', 'is_published', 'listen_count') 
        }),
        ('Pricing & Download (Generated)', { # Updated section title
            'fields': ('pricing_model', 'price', 'currency', 'minimum_price_nyp'),
            'description': "Configure pricing. Downloads are auto-generated from track files."
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'release', 'track_number', 'duration_in_seconds', 'codec_name', 'is_lossless', 'listen_count') 
    list_filter = ('release__artist', 'is_lossless', 'codec_name', 'sample_rate') 
    search_fields = ('title', 'release__title', 'release__artist__name', 'genres__name')
    readonly_fields = ('duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless', 'listen_count') 
    filter_horizontal = ('genres',)
    fieldsets = (
        (None, {
            'fields': ('release', 'title', 'track_number', 'audio_file', 'genres', 'listen_count') 
        }),
        ('Audio Metadata (Auto-populated)', {
            'classes': ('collapse',), 
            'fields': ('duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless'),
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'timestamp_seconds', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('text', 'user__username', 'track__title')

@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ('release', 'highlighted_by', 'highlighted_at', 'is_active', 'order')
    list_filter = ('is_active', 'highlighted_by')
    search_fields = ('release__title', 'release__artist__name')

@admin.register(GeneratedDownload)
class GeneratedDownloadAdmin(admin.ModelAdmin):
    list_display = ('id', 'release', 'user', 'requested_format', 'status', 'celery_task_id', 'created_at', 'expires_at')
    list_filter = ('status', 'requested_format', 'created_at', 'expires_at')
    search_fields = ('release__title', 'user__username', 'celery_task_id', 'unique_identifier')
    readonly_fields = ('id','unique_identifier', 'release', 'user', 'requested_format', 'celery_task_id', 'download_file', 'created_at', 'updated_at', 'expires_at', 'failure_reason')
    actions = ['cleanup_expired_files']

    def cleanup_expired_files(self, request, queryset):
        count = 0
        now = timezone.now()
        items_to_cleanup = queryset.filter(
            models.Q(status=GeneratedDownload.StatusChoices.FAILED) |
            models.Q(status=GeneratedDownload.StatusChoices.EXPIRED) |
            (models.Q(status=GeneratedDownload.StatusChoices.READY) & models.Q(expires_at__lt=now))
        )

        for item in items_to_cleanup:
            if item.download_file and item.download_file.name:
                try:
                    logger.info(f"Admin action: Attempting to delete file {item.download_file.name} for GeneratedDownload ID {item.id}")
                    item.download_file.delete(save=False) 
                    item.status = GeneratedDownload.StatusChoices.EXPIRED 
                    item.failure_reason = (item.failure_reason or "") + "\nAdmin cleanup action."
                    item.save(update_fields=['status', 'download_file', 'failure_reason'])
                    count +=1
                    logger.info(f"Admin action: Successfully deleted file and updated status for GeneratedDownload ID {item.id}")
                except Exception as e:
                    logger.error(f"Admin action: Failed to cleanup generated file for {item.id}: {e}")
        self.message_user(request, f"Attempted cleanup for {items_to_cleanup.count()} items. Successfully cleaned up files for {count} items.")
    cleanup_expired_files.short_description = "Cleanup selected failed/expired download files"

@admin.register(ListenEvent)
class ListenEventAdmin(admin.ModelAdmin):
    list_display = (
        'track_title_link', 
        'release_title_link', 
        'user_display', 
        'listen_start_timestamp_utc',
        'reported_listen_duration_ms',
        'listened_at' 
    )
    list_filter = ('listened_at', 'track__release__artist', 'user') 
    search_fields = ('track__title', 'release__title', 'user__username')
    readonly_fields = (
        'user', 
        'track', 
        'release', 
        'listen_start_timestamp_utc', 
        'reported_listen_duration_ms', 
        'listened_at',
    )
    list_select_related = ('user', 'track', 'release', 'track__release__artist')

    def track_title_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:music_track_change", args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', link, obj.track.title)
    track_title_link.short_description = 'Track'
    track_title_link.admin_order_field = 'track__title'

    def release_title_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.release:
            link = reverse("admin:music_release_change", args=[obj.release.id])
            return format_html('<a href="{}">{}</a>', link, obj.release.title)
        return '-'
    release_title_link.short_description = 'Release'
    release_title_link.admin_order_field = 'release__title'

    def user_display(self, obj):
        return obj.user.username if obj.user else "Anonymous"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'