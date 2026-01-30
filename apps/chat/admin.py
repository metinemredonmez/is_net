"""
IOSP - Chat Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['role', 'content_preview', 'confidence', 'is_helpful', 'created_at']
    fields = ['role', 'content_preview', 'confidence', 'is_helpful', 'created_at']
    can_delete = False
    max_num = 0

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('İçerik')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'message_count', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['title', 'user__email', 'messages__content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role_badge', 'content_preview', 'confidence_badge', 'is_helpful', 'created_at']
    list_filter = ['role', 'is_helpful', 'created_at']
    search_fields = ['content', 'conversation__title']
    readonly_fields = ['conversation', 'role', 'content', 'sources', 'confidence', 'tokens_used', 'response_time_ms', 'created_at']
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = _('İçerik')

    def role_badge(self, obj):
        colors = {
            'user': '#007bff',
            'assistant': '#28a745',
            'system': '#6c757d',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = _('Rol')

    def confidence_badge(self, obj):
        if obj.confidence is None:
            return '-'
        color = '#28a745' if obj.confidence > 0.7 else '#ffc107' if obj.confidence > 0.4 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.0%}</span>',
            color, obj.confidence
        )
    confidence_badge.short_description = _('Güven')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
