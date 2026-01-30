"""
IOSP - Documents Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Document, DocumentCategory, DocumentChunk


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'document_count', 'color_preview']
    list_filter = ['parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = _('Doküman Sayısı')

    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px;">&nbsp;</span>',
            obj.color
        )
    color_preview.short_description = _('Renk')


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ['chunk_index', 'content_preview', 'token_count', 'vector_id']
    fields = ['chunk_index', 'content_preview', 'token_count', 'page_number']
    can_delete = False
    max_num = 0  # Sadece görüntüleme

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('İçerik')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'file_type_badge', 'status_badge',
        'chunk_count', 'file_size_display', 'uploaded_by', 'created_at'
    ]
    list_filter = ['status', 'file_type', 'category', 'is_public', 'created_at']
    search_fields = ['title', 'description', 'tags']
    readonly_fields = ['file_size', 'chunk_count', 'processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [DocumentChunkInline]

    fieldsets = (
        (_('Doküman Bilgileri'), {
            'fields': ('title', 'description', 'file', 'file_type')
        }),
        (_('Kategori ve Etiketler'), {
            'fields': ('category', 'tags', 'is_public')
        }),
        (_('İşleme Durumu'), {
            'fields': ('status', 'chunk_count', 'error_message'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'file_size', 'metadata', 'processed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def file_type_badge(self, obj):
        colors = {
            'pdf': '#dc3545',
            'docx': '#007bff',
            'txt': '#28a745',
            'md': '#6f42c1',
        }
        color = colors.get(obj.file_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color, obj.file_type
        )
    file_type_badge.short_description = _('Tür')

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _('Durum')

    actions = ['process_documents', 'mark_as_pending']

    @admin.action(description=_('Seçili dokümanları işle'))
    def process_documents(self, request, queryset):
        # Celery task tetikle
        count = queryset.filter(status='pending').count()
        queryset.filter(status='pending').update(status='processing')
        self.message_user(request, f'{count} doküman işleme kuyruğuna alındı.')

    @admin.action(description=_('Bekliyor olarak işaretle'))
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'content_preview', 'token_count', 'page_number']
    list_filter = ['document__category', 'document']
    search_fields = ['content', 'document__title']
    readonly_fields = ['document', 'chunk_index', 'content', 'token_count', 'vector_id', 'metadata', 'created_at']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = _('İçerik')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
