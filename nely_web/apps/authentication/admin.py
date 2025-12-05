from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from apps.core.admin_mixins import RoleBasedAdminMixin  # Import from core
from .models import User, UserAddress

@admin.register(User)
class UserAdmin(RoleBasedAdminMixin, BaseUserAdmin):
    list_display = ['email', 'first_name', 'role', 'get_groups', 'is_active', 'email_verified', 'created_at']
    list_filter = ['role', 'is_active', 'email_verified', 'is_staff', 'is_superuser', 'groups']
    search_fields = ['email', 'first_name']
    ordering = ['-created_at']

    def get_groups(self, obj):
        """Display user's groups as colored badges"""
        groups = obj.groups.all()
        if not groups:
            return format_html('<span style="color: #999;">Нет групп</span>')

        badges = []
        for group in groups:
            if group.name == 'Manager':
                color = '#28a745'  # Green for managers
            else:
                color = '#007bff'  # Blue for others

            badges.append(
                f'<span style="background: {color}; color: white; padding: 3px 8px; '
                f'border-radius: 3px; font-size: 11px; margin-right: 5px;">{group.name}</span>'
            )

        return format_html(''.join(badges))

    get_groups.short_description = 'Группы'

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'phone')}),
        ('Разрешения', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'email_verified', 'groups', 'user_permissions'),
            'description': 'Для менеджера каталога: включите "Статус персонала" и добавьте в группу "Manager"'
        }),
        ('Важные даты', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'role', 'groups'),
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

    filter_horizontal = ('groups', 'user_permissions')

    def has_module_permission(self, request):
        # Only superusers and user managers can access users
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in=['User Managers', 'Customer Service']).exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(name='Customer Service').exists():
            # Customer service can only see customers, not staff
            return qs.filter(is_staff=False)
        return qs

@admin.register(UserAddress)
class UserAddressAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'address_line1', 'city', 'country', 'phone']
    list_filter = ['address_type', 'country', 'is_default']
    search_fields = ['user__email', 'city', 'address_line1']
    exclude = ('address_type', 'is_default')
