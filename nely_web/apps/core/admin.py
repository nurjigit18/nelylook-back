from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from apps.core.admin_mixins import RoleBasedAdminMixin
from .models import Currency


# ============================================================================
# GROUP ADMIN CUSTOMIZATION
# ============================================================================
# Note: User admin is customized in apps.authentication.admin
# This file only handles Group admin to avoid conflicts


class CustomGroupAdmin(BaseGroupAdmin):
    """
    Custom Group admin showing group members
    """
    list_display = ['name', 'get_members_count', 'get_permissions_count']

    def get_members_count(self, obj):
        """Show count of users in this group"""
        count = obj.user_set.count()
        if count == 0:
            return format_html('<span style="color: #999;">0 пользователей</span>')
        return format_html(
            '<span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{} {}</span>',
            count,
            'пользователь' if count == 1 else 'пользователя' if count < 5 else 'пользователей'
        )

    get_members_count.short_description = 'Участников'

    def get_permissions_count(self, obj):
        """Show count of permissions in this group"""
        count = obj.permissions.count()
        return format_html(
            '<span style="color: #666;">{} разрешений</span>',
            count
        )

    get_permissions_count.short_description = 'Разрешений'

    # Add custom fieldset to show group members
    fieldsets = (
        (None, {'fields': ('name', 'permissions')}),
    )

    readonly_fields = ['get_group_members']

    def get_group_members(self, obj):
        """Display list of users in this group"""
        users = obj.user_set.all()

        if not users:
            return format_html('<p style="color: #999;">В этой группе пока нет пользователей</p>')

        user_list = []
        for user in users:
            status = []
            if user.is_superuser:
                status.append('<span style="color: #dc3545;">★ Суперпользователь</span>')
            if user.is_staff:
                status.append('<span style="color: #28a745;">✓ Персонал</span>')
            if not user.is_active:
                status.append('<span style="color: #999;">⊗ Неактивен</span>')

            status_str = ' '.join(status) if status else '<span style="color: #666;">Обычный пользователь</span>'

            user_list.append(
                f'<li style="margin: 8px 0; padding: 8px; background: #f8f8f8; border-left: 3px solid #007bff;">'
                f'<strong>{user.username}</strong> ({user.email or "без email"}) - {status_str}'
                f'</li>'
            )

        return format_html(
            '<div style="margin-top: 10px;">'
            '<h3 style="margin-bottom: 10px;">Пользователи в группе "{}" ({})</h3>'
            '<ul style="list-style: none; padding: 0; margin: 0;">{}</ul>'
            '</div>',
            obj.name,
            users.count(),
            ''.join(user_list)
        )

    get_group_members.short_description = 'Участники группы'

    def get_fieldsets(self, request, obj=None):
        """Add members section when viewing existing group"""
        fieldsets = list(self.fieldsets)
        if obj:  # Only show members for existing groups
            fieldsets.append(
                ('Участники группы', {
                    'fields': ('get_group_members',),
                    'description': 'Список всех пользователей в этой группе'
                })
            )
        return fieldsets


# Unregister the default Group admin (if already registered)
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

# Register our customized Group admin
admin.site.register(Group, CustomGroupAdmin)


# ============================================================================
# CURRENCY ADMIN
# ============================================================================

@admin.register(Currency)
class CurrencyAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['currency_code', 'currency_name', 'currency_symbol', 'exchange_rate', 'is_base_currency', 'is_active']
    list_filter = ['is_active', 'is_base_currency']
    search_fields = ['currency_code', 'currency_name']

    def has_module_permission(self, request):
        # Only superusers can manage currencies
        return request.user.is_superuser