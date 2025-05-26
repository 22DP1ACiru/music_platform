from django.contrib import admin
from .models import Genre, Artist, Release, Track, Comment, Highlight

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
        ('Download & Pricing', {
            'fields': ('download_file', 'pricing_model', 'price', 'currency', 'minimum_price_nyp'),
            'description': "Configure download options and pricing for this release."
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Conditional logic for fields can be added here if needed,
        # e.g. hide price if pricing_model is not PAID.
        # For simplicity, Django admin handles nullable fields well.
        # Frontend forms are better for complex conditional UI.
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