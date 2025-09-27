from django.contrib import admin
from apps.core.admin_mixins import RoleBasedAdminMixin  # Import from core
from .models import Order, OrderItems, DeliveryZones

class OrderItemsInline(admin.TabularInline):
    model = OrderItems
    extra = 0
    readonly_fields = ['product_name', 'variant_details', 'total_price']

@admin.register(Order)
class OrderAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'guest_email', 'order_status', 
        'payment_status', 'total_amount_base', 'order_date'
    ]
    list_filter = [
        'order_status', 'payment_status', 'payment_method', 
        'currency', 'order_date'
    ]
    search_fields = ['order_number', 'user__email', 'guest_email', 'tracking_number']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 
        'subtotal_base', 'total_amount_base'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'guest_email', 'order_date')
        }),
        ('Status', {
            'fields': ('order_status', 'payment_status', 'payment_method')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address')
        }),
        ('Delivery', {
            'fields': ('delivery_date', 'tracking_number')
        }),
        ('Financial', {
            'fields': ('currency', 'subtotal_base', 'shipping_cost_base', 'discount_base', 'total_amount_base')
        }),
        ('Admin', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderItemsInline]
    
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        # Allow order managers and customer service
        return request.user.groups.filter(
            name__in=['Order Managers', 'Customer Service', 'Fulfillment']
        ).exists()
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ['order_number', 'created_at', 'updated_at']
        
        if request.user.groups.filter(name='Customer Service').exists():
            # Customer service can only update status and notes
            readonly.extend([
                'user', 'guest_email', 'payment_method', 
                'subtotal_base', 'total_amount_base', 'currency'
            ])
        elif request.user.groups.filter(name='Fulfillment').exists():
            # Fulfillment can only update shipping info
            readonly.extend([
                'user', 'guest_email', 'payment_status', 'payment_method',
                'subtotal_base', 'total_amount_base', 'discount_base'
            ])
            
        return readonly

@admin.register(DeliveryZones)
class DeliveryZonesAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['zone_name', 'delivery_cost', 'delivery_time_days', 'is_active']
    list_filter = ['is_active']
    search_fields = ['zone_name', 'cities']