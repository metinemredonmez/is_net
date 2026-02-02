"""
IOSP - Documents Models
Doküman yönetimi ve chunk'lama
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid
import os


def document_upload_path(instance, filename):
    """Doküman yükleme path'i: uploads/2024/01/uuid_filename"""
    from datetime import datetime
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    return os.path.join(
        'documents',
        datetime.now().strftime('%Y'),
        datetime.now().strftime('%m'),
        new_filename
    )


class DocumentCategory(models.Model):
    """Doküman kategorisi"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Kategori Adı'), max_length=100)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Açıklama'), blank=True)
    icon = models.CharField(_('İkon'), max_length=50, default='fa-folder')
    color = models.CharField(_('Renk'), max_length=20, default='#007bff')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='children',
        verbose_name=_('Üst Kategori')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Doküman Kategorisi')
        verbose_name_plural = _('Doküman Kategorileri')
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    """Ana doküman modeli"""
    class Status(models.TextChoices):
        PENDING = 'pending', _('Bekliyor')
        PROCESSING = 'processing', _('İşleniyor')
        COMPLETED = 'completed', _('Tamamlandı')
        FAILED = 'failed', _('Hata')

    class FileType(models.TextChoices):
        PDF = 'pdf', _('PDF')
        DOCX = 'docx', _('Word')
        TXT = 'txt', _('Text')
        MD = 'md', _('Markdown')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Başlık'), max_length=500)
    description = models.TextField(_('Açıklama'), blank=True)
    file = models.FileField(_('Dosya'), upload_to=document_upload_path)
    file_type = models.CharField(_('Dosya Türü'), max_length=10, choices=FileType.choices)
    file_size = models.PositiveIntegerField(_('Dosya Boyutu (bytes)'), default=0)

    # Categorization
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name=_('Kategori')
    )
    tags = models.JSONField(_('Etiketler'), default=list, blank=True)

    # Processing status
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    processing_progress = models.PositiveIntegerField(
        _('İşleme İlerlemesi'),
        default=0,
        help_text='0-100 arası ilerleme yüzdesi'
    )
    chunk_count = models.PositiveIntegerField(_('Chunk Sayısı'), default=0)
    error_message = models.TextField(_('Hata Mesajı'), blank=True)
    task_id = models.CharField(_('Celery Task ID'), max_length=255, blank=True)

    # Metadata
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name=_('Yükleyen')
    )
    is_public = models.BooleanField(_('Herkese Açık'), default=False)
    metadata = models.JSONField(_('Metadata'), default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(_('İşlenme Tarihi'), null=True, blank=True)

    class Meta:
        verbose_name = _('Doküman')
        verbose_name_plural = _('Dokümanlar')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def file_size_display(self):
        """Human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def save(self, *args, **kwargs):
        # Auto-detect file type
        if self.file and not self.file_type:
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['pdf']:
                self.file_type = self.FileType.PDF
            elif ext in ['docx', 'doc']:
                self.file_type = self.FileType.DOCX
            elif ext in ['txt']:
                self.file_type = self.FileType.TXT
            elif ext in ['md', 'markdown']:
                self.file_type = self.FileType.MD

        # Set file size
        if self.file:
            self.file_size = self.file.size

        super().save(*args, **kwargs)


class DocumentChunk(models.Model):
    """
    Doküman parçaları (RAG için)
    Her doküman küçük parçalara bölünür ve embed edilir
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name=_('Doküman')
    )
    chunk_index = models.PositiveIntegerField(_('Sıra'))
    content = models.TextField(_('İçerik'))
    token_count = models.PositiveIntegerField(_('Token Sayısı'), default=0)

    # Vector store reference
    vector_id = models.CharField(_('Vector ID'), max_length=100, blank=True)

    # Page/section info
    page_number = models.PositiveIntegerField(_('Sayfa No'), null=True, blank=True)
    section = models.CharField(_('Bölüm'), max_length=200, blank=True)

    # Metadata
    metadata = models.JSONField(_('Metadata'), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Doküman Parçası')
        verbose_name_plural = _('Doküman Parçaları')
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"
