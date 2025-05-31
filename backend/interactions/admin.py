from django.contrib import admin
from .models import Follow

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'artist_display', 'created_at')
    search_fields = ('user__username', 'artist__name')
    list_filter = ('created_at',)
    autocomplete_fields = ['user', 'artist']

    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = 'User (Follower)'

    def artist_display(self, obj):
        return obj.artist.name
    artist_display.short_description = 'Artist (Followed)'