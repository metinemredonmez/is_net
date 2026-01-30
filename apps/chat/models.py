"""
IOSP - Chat Models
Sohbet geçmişi ve oturumlar
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid


class Conversation(models.Model):
    """Sohbet oturumu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name=_('Kullanıcı')
    )
    title = models.CharField(_('Başlık'), max_length=200, blank=True)
    is_active = models.BooleanField(_('Aktif'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sohbet')
        verbose_name_plural = _('Sohbetler')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Yeni Sohbet'}"

    @property
    def message_count(self):
        return self.messages.count()

    def save(self, *args, **kwargs):
        # Auto-generate title from first message
        if not self.title and self.pk:
            first_msg = self.messages.filter(role='user').first()
            if first_msg:
                self.title = first_msg.content[:50] + ('...' if len(first_msg.content) > 50 else '')
        super().save(*args, **kwargs)


class Message(models.Model):
    """Sohbet mesajı"""
    class Role(models.TextChoices):
        USER = 'user', _('Kullanıcı')
        ASSISTANT = 'assistant', _('Asistan')
        SYSTEM = 'system', _('Sistem')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Sohbet')
    )
    role = models.CharField(_('Rol'), max_length=20, choices=Role.choices)
    content = models.TextField(_('İçerik'))

    # RAG metadata
    sources = models.JSONField(_('Kaynaklar'), default=list, blank=True)
    confidence = models.FloatField(_('Güven Skoru'), null=True, blank=True)

    # Feedback
    is_helpful = models.BooleanField(_('Yararlı mı?'), null=True, blank=True)
    feedback = models.TextField(_('Geri Bildirim'), blank=True)

    # Metadata
    tokens_used = models.PositiveIntegerField(_('Token Kullanımı'), default=0)
    response_time_ms = models.PositiveIntegerField(_('Yanıt Süresi (ms)'), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mesaj')
        verbose_name_plural = _('Mesajlar')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}"
