from django.contrib import admin
from .models import Conversation, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'timestamp', 'is_read')
    can_delete = False
    ordering = ('timestamp',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants_display', 'created_at', 'updated_at')
    search_fields = ('participants__username',)
    filter_horizontal = ('participants',) # Good for M2M
    inlines = [MessageInline]

    def get_participants_display(self, obj):
        return ", ".join([user.username for user in obj.participants.all()[:3]]) + \
               ("..." if obj.participants.count() > 3 else "")
    get_participants_display.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_link', 'sender', 'short_text', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp', 'sender')
    search_fields = ('text', 'sender__username', 'conversation__id')
    readonly_fields = ('timestamp',)
    list_select_related = ('conversation', 'sender') # Optimization

    def short_text(self, obj):
        return (obj.text[:75] + '...') if len(obj.text) > 75 else obj.text
    short_text.short_description = 'Text'

    def conversation_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        return format_html('<a href="{}">Conversation #{}</a>', link, obj.conversation.id)
    conversation_link.short_description = 'Conversation'