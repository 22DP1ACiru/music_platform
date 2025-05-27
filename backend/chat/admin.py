from django.contrib import admin
from .models import Conversation, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'attachment', 'message_type', 'timestamp', 'is_read')
    fields = ('sender', 'text', 'attachment', 'message_type', 'timestamp', 'is_read')
    can_delete = False 
    ordering = ('timestamp',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants_display', 'initiator', 'related_artist_display', 'is_accepted', 'created_at', 'updated_at')
    search_fields = ('participants__username', 'initiator__username', 'related_artist__name')
    list_filter = ('is_accepted', 'created_at', 'updated_at', 'related_artist')
    filter_horizontal = ('participants',) 
    inlines = [MessageInline]
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('initiator', 'related_artist') # For performance

    def get_participants_display(self, obj):
        return ", ".join([user.username for user in obj.participants.all()[:3]]) + \
               ("..." if obj.participants.count() > 3 else "")
    get_participants_display.short_description = 'Participants'

    def related_artist_display(self, obj):
        return obj.related_artist.name if obj.related_artist else "N/A (User DM)"
    related_artist_display.short_description = 'Artist Context'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_link', 'sender', 'message_type', 'short_text', 'attachment_info', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp', 'sender', 'message_type')
    search_fields = ('text', 'sender__username', 'conversation__id')
    readonly_fields = ('timestamp',)
    list_select_related = ('conversation', 'sender', 'conversation__related_artist') 

    def short_text(self, obj):
        if obj.text:
            return (obj.text[:75] + '...') if len(obj.text) > 75 else obj.text
        return "N/A (Attachment)"
    short_text.short_description = 'Text Snippet'

    def attachment_info(self,obj):
        if obj.attachment and obj.attachment.name:
            return obj.attachment.name.split('/')[-1] 
        return "No attachment"
    attachment_info.short_description = "Attachment"
    
    def conversation_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        return format_html('<a href="{}">Conversation #{} {}</a>', 
                           link, 
                           obj.conversation.id,
                           f"(Artist: {obj.conversation.related_artist.name})" if obj.conversation.related_artist else "")
    conversation_link.short_description = 'Conversation'