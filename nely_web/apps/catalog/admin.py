from django.contrib import admin
from django.utils.html import format_html
from django import forms
from apps.core.admin_mixins import RoleBasedAdminMixin
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
    
    exclude = ('description', 'category_path')
    
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
    color_preview.short_description = 'Превью'

@admin.register(Size)
class SizeAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['size_name', 'size_category', 'size_group', 'sort_order', 'is_active']
    list_filter = ['is_active', 'size_category', 'size_group']
    search_fields = ['size_name']
    ordering = ['size_category', 'sort_order']


class ProductImageForm(forms.ModelForm):
    """
    Custom form for ProductImage with Supabase file upload
    """
    class Meta:
        model = ProductImage
        fields = '__all__'
        widgets = {
            'image_url': forms.TextInput(attrs={
                'readonly': 'readonly',
                'placeholder': 'Автоматически заполнится после загрузки',
                'style': 'background-color: #f0f0f0;'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image_url readonly and not required
        if 'image_url' in self.fields:
            self.fields['image_url'].required = False


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1
    fields = [
        'image_file',      # File upload field (NEW)    
        'alt_text', 
        'is_primary', 
        'display_order', 
    ]
    readonly_fields = ['image_url']
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add help text to the formset
        return formset


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['sku', 'size', 'color', 'price', 'sale_price', 'stock_quantity', 'status']
    readonly_fields = ['sku']   # 🚀 Makes SKU non-editable


@admin.register(Product)
class ProductAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'product_name', 'product_code', 'category', 'clothing_type', 
        'base_price', 'status', 'stock_quantity','is_featured'
    ]
    list_filter = [
        'status', 'category', 'clothing_type', 'season',
        'is_featured', 'is_new_arrival', 'is_bestseller'
    ]
    search_fields = ['product_name', 'product_code', 'description']
    readonly_fields = ['product_code', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('product_name',)}
    
    fieldsets = (
        ('Базовая информация', {
            'fields': ('product_name', 'product_code', 'slug', 'description', 'short_description')
        }),
        ('Категории', {
            'fields': ('category', 'clothing_type', 'season', 'gender')
        }),
        ('Цена', {
            'fields': ('base_price', 'sale_price', 'cost_price')
        }),
        ('Отметки', {
            'fields': ('is_featured', 'is_new_arrival', 'is_bestseller', 'status')
        }),
        ('Время и даты', {
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
        
        if not request.user.is_superuser:
            if request.user.groups.filter(name='Product Managers').exists():
                readonly.append('cost_price')
            elif request.user.groups.filter(name='Content Managers').exists():
                readonly.extend(['base_price', 'sale_price', 'cost_price'])
                
        return readonly


@admin.register(ProductVariant)
class ProductVariantAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'sku', 'product', 'size', 'color', 'price', 
        'stock_quantity', 'status'
    ]
    list_editable = ['stock_quantity',]
    list_filter = ['status', 'product__category', 'size', 'color']
    search_fields = ['sku', 'product__product_name', 'barcode']
    readonly_fields = ['sku']   # 🚀 Prevents manual editing
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'size', 'color'
        )


@admin.register(Collection)
class CollectionAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['collection_name', 'is_featured', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['collection_name', 'description']
    prepopulated_fields = {'collection_slug': ('collection_name',)}


@admin.register(ProductImage)
class ProductImageAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """
    Standalone admin for managing product images with Supabase upload
    """
    form = ProductImageForm
    list_display = [
        'image_id', 'product', 'variant', 'image_type', 
        'is_primary', 'display_order', 'image_preview'
    ]
    list_filter = ['image_type', 'is_primary', 'product__category']
    search_fields = ['product__product_name', 'variant__sku', 'alt_text']
    readonly_fields = ['image_url', 'image_preview', 'created_at']
    
    fieldsets = (
        ('Загрузка фото', {
            'fields': ('image_file',),
            'description': 'Загрузите фото, и оно автоматически сохранится в Supabase'
        }),
        ('Информация о фото', {
            'fields': (
                'product', 'variant', 'image_url', 
                'alt_text', 'is_primary', 'display_order', 'image_type'
            )
        }),
        ('Превью', {
            'fields': ('image_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """
        Display image preview in admin
        """
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border: 1px solid #ddd; padding: 5px;" />',
                obj.image_url
            )
        return "Нет фото"
    
    image_preview.short_description = 'Превью фото'


@admin.register(RelatedProduct)
class RelatedProductAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['product', 'related_product', 'relation_type', 'display_order']
    list_filter = ['relation_type']
    search_fields = ['product__product_name', 'related_product__product_name']
    autocomplete_fields = ['product', 'related_product']
