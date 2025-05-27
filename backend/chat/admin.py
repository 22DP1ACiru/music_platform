from django.contrib import admin
from .models import Conversation, Message 
from django.utils.html import format_html 

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = (
        'get_sender_display_inline', 
        'text', 
        'message_type', 
        'attachment_info_inline', 
        'timestamp', 
        'is_read'
    )
    readonly_fields = (
        'get_sender_display_inline', 
        'attachment_info_inline', 
        'timestamp', 
        'is_read'
    )
    can_delete = False 
    ordering = ('timestamp',)

    def get_sender_display_inline(self, obj):
        if obj.sender_identity_type == Message.SenderIdentity.ARTIST and obj.sending_artist:
            return f"{obj.sending_artist.name} (Artist)"
        elif obj.sender_user:
            return obj.sender_user.username
        return "N/A"
    get_sender_display_inline.short_description = 'Sent As'

    def attachment_info_inline(self, obj):
        if obj.original_attachment_filename:
            return obj.original_attachment_filename
        if obj.attachment and obj.attachment.name:
            return obj.attachment.name.split('/')[-1]
        return "No Attachment"
    attachment_info_inline.short_description = 'Attachment'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'get_participants_display', 
        'initiator_combined_display', 
        'related_artist_recipient_display', # Corrected display method name here too if it changed
        'is_accepted', 
        'created_at', 
        'updated_at'
    )
    search_fields = (
        'participants__username', 
        'initiator_user__username', 
        'initiator_artist_profile__name', 
        'related_artist_recipient__name' 
    )
    # CORRECTED LINE:
    list_filter = ('is_accepted', 'created_at', 'updated_at', 'initiator_identity_type', 'related_artist_recipient') 
    filter_horizontal = ('participants',) 
    inlines = [MessageInline]
    readonly_fields = ('created_at', 'updated_at', 'initiator_user', 'initiator_identity_type', 'initiator_artist_profile') 
    fields = (
        'participants', 
        'initiator_user', 
        'initiator_identity_type', 
        'initiator_artist_profile',
        'related_artist_recipient',
        'is_accepted',
        'created_at',
        'updated_at'
    ) 
    list_select_related = ('initiator_user', 'initiator_artist_profile', 'related_artist_recipient') 

    def get_participants_display(self, obj):
        return ", ".join([user.username for user in obj.participants.all()[:3]]) + \
               ("..." if obj.participants.count() > 3 else "")
    get_participants_display.short_description = 'Participants'

    def initiator_combined_display(self, obj): 
        if not obj.initiator_user:
            return "N/A"
        if obj.initiator_identity_type == Conversation.IdentityType.ARTIST and obj.initiator_artist_profile:
            return f"{obj.initiator_artist_profile.name} [Artist] (via {obj.initiator_user.username})"
        return f"{obj.initiator_user.username} [User]"
    initiator_combined_display.short_description = 'Initiated By'
    initiator_combined_display.admin_order_field = 'initiator_user__username' 

    def related_artist_recipient_display(self, obj): 
        return obj.related_artist_recipient.name if obj.related_artist_recipient else "N/A (User DM)"
    related_artist_recipient_display.short_description = 'Recipient Artist Context'
    related_artist_recipient_display.admin_order_field = 'related_artist_recipient__name'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'conversation_link', 
        'get_sender_display_admin', 
        'message_type', 
        'short_text', 
        'attachment_info_admin', 
        'timestamp', 
        'is_read'
    )
    list_filter = ('is_read', 'timestamp', 'sender_user', 'sender_identity_type', 'message_type', 'sending_artist')
    search_fields = ('text', 'sender_user__username', 'sending_artist__name', 'conversation__id', 'original_attachment_filename')
    readonly_fields = ('timestamp', 'sender_user', 'sender_identity_type', 'sending_artist', 'attachment', 'original_attachment_filename', 'conversation') 
    fields = (
        'conversation_link_field', 
        'sender_user', 
        'sender_identity_type', 
        'sending_artist', 
        'text', 
        'message_type', 
        'attachment', 
        'original_attachment_filename', 
        'is_read', 
        'timestamp'
    )
    list_select_related = ('conversation', 'sender_user', 'sending_artist', 'conversation__related_artist_recipient') # Corrected related_artist_recipient

    def get_sender_display_admin(self, obj):
        if obj.sender_identity_type == Message.SenderIdentity.ARTIST and obj.sending_artist:
            return format_html(f"{obj.sending_artist.name} (Artist)<br><small>via {obj.sender_user.username}</small>")
        elif obj.sender_user:
            return obj.sender_user.username
        return "N/A"
    get_sender_display_admin.short_description = 'Sent As'
    get_sender_display_admin.admin_order_field = 'sender_user__username' 

    def short_text(self, obj):
        if obj.text:
            return (obj.text[:75] + '...') if len(obj.text) > 75 else obj.text
        return "N/A (Attachment)"
    short_text.short_description = 'Text Snippet'

    def attachment_info_admin(self,obj):
        if obj.original_attachment_filename: 
            return obj.original_attachment_filename
        if obj.attachment and obj.attachment.name:
            return obj.attachment.name.split('/')[-1] 
        return "No attachment"
    attachment_info_admin.short_description = "Attachment"
    
    def conversation_link(self, obj): 
        from django.urls import reverse
        link = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        conv_display = f"Conv #{obj.conversation.id}"
        if obj.conversation.related_artist_recipient: 
            conv_display += f" (to Artist: {obj.conversation.related_artist_recipient.name})"
        return format_html('<a href="{}">{}</a>', link, conv_display)
    conversation_link.short_description = 'Conversation'

    def conversation_link_field(self, obj): 
        if obj.pk and obj.conversation: 
             return self.conversation_link(obj)
        return "N/A (New Message)"
    conversation_link_field.short_description = 'Conversation'

    def get_readonly_fields(self, request, obj=None):
        if obj: 
            return self.readonly_fields 
        return ('timestamp', 'original_attachment_filename') 