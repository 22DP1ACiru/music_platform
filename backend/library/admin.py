from django.contrib import admin
from .models import UserLibraryItem

@admin.register(UserLibraryItem)
class UserLibraryItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'release_title', 'acquired_at', 'acquisition_type')
    list_filter = ('acquisition_type', 'user', 'acquired_at')
    search_fields = ('user__username', 'release__title')
    autocomplete_fields = ['user', 'release'] # Makes selecting easier

    def release_title(self, obj):
        return obj.release.title
    release_title.short_description = 'Release'
    release_title.admin_order_field = 'release__title'