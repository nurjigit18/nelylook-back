from django.contrib import admin

class RoleBasedAdminMixin:
    """Mixin to add role-based access control to admin classes"""
    
    def has_module_permission(self, request):
        """Control who can see this module in admin index"""
        if request.user.is_superuser:
            return True
            
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