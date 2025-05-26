from django.contrib import admin
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload # Added GeneratedDownload
from django.utils import timezone # For admin action
from django.db import models # For Q objects in admin action (if still needed)
import logging # For admin action logging

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
    # Add new metadata fields as readonly
    fields = ('track_number', 'title', 'audio_file', 'duration_in_seconds', 
              'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless') 
    readonly_fields = ('duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless')

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_type', 'pricing_model', 'price', 'currency', 'release_date', 'is_published', 'is_visible')
    list_filter = ('release_type', 'is_published', 'artist', 'pricing_model', 'currency') 
    search_fields = ('title', 'artist__name', 'genres__name') 
    inlines = [TrackInline]
    filter_horizontal = ('genres',) 
    fieldsets = (
        (None, {
            'fields': ('title', 'artist', 'release_type', 'release_date', 'cover_art', 'genres', 'is_published')
        }),
        ('Musician-Uploaded Download & Pricing', { 
            'fields': ('download_file', 'pricing_model', 'price', 'currency', 'minimum_price_nyp'),
            'description': "Configure download options and pricing for this release based on a musician-provided file."
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'release', 'track_number', 'duration_in_seconds', 'codec_name', 'is_lossless') 
    list_filter = ('release__artist', 'is_lossless', 'codec_name', 'sample_rate') 
    search_fields = ('title', 'release__title', 'release__artist__name', 'genres__name')
    # Add new metadata fields as readonly
    readonly_fields = ('duration_in_seconds', 'codec_name', 'bit_rate', 'sample_rate', 'channels', 'is_lossless')
    filter_horizontal = ('genres',)
    # Optionally, group fields in fieldsets for better organization
    fieldsets = (
        (None, {
            'fields': ('release', 'title', 'track_number', 'audio_file', 'genres')
        }),
        ('Audio Metadata (Auto-populated)', {
            'classes': ('collapse',), # Make it collapsible
            'fields': readonly_fields,
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
        # Filter for items that are expired OR failed.
        # For READY items, expiry is checked by `expires_at`. For PENDING/PROCESSING, they might become FAILED.
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
                    item.download_file.delete(save=False) # Delete file from storage
                    item.status = GeneratedDownload.StatusChoices.EXPIRED # Mark as expired/cleaned
                    item.failure_reason = (item.failure_reason or "") + "\nAdmin cleanup action."
                    item.save(update_fields=['status', 'download_file', 'failure_reason'])
                    count +=1
                    logger.info(f"Admin action: Successfully deleted file and updated status for GeneratedDownload ID {item.id}")
                except Exception as e:
                    logger.error(f"Admin action: Failed to cleanup generated file for {item.id}: {e}")
        self.message_user(request, f"Attempted cleanup for {items_to_cleanup.count()} items. Successfully cleaned up files for {count} items.")
    cleanup_expired_files.short_description = "Cleanup selected failed/expired download files"