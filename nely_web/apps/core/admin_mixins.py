from django.contrib import admin

class RoleBasedAdminMixin:
    """Mixin to add role-based access control to admin classes"""

    # Define which models managers can access
    MANAGER_ALLOWED_MODELS = [
        'product',           # Товары
        'productvariant',    # Вариации товаров
        'category',          # Категории
        'collection',        # Коллекции
        'color',             # Цвета
    ]

    def is_manager(self, user):
        """Check if user is a manager (not superuser, but in 'Manager' group)"""
        if user.is_superuser:
            return False
        return user.groups.filter(name='Manager').exists()

    def has_module_permission(self, request):
        """Control who can see this module in admin index"""
        if request.user.is_superuser:
            return True

        # If user is a manager, only show allowed models
        if self.is_manager(request.user):
            opts = self.model._meta
            model_name = opts.model_name.lower()
            return model_name in self.MANAGER_ALLOWED_MODELS

        # Check if user has specific permissions for this model
        opts = self.model._meta
        codename = f'view_{opts.model_name}'
        return request.user.has_perm(f'{opts.app_label}.{codename}')
    
    def has_view_permission(self, request, obj=None):
        """Control view access"""
        if request.user.is_superuser:
            return True
        return super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        """Control add access"""
        if request.user.is_superuser:
            return True
        return super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Control edit access"""
        if request.user.is_superuser:
            return True
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Control delete access"""
        if request.user.is_superuser:
            return True
        return super().has_delete_permission(request, obj)