from django.contrib import admin
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload # Added GeneratedDownload

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
    fields = ('track_number', 'title', 'audio_file', 'duration_in_seconds') 
    readonly_fields = ('duration_in_seconds',)

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
        ('Musician-Uploaded Download & Pricing', { # Clarified this section
            'fields': ('download_file', 'pricing_model', 'price', 'currency', 'minimum_price_nyp'),
            'description': "Configure download options and pricing for this release based on a musician-provided file."
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'release', 'track_number', 'duration_in_seconds') 
    list_filter = ('release__artist',) 
    search_fields = ('title', 'release__title', 'release__artist__name', 'genres__name')
    readonly_fields = ('duration_in_seconds',)
    filter_horizontal = ('genres',)

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
    readonly_fields = ('created_at', 'updated_at', 'celery_task_id', 'download_file', 'unique_identifier', 'failure_reason')
    actions = ['cleanup_expired_files']

    def cleanup_expired_files(self, request, queryset):
        # Example action: find expired and FAILED/READY items and delete their files
        # This should ideally be a periodic Celery task, but an admin action can be useful
        count = 0
        for item in queryset.filter(models.Q(expires_at__lt=timezone.now()) | models.Q(status=GeneratedDownload.StatusChoices.FAILED)):
            if item.download_file:
                try:
                    item.download_file.delete(save=False) # Delete file from storage
                    item.status = GeneratedDownload.StatusChoices.EXPIRED # Or some other status
                    item.save(update_fields=['status', 'download_file'])
                    count +=1
                except Exception as e:
                    logger.error(f"Failed to cleanup generated file for {item.id}: {e}")
        self.message_user(request, f"Cleaned up {count} expired/failed download files.")
    cleanup_expired_files.short_description = "Cleanup selected expired/failed download files"