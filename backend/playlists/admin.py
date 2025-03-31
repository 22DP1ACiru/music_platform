from django.contrib import admin
from .models import Playlist

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_public', 'updated_at')
    list_filter = ('is_public', 'owner')
    search_fields = ('title', 'owner__username')
    filter_horizontal = ('tracks',) # Better UI for ManyToManyField with tracks