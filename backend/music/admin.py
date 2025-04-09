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

# Inline editing for Tracks within a Release admin page
class TrackInline(admin.TabularInline):
    model = Track
    extra = 1 # How many empty forms to show
    fields = ('track_number', 'title', 'audio_file', 'genre', 'duration_in_seconds') 

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_type', 'release_date', 'is_published', 'is_visible')
    list_filter = ('release_type', 'is_published', 'artist', 'genre')
    search_fields = ('title', 'artist__name')
    inlines = [TrackInline]

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'release', 'track_number', 'genre', 'duration_in_seconds')
    list_filter = ('release__artist', 'genre')
    search_fields = ('title', 'release__title', 'release__artist__name')

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
