"""
IOSP - Accounts Models
Custom User model with role-based access control
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import uuid


class Department(models.Model):
    """Departman modeli - İşNet organizasyon yapısı"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Departman Adı'), max_length=100)
    code = models.CharField(_('Departman Kodu'), max_length=20, unique=True)
    description = models.TextField(_('Açıklama'), blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Üst Departman')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Departman')
        verbose_name_plural = _('Departmanlar')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserManager(BaseUserManager):
    """Custom user manager"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email adresi zorunludur'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User Model for IOSP
    Email-based authentication with roles
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Sistem Yöneticisi')
        MANAGER = 'manager', _('Yönetici')
        ANALYST = 'analyst', _('Analist')
        OPERATOR = 'operator', _('Operatör')
        VIEWER = 'viewer', _('İzleyici')

    # Remove username, use email instead
    username = None
    email = models.EmailField(_('E-posta'), unique=True)

    # Profile fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(_('Ad Soyad'), max_length=255)
    phone = models.CharField(_('Telefon'), max_length=20, blank=True)
    avatar = models.ImageField(_('Profil Fotoğrafı'), upload_to='avatars/', blank=True, null=True)

    # Role & Department
    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Departman')
    )

    # Security
    last_login_ip = models.GenericIPAddressField(_('Son Giriş IP'), null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(_('Başarısız Giriş'), default=0)
    is_locked = models.BooleanField(_('Hesap Kilitli'), default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = _('Kullanıcı')
        verbose_name_plural = _('Kullanıcılar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]

    @property
    def can_upload_documents(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER, self.Role.ANALYST]

    @property
    def can_view_analytics(self):
        return self.role != self.Role.VIEWER


class UserActivity(models.Model):
    """Kullanıcı aktivite logu"""
    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Giriş')
        LOGOUT = 'logout', _('Çıkış')
        DOCUMENT_UPLOAD = 'doc_upload', _('Doküman Yükleme')
        DOCUMENT_VIEW = 'doc_view', _('Doküman Görüntüleme')
        CHAT_QUERY = 'chat_query', _('Soru Sorma')
        SETTINGS_CHANGE = 'settings', _('Ayar Değişikliği')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(_('Aktivite Türü'), max_length=20, choices=ActivityType.choices)
    description = models.TextField(_('Açıklama'), blank=True)
    ip_address = models.GenericIPAddressField(_('IP Adresi'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    metadata = models.JSONField(_('Ek Bilgi'), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Kullanıcı Aktivitesi')
        verbose_name_plural = _('Kullanıcı Aktiviteleri')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"
