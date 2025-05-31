from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'recipient_username', 
        'notification_type', 
        'actor_display',
        'verb', 
        'is_read', 
        'created_at', 
        'is_artist_channel',
        'related_object_link'
    )
    list_filter = ('notification_type', 'is_read', 'is_artist_channel', 'created_at', 'recipient')
    search_fields = (
        'recipient__username', 
        'verb', 
        'description', 
        'actor_user__username', 
        'actor_artist__name'
    )
    readonly_fields = ('created_at',)
    autocomplete_fields = [
        'recipient', 
        'actor_user', 'actor_artist', 
        'target_release', 'target_artist_profile', 'target_user_profile', 
        'target_conversation', 'target_order'
    ]
    fieldsets = (
        ("Core Info", {
            'fields': ('recipient', 'notification_type', 'verb', 'description', 'is_read', 'is_artist_channel')
        }),
        ("Actor (Who performed the action)", {
            'fields': ('actor_user', 'actor_artist'),
            'classes': ('collapse',)
        }),
        ("Target (Primary object of notification)", {
            'fields': ('target_release', 'target_artist_profile', 'target_user_profile', 'target_conversation', 'target_order'),
            'classes': ('collapse',)
        }),
        ("Timestamps", {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def recipient_username(self, obj):
        return obj.recipient.username
    recipient_username.short_description = "Recipient"

    def actor_display(self, obj):
        if obj.actor_artist:
            return f"Artist: {obj.actor_artist.name}"
        if obj.actor_user:
            return f"User: {obj.actor_user.username}"
        return "System"
    actor_display.short_description = "Actor"

    def related_object_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        
        if obj.target_release:
            link = reverse("admin:music_release_change", args=[obj.target_release.id])
            return format_html('<a href="{}">Release: {}</a>', link, obj.target_release.title)
        if obj.target_artist_profile:
            link = reverse("admin:music_artist_change", args=[obj.target_artist_profile.id])
            return format_html('<a href="{}">Artist: {}</a>', link, obj.target_artist_profile.name)
        # Add more for other targets if needed
        return "N/A"
    related_object_link.short_description = "Related Object"