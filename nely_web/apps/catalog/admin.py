# apps/catalog/admin.py - IMPROVED VERSION
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
import json
from apps.core.admin_mixins import RoleBasedAdminMixin
from .models import (
    Category, ClothingType, Product, ProductVariant,
    Collection, CollectionProduct, Color, Size, ProductImage, RelatedProduct
)


# ============================================================================
# CUSTOM FORMS
# ============================================================================

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
        
        # If we're editing an existing product with variants, filter colors
        if 'color' in self.fields and hasattr(self, 'parent_obj') and self.parent_obj:
            # Get colors that have variants for this product
            available_colors = Color.objects.filter(
                variants__product=self.parent_obj
            ).distinct()
            
            if available_colors.exists():
                self.fields['color'].queryset = available_colors
                self.fields['color'].help_text = (
                    'Только цвета с вариациями. '
                    'Сначала создайте вариацию (SKU) с нужным цветом.'
                )
            else:
                self.fields['color'].help_text = (
                    '⚠️ Сначала добавьте вариации с цветами ниже!'
                )


class ProductVariantForm(forms.ModelForm):
    """
    Custom form for ProductVariant to show helpful messages
    """
    class Meta:
        model = ProductVariant
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        if 'color' in self.fields:
            self.fields['color'].help_text = (
                'Выберите цвет для этой вариации. '
                'Этот цвет будет доступен для фото выше.'
            )
        
        if 'size' in self.fields:
            self.fields['size'].help_text = 'Выберите размер для этой вариации.'


# ============================================================================
# INLINE ADMINS
# ============================================================================

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    form = ProductVariantForm
    extra = 1
    fields = ['color', 'size', 'stock_quantity', 'status', 'sku']
    readonly_fields = ['sku']
    
    # Order by color first for better organization
    ordering = ['color', 'size']
    
    def get_formset(self, request, obj=None, **kwargs):
        """
        Add custom CSS to highlight the importance of adding variants first
        """
        formset = super().get_formset(request, obj, **kwargs)
        return formset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 0  # Don't show empty forms by default
    fields = ['color', 'image_file', 'alt_text', 'is_primary', 'display_order', 'image_preview']
    readonly_fields = ['image_preview']

    # Order by color for consistency with variants
    ordering = ['color', 'display_order']

    def get_formset(self, request, obj=None, **kwargs):
        """
        Pass the parent object to the form so it can filter colors
        """
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.parent_obj = obj
        return formset

    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image_url
            )
        return "Нет фото"
    image_preview.short_description = 'Превью'


class CollectionProductInline(admin.TabularInline):
    """Inline for adding products to a collection"""
    model = CollectionProduct
    extra = 1
    fields = ['product', 'display_order']
    autocomplete_fields = ['product']
    ordering = ['display_order']
    verbose_name = "Товар в коллекции"
    verbose_name_plural = "Товары в коллекции"


# ============================================================================
# MAIN ADMIN CLASSES
# ============================================================================

@admin.register(Category)
class CategoryAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['category_name', 'category_slug', 'parent_category', 'is_active', 'display_order']
    list_filter = ['is_active', 'parent_category']
    search_fields = ['category_name', 'category_slug','description']
    ordering = ['display_order', 'category_name']
    prepopulated_fields = {'category_slug': ('category_name',)}  # Auto-generate slug in admin

    exclude = ('is_active','description', 'category_path')
    
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


@admin.register(Product)
class ProductAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'product_name', 'product_code', 'category', 'clothing_type', 
        'base_price', 'status', 'stock_quantity', 'is_featured', 'is_new_arrival',
        'color_count', 'image_count'
    ]
    list_filter = [
        'status', 'category', 'clothing_type', 'season',
        'is_featured', 'is_new_arrival', 'is_bestseller'
    ]
    search_fields = ['product_name', 'product_code', 'description']
    readonly_fields = ['product_code', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('product_name',)}
    
    fieldsets = (
        ('📋 Базовая информация', {
            'fields': ('product_name', 'product_code', 'slug', 'description', 'short_description')
        }),
        ('📁 Категории', {
            'fields': ('category', 'clothing_type', 'season')
        }),
        ('💰 Цена', {
            'fields': ('base_price', 'sale_price', 'cost_price')
        }),
        ('⭐ Отметки', {
            'fields': ('is_featured', 'is_new_arrival', 'is_bestseller', 'status')
        }),
    )
    
    # IMPORTANT: Variants first, then images
    inlines = [ProductVariantInline, ProductImageInline]
    
    class Media:
        css = {
            'all': ('admin/css/product_admin_custom.css',)
        }
        js = ('admin/js/product_admin_custom.js',)
    
    def get_inline_instances(self, request, obj=None):
        """
        Show helpful message if creating new product
        """
        inline_instances = super().get_inline_instances(request, obj)
        
        # If creating new product, only show variant inline
        if obj is None:
            return [i for i in inline_instances if isinstance(i, ProductVariantInline)]
        
        return inline_instances
    
    def color_count(self, obj):
        count = obj.variants.values('color').distinct().count()
        return f"{count} цветов"
    color_count.short_description = 'Цвета'
    
    def image_count(self, obj):
        count = obj.images.count()
        if count > 0:
            return format_html('✓ {} фото', count)
        return format_html('<span style="color: orange;">Нет фото</span>')
    image_count.short_description = 'Фото'
    
    def save_model(self, request, obj, form, change):
        """
        Add helpful message after saving
        """
        super().save_model(request, obj, form, change)
        
        if not change:  # New product
            self.message_user(
                request,
                '✅ Товар создан! Теперь добавьте вариации (цвет + размер) ниже.',
                level='SUCCESS'
            )
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Add help text for new products
        """
        form = super().get_form(request, obj, **kwargs)
        
        if obj is None:
            # New product
            form.base_fields['product_name'].help_text = (
                '⚠️ ИНСТРУКЦИЯ: '
                '1) Сначала заполните основную информацию и нажмите "Сохранить". '
                '2) Потом добавьте вариации (цвет + размер). '
                '3) Только после этого загружайте фото для каждого цвета.'
            )
        
        return form


@admin.register(ProductVariant)
class ProductVariantAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'sku', 'product', 'size', 'color', 
        'stock_quantity', 'status'
    ]
    list_editable = ['stock_quantity']
    list_filter = ['status', 'product__category', 'size', 'color']
    search_fields = ['sku', 'product__product_name', 'barcode']
    readonly_fields = ['sku']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'size', 'color'
        )


@admin.register(Collection)
class CollectionAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['collection_name', 'collection_slug', 'product_count', 'is_featured', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['collection_name', 'collection_slug', 'description']
    prepopulated_fields = {'collection_slug': ('collection_name',)}
    inlines = [CollectionProductInline]

    fieldsets = (
        ('📋 Основная информация', {
            'fields': ('collection_name', 'collection_slug', 'description')
        }),
        ('🖼️ Баннер', {
            'fields': ('banner_image',),
            'description': 'URL изображения баннера для страницы коллекции'
        }),
        ('⚙️ Настройки', {
            'fields': ('is_featured', 'is_active', 'display_order')
        }),
    )

    def product_count(self, obj):
        count = obj.collection_products.count()
        if count > 0:
            return format_html('<span style="color: green;">{} товаров</span>', count)
        return format_html('<span style="color: orange;">Нет товаров</span>')
    product_count.short_description = 'Товары'


@admin.register(ProductImage)
class ProductImageAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    """
    Standalone admin for managing product images with Supabase upload
    """
    form = ProductImageForm
    list_display = [
        'image_id', 'product', 'color', 'image_type', 
        'is_primary', 'display_order', 'image_preview'
    ]
    list_filter = ['image_type', 'is_primary', 'product__category', 'color']
    search_fields = ['product__product_name', 'alt_text']
    readonly_fields = ['image_url', 'image_preview', 'created_at']
    
    fieldsets = (
        ('🎨 Выбор цвета', {
            'fields': ('product', 'color'),
            'description': '⚠️ Сначала убедитесь что для товара есть вариация с этим цветом!'
        }),
        ('📸 Загрузка фото', {
            'fields': ('image_file',),
            'description': 'Загрузите фото, и оно автоматически сохранится в Supabase'
        }),
        ('ℹ️ Информация о фото', {
            'fields': (
                'image_url', 
                'alt_text', 'is_primary', 'display_order', 'image_type'
            )
        }),
        ('👁️ Превью', {
            'fields': ('image_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Filter colors based on selected product
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Get product from query params or object
        product_id = request.GET.get('product')
        if obj:
            product_id = obj.product_id
        
        if product_id:
            # Filter colors to only those with variants for this product
            available_colors = Color.objects.filter(
                variants__product_id=product_id
            ).distinct()
            
            form.base_fields['color'].queryset = available_colors
            
            if not available_colors.exists():
                form.base_fields['color'].help_text = (
                    '⚠️ У этого товара нет вариаций с цветами! '
                    'Сначала добавьте вариации.'
                )
        
        return form
    
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
    
    def save_model(self, request, obj, form, change):
        """
        Validate that the color has a variant before saving
        """
        super().save_model(request, obj, form, change)
        
        # Check if variant exists
        if obj.color and obj.product:
            variant_exists = ProductVariant.objects.filter(
                product=obj.product,
                color=obj.color
            ).exists()
            
            if not variant_exists:
                self.message_user(
                    request,
                    f'⚠️ Внимание: Нет вариации для товара "{obj.product}" с цветом "{obj.color}". '
                    'Рекомендуется создать вариацию.',
                    level='WARNING'
                )


@admin.register(RelatedProduct)
class RelatedProductAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['product', 'related_product', 'relation_type', 'display_order']
    list_filter = ['relation_type']
    search_fields = ['product__product_name', 'related_product__product_name']
    autocomplete_fields = ['product', 'related_product']


# ============================================================================
# CUSTOM ADMIN VIEWS - Easy Product Creator
# ============================================================================

@staff_member_required
def easy_product_creator(request):
    """
    Custom admin view for easy product creation with color-first workflow
    """
    if request.method == 'GET':
        # Fetch data for the form
        categories = Category.objects.filter(is_active=True).order_by('category_name')
        clothing_types = ClothingType.objects.filter(is_active=True).order_by('type_name')
        colors = Color.objects.filter(is_active=True).order_by('color_name')
        sizes = Size.objects.filter(is_active=True).order_by('sort_order')

        # Serialize colors and sizes for JavaScript
        colors_json = json.dumps([{
            'color_id': c.color_id,
            'color_name': c.color_name,
            'color_code': c.color_code
        } for c in colors])

        sizes_json = json.dumps([{
            'size_id': s.size_id,
            'size_name': s.size_name
        } for s in sizes])

        context = {
            'title': 'Легкое добавление товара',
            'categories': categories,
            'clothing_types': clothing_types,
            'colors': colors,
            'colors_json': colors_json,
            'sizes': sizes,
            'sizes_json': sizes_json,
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'has_permission': True,
        }

        return render(request, 'admin/catalog/easy_product_creator.html', context)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@staff_member_required
@require_http_methods(["POST"])
def upload_product_image(request):
    """
    Upload image to Supabase and return URL
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)

        uploaded_file = request.FILES['file']

        # Use Supabase storage
        from apps.core.storage import SupabaseStorage
        storage = SupabaseStorage()

        # Generate unique filename
        import uuid
        from pathlib import Path
        ext = Path(uploaded_file.name).suffix
        filename = f"products/{uuid.uuid4().hex}{ext}"

        # Save to Supabase
        saved_path = storage.save(filename, uploaded_file)
        image_url = storage.url(saved_path)

        return JsonResponse({
            'success': True,
            'url': image_url,
            'filename': saved_path
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
def create_product_easy(request):
    """
    API endpoint to handle product creation from Easy Product Creator
    """
    try:
        data = json.loads(request.body)

        with transaction.atomic():
            # Generate slug from product name
            from django.utils.text import slugify
            from unidecode import unidecode

            base_slug = slugify(unidecode(data['product_name']))
            slug = base_slug

            # Ensure unique slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Create Product
            product = Product.objects.create(
                product_name=data['product_name'],
                slug=slug,
                category_id=data['category_id'],
                clothing_type_id=data.get('clothing_type_id'),
                description=data.get('description', ''),
                short_description=data.get('short_description', ''),
                base_price=data['base_price'],
                sale_price=data.get('sale_price'),
                season=data.get('season', ''),
                is_featured=data.get('is_featured', False),
                is_new_arrival=data.get('is_new_arrival', False),
                is_bestseller=data.get('is_bestseller', False),
                status='active'
            )

            # Create ProductVariants
            variants_data = data.get('variants', [])
            for variant_data in variants_data:
                color_id = variant_data['color_id']
                for size_data in variant_data['sizes']:
                    ProductVariant.objects.create(
                        product=product,
                        color_id=color_id,
                        size_id=size_data['size_id'],
                        stock_quantity=size_data['stock_quantity'],
                        status='active' if size_data['stock_quantity'] > 0 else 'oos'
                    )

            # Create ProductImages
            images_data = data.get('images', [])
            for image_data in images_data:
                ProductImage.objects.create(
                    product=product,
                    color_id=image_data['color_id'],
                    image_url=image_data['image_url'],
                    alt_text=image_data.get('alt_text', product.product_name),
                    is_primary=image_data.get('is_primary', False),
                    display_order=image_data.get('display_order', 1),
                    image_type='product'
                )

        return JsonResponse({
            'success': True,
            'message': f'Товар "{product.product_name}" успешно создан!',
            'product_id': product.product_id,
            'redirect_url': f'/admin/catalog/product/{product.product_id}/change/'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# Customize ProductAdmin to add custom URL
class CustomProductAdmin(ProductAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('easy-creator/', easy_product_creator, name='catalog_product_easy_creator'),
            path('easy-creator/upload/', upload_product_image, name='catalog_product_image_upload'),
            path('easy-creator/create/', create_product_easy, name='catalog_product_easy_create'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Add button to access Easy Product Creator"""
        extra_context = extra_context or {}
        extra_context['show_easy_creator_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


# Re-register Product with custom admin
admin.site.unregister(Product)
admin.site.register(Product, CustomProductAdmin)