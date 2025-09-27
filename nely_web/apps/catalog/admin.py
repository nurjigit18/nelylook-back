from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_mixins import RoleBasedAdminMixin  # Import from core
from .models import (
    Category, ClothingType, Product, ProductVariant, 
    Collection, Color, Size, ProductImage, RelatedProduct
)

@admin.register(Category)
class CategoryAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['category_name', 'parent_category', 'is_active', 'display_order']
    list_filter = ['is_active', 'parent_category']
    search_fields = ['category_name', 'description']
    ordering = ['display_order', 'category_name']
    
    exclude = ('description',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.select_related('parent_category')

@admin.register(ClothingType)
class ClothingTypeAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['type_name', 'category', 'is_active', 'display_order']
    list_filter = ['is_active', 'category']
    search_fields = ['type_name']
    ordering = ['category__category_name', 'display_order']

@admin.register(Color)
class ColorAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['color_name', 'color_code', 'color_family', 'color_preview', 'is_active']
    list_filter = ['is_active', 'color_family']
    search_fields = ['color_name', 'color_code']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
                obj.color_code
            )
        return '-'
    color_preview.short_description = 'Preview'

@admin.register(Size)
class SizeAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['size_name', 'size_category', 'size_group', 'sort_order', 'is_active']
    list_filter = ['is_active', 'size_category', 'size_group']
    search_fields = ['size_name']
    ordering = ['size_category', 'sort_order']

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image_url', 'alt_text', 'is_primary', 'display_order', 'image_type']

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['sku', 'size', 'color', 'price', 'sale_price', 'stock_quantity', 'status']

@admin.register(Product)
class ProductAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'product_name', 'product_code', 'category', 'clothing_type', 
        'base_price', 'status', 'is_featured', 'created_at'
    ]
    list_filter = [
        'status', 'category', 'clothing_type', 'season', 'gender',
        'is_featured', 'is_new_arrival', 'is_bestseller'
    ]
    search_fields = ['product_name', 'product_code', 'description']
    readonly_fields = ['product_code', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'product_code', 'slug', 'description', 'short_description')
        }),
        ('Categorization', {
            'fields': ('category', 'clothing_type', 'season', 'gender')
        }),
        ('Pricing', {
            'fields': ('base_price', 'sale_price', 'cost_price')
        }),
        ('Flags', {
            'fields': ('is_featured', 'is_new_arrival', 'is_bestseller', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductVariantInline, ProductImageInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'clothing_type'
        )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        
        # If user is not superuser, make certain fields readonly
        if not request.user.is_superuser:
            if request.user.groups.filter(name='Product Managers').exists():
                # Product managers can't edit cost_price
                readonly.append('cost_price')
            elif request.user.groups.filter(name='Content Managers').exists():
                # Content managers can only edit content, not pricing
                readonly.extend(['base_price', 'sale_price', 'cost_price'])
                
        return readonly

@admin.register(ProductVariant)
class ProductVariantAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'sku', 'product', 'size', 'color', 'price', 
        'stock_quantity', 'status'
    ]
    list_filter = ['status', 'product__category', 'size', 'color']
    search_fields = ['sku', 'product__product_name', 'barcode']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'size', 'color'
        )

@admin.register(Collection)
class CollectionAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['collection_name', 'is_featured', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['collection_name', 'description']

@admin.register(ProductImage)
class ProductImageAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['product', 'variant', 'image_type', 'is_primary', 'display_order']
    list_filter = ['image_type', 'is_primary', 'product__category']
    search_fields = ['product__product_name', 'alt_text']