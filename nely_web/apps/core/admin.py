from django.contrib import admin
from apps.core.admin_mixins import RoleBasedAdminMixin
from .models import Currency

@admin.register(Currency)
class CurrencyAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['currency_code', 'currency_name', 'currency_symbol', 'exchange_rate', 'is_base_currency', 'is_active']
    list_filter = ['is_active', 'is_base_currency']
    search_fields = ['currency_code', 'currency_name']
    
    def has_module_permission(self, request):
        # Only superusers can manage currencies
        return request.user.is_superuser