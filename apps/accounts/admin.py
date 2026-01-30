"""
IOSP - Accounts Admin
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import User, Department, UserActivity


class UserResource(resources.ModelResource):
    """User import/export resource"""
    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'role', 'department', 'is_active')
        export_order = fields


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent', 'user_count', 'created_at']
    list_filter = ['parent']
    search_fields = ['name', 'code']
    ordering = ['code']

    def user_count(self, obj):
        count = obj.users.count()
        return format_html('<span style="color: #007bff; font-weight: bold;">{}</span>', count)
    user_count.short_description = _('Kullanıcı Sayısı')


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    resource_class = UserResource

    # List view
    list_display = [
        'email', 'full_name', 'role_badge', 'department',
        'is_active', 'is_locked', 'last_login', 'created_at'
    ]
    list_filter = ['role', 'department', 'is_active', 'is_locked', 'is_staff']
    search_fields = ['email', 'full_name', 'phone']
    ordering = ['-created_at']

    # Fieldsets for add/edit
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Kişisel Bilgiler'), {'fields': ('full_name', 'phone', 'avatar')}),
        (_('Rol ve Departman'), {'fields': ('role', 'department')}),
        (_('İzinler'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Güvenlik'), {
            'fields': ('is_locked', 'failed_login_attempts', 'last_login_ip'),
            'classes': ('collapse',),
        }),
        (_('Önemli Tarihler'), {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role', 'department'),
        }),
    )

    readonly_fields = ['last_login', 'created_at', 'updated_at', 'last_login_ip']

    def role_badge(self, obj):
        colors = {
            'admin': '#dc3545',      # Red
            'manager': '#fd7e14',    # Orange
            'analyst': '#007bff',    # Blue
            'operator': '#28a745',   # Green
            'viewer': '#6c757d',     # Gray
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = _('Rol')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'ip_address', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email', 'description']
    ordering = ['-created_at']
    readonly_fields = ['user', 'activity_type', 'description', 'ip_address', 'user_agent', 'metadata', 'created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
