"""
IOSP - Custom Permissions
Role-based access control (RBAC) permissions
"""
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Sadece nesne sahibi veya admin erişebilir.
    Object-level permission.
    """
    message = "Bu işlem için yetkiniz bulunmuyor."

    def has_object_permission(self, request, view, obj):
        # Admin her şeye erişebilir
        if request.user.is_staff or request.user.role == 'admin':
            return True

        # Sahibi kontrol et (uploaded_by, user, owner gibi fieldlar)
        if hasattr(obj, 'uploaded_by'):
            return obj.uploaded_by == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        return False


class IsOwnerOrAdminOrPublic(permissions.BasePermission):
    """
    Nesne sahibi, admin veya public ise erişebilir.
    Dokümanlar için kullanılır.
    """
    message = "Bu dokümana erişim yetkiniz bulunmuyor."

    def has_object_permission(self, request, view, obj):
        # Admin her şeye erişebilir
        if request.user.is_staff or request.user.role == 'admin':
            return True

        # Manager da erişebilir
        if hasattr(request.user, 'role') and request.user.role == 'manager':
            return True

        # Public dokümanlar herkese açık
        if hasattr(obj, 'is_public') and obj.is_public:
            return True

        # Sahibi kontrol et
        if hasattr(obj, 'uploaded_by'):
            return obj.uploaded_by == request.user

        return False


class CanUploadDocuments(permissions.BasePermission):
    """
    Sadece doküman yükleme yetkisi olan roller.
    Admin, Manager, Analyst yükleyebilir.
    """
    message = "Doküman yükleme yetkiniz bulunmuyor."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Sadece POST (create) için kontrol et
        if request.method != 'POST':
            return True

        # Model'deki can_upload_documents property'sini kullan
        if hasattr(request.user, 'can_upload_documents'):
            return request.user.can_upload_documents

        # Varsayılan: viewer hariç herkes
        allowed_roles = ['admin', 'manager', 'analyst', 'operator']
        return request.user.role in allowed_roles


class IsAdminOrManager(permissions.BasePermission):
    """
    Sadece Admin veya Manager rolü.
    """
    message = "Bu işlem için admin veya yönetici yetkisi gerekiyor."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return (
            request.user.is_staff or
            request.user.role in ['admin', 'manager']
        )


class ReadOnly(permissions.BasePermission):
    """
    Sadece okuma işlemleri (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
