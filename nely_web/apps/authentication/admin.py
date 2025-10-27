from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.core.admin_mixins import RoleBasedAdminMixin  # Import from core
from .models import User, UserAddress

@admin.register(User)
class UserAdmin(RoleBasedAdminMixin, BaseUserAdmin):
    list_display = ['email', 'first_name', 'role', 'is_active', 'email_verified', 'created_at']
    list_filter = ['role', 'is_active', 'email_verified', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email',)}),
        ('Personal info', {'fields': ('first_name', 'phone')}),
        ('Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'email_verified'),
        }),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'role'),
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    exclude = ('password', 'group')
    
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
