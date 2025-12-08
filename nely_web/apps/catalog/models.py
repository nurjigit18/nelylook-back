# apps/catalog/models.py - FIXED VERSION
from django.db import models
from apps.core.storage import SupabaseStorage
from django.utils.text import slugify
import uuid

class Season(models.TextChoices):
    SPRING = "spring", "Весная"
    SUMMER = "summer", "Лето"
    AUTUMN = "autumn", "Осень"
    WINTER = "winter", "Зима"
    ALL    = "all",    "Всесезон"

class Status(models.TextChoices):
    DRAFT     = "draft", "Черновик"
    ACTIVE    = "active","В наличии"
    ARCHIVED  = "archived","Архивирован"
    OUT_OF_STOCK= "oos",   "Нет в наличии"
    
class ImageFile(models.TextChoices):
    PNG = "png", "png"
    JPG = "jpg", "jpg"
    JPEG = "jpeg", "jpeg"

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_slug = models.SlugField(unique=True, max_length=100, blank=True, verbose_name="URL-идентификатор")
    category_name = models.CharField(max_length=100, unique=True, verbose_name="Категории")
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        blank=True, null=True,
        verbose_name='Главная категория'
    )    
    category_path = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    display_order = models.IntegerField(blank=True, null=True, verbose_name="Приоритет")
    is_active = models.BooleanField(default=True, verbose_name="В наличии")

    def save(self, *args, **kwargs):
        if not self.category_slug and self.category_name:
            base_slug = slugify(self.category_name, allow_unicode=True)
            self.category_slug = base_slug
        super().save(*args, **kwargs)
        
    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        
    def __str__(self): 
        return self.category_name

class ClothingType(models.Model):
    type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(unique=True, max_length=50, verbose_name="Тип одежды")
    category = models.ForeignKey(
        Category,  # Direct reference, not string
        on_delete=models.CASCADE,
        related_name='clothing_types',
        verbose_name='Категория'
        # Remove null constraint for now to avoid migration issues
    )    
    display_order = models.IntegerField(blank=True, null=True, verbose_name="Приоритет")
    is_active = models.BooleanField(default=True, verbose_name="В наличии")

    class Meta:
        db_table = 'clothing_types'
        verbose_name_plural = 'Тип одежды'
    
    def __str__(self): 
        return f"{self.category.category_name} · {self.type_name}"

class Color(models.Model):
    color_id = models.AutoField(primary_key=True)
    color_name = models.CharField(max_length=50, unique=True, verbose_name="Цвет")
    color_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Код цвета")
    color_family = models.CharField(max_length=30, blank=True, null=True, verbose_name="Категория цвета")
    is_active = models.BooleanField(default=True, verbose_name="В наличии")

    class Meta:
        db_table = 'colors'
        verbose_name_plural = 'Цвета'
    
    def __str__(self):
        return self.color_name

class Size(models.Model):
    size_id = models.AutoField(primary_key=True)
    size_name = models.CharField(max_length=20, unique=True, verbose_name="Размер")
    size_code = models.CharField(max_length=5, blank=True, null=True, verbose_name="Буквенный код (S, M, L, XL)")
    size_category = models.CharField(max_length=20, blank=True, null=True, verbose_name="Категория")
    size_group = models.CharField(max_length=20, blank=True, null=True, verbose_name="Классификация")
    sort_order = models.IntegerField(blank=True, null=True, verbose_name="Приоритет")
    measurements = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="В наличии")

    class Meta:
        db_table = 'sizes'
        verbose_name_plural = 'Размеры'
        ordering = ['sort_order', 'size_name']

    def __str__(self):
        return self.size_name

class Collection(models.Model):
    collection_id = models.AutoField(primary_key=True)
    collection_name = models.CharField(max_length=100, verbose_name="Коллекция")
    collection_slug = models.CharField(unique=True, max_length=255, verbose_name='URL-идентификатор')
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    banner_image = models.ImageField(upload_to='collections/banners/', blank=True, null=True, verbose_name="Баннер коллекции")
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    display_order = models.IntegerField(blank=True, null=True, verbose_name="Приоритет")
    is_active = models.BooleanField(default=True, verbose_name="В наличии")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = 'collections'
        verbose_name_plural = 'Коллекции'

    def __str__(self):
        return self.collection_name

    def save(self, *args, **kwargs):
        # Optimize banner image if it's a new upload (strip EXIF data for faster processing)
        if self.banner_image and hasattr(self.banner_image, 'file'):
            try:
                from PIL import Image
                from io import BytesIO
                from django.core.files.uploadedfile import InMemoryUploadedFile
                import sys

                # Open the image
                img = Image.open(self.banner_image)

                # Only process JPEG images to strip EXIF data
                if img.format == 'JPEG':
                    # Create output buffer
                    output = BytesIO()

                    # Save without EXIF data (data=None removes EXIF)
                    img.save(
                        output,
                        format='JPEG',
                        quality=90,  # High quality, no reprocessing
                        optimize=False,  # Skip optimization for speed
                        exif=b''  # Remove EXIF data
                    )
                    output.seek(0)

                    # Replace the file with EXIF-free version
                    self.banner_image = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        self.banner_image.name,
                        'image/jpeg',
                        sys.getsizeof(output),
                        None
                    )
            except Exception:
                # If optimization fails, just use original
                pass

        super().save(*args, **kwargs)

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255, verbose_name="Название модели")
    product_code = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Код модели")
    slug = models.SlugField(unique=True, max_length=255, verbose_name='URL-идентификатор')
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    short_description = models.TextField(blank=True, null=True, verbose_name="Краткое описание")
    
    # Fixed foreign key references
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products',
        verbose_name='Категория'
    )
    clothing_type = models.ForeignKey(
        ClothingType, 
        on_delete=models.PROTECT, 
        related_name='products',
        verbose_name='Тип одежды',
        null=True,
        blank=True
    )
    
    season = models.CharField(max_length=10, choices=Season.choices, default=Season.ALL, verbose_name="Сезон")
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая цена")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Цена по скидке")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Расходная цена")
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    is_new_arrival = models.BooleanField(default=False, verbose_name="Новое")
    is_bestseller = models.BooleanField(default=False, verbose_name="Популярное")
    stock_quantity = models.IntegerField(default=0, verbose_name="В наличии")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = 'products'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        Model = type(self)  # this is your Product model

        # 1) generate slug
        if not self.slug and self.product_name:
            from django.utils.text import slugify
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1

            while Model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        # 2) generate product_code like NL-00000
        if not self.product_code:
            prefix = "NL-"
            last_code_obj = Model.objects.filter(
                product_code__startswith=prefix
            ).order_by("-product_code").first()

            if last_code_obj and last_code_obj.product_code:
                last_num_str = last_code_obj.product_code.replace(prefix, "")
                try:
                    last_num = int(last_num_str)
                except ValueError:
                    last_num = 0
            else:
                last_num = 0

            new_num = last_num + 1
            self.product_code = f"{prefix}{new_num:05d}"

        super().save(*args, **kwargs)



    def __str__(self):
        return self.product_name

class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Модель'
    )   
    sku = models.CharField(unique=True, max_length=100, blank=True, verbose_name="Баркод")
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        blank=True, null=True,
        related_name='variants',
        verbose_name='Размер'
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        blank=True, null=True,
        related_name='variants',
        verbose_name='Цвет'
    )
    stock_quantity = models.IntegerField(default=0, verbose_name="В наличии")
    low_stock_threshold = models.IntegerField(default=10, verbose_name="Мин. в наличии")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = 'product_variants'
        verbose_name_plural = 'Вариации товаров'
        unique_together = [['product', 'size', 'color']]
        ordering = ['product', 'color', 'size']
    
    def save(self, *args, **kwargs):
        # Check if this is a new instance
        is_new = self.pk is None
        
        # Save first to get the primary key
        super().save(*args, **kwargs)
        
        # Generate SKU only for new instances without a SKU
        if is_new and not self.sku:
            # Use variant_id instead of id since that's your primary key
            self.sku = f"25{self.variant_id:06d}"  # e.g., 25000001, 25000002
            super().save(update_fields=['sku'])

    def __str__(self):
        parts = [str(self.product)]
        if self.size:
            parts.append(str(self.size))
        if self.color:
            parts.append(str(self.color))
        return ' - '.join(parts)


# apps/catalog/models.py

class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        verbose_name='Модель'
    )
    
    color = models.ForeignKey(
        'Color',
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name='product_images',
        verbose_name='Цвет'
    )
    
    # File upload field
    image_file = models.ImageField(
        upload_to='',  # Empty = root directory
        storage=SupabaseStorage,
        blank=True,
        null=True,
        verbose_name='Загрузить фото',
        help_text='Загрузите фото (будет сохранено в Supabase)'
    )
    
    # URL field (auto-populated)
    image_url = models.URLField(
        max_length=500, 
        blank=True,
        verbose_name="Ссылка",
        help_text='Автоматически заполняется после загрузки'
    )
    
    alt_text = models.CharField(max_length=255, blank=True, null=True, verbose_name='Альтернативный текст')
    is_primary = models.BooleanField(default=False, verbose_name='Основное фото для этого цвета')
    display_order = models.IntegerField(default=1, verbose_name='Порядок показа')
    image_type = models.CharField(max_length=20, choices=ImageFile.choices, default=ImageFile.PNG, verbose_name="Тип файла")
    created_at = models.DateTimeField(auto_now_add=True, null=False, verbose_name="Дата создания")

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Фото товара'
        verbose_name_plural = 'Фото товаров'
        ordering = ['product', 'color', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'color'],
                condition=models.Q(is_primary=True),
                name='one_primary_per_color'
            )
        ]
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically populate image_url from uploaded file.
        Handles both new uploads and existing files.
        """
        if self.image_file:
            # Get the filename from image_file (which may contain 'products/' prefix)
            filename = self.image_file.name
            
            # Remove any directory prefix (e.g., 'products/')
            if '/' in filename:
                filename = filename.split('/')[-1]
            
            # Generate the public URL using just the filename
            from apps.core.storage import SupabaseStorage
            storage = SupabaseStorage()
            self.image_url = storage.url(filename)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.product_name} - {self.color.color_name if self.color else 'No color'}"




class RelatedProduct(models.Model):
    relation_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='related_from'
    )    
    related_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='related_to'
    )    
    relation_type = models.CharField(max_length=20, default='related')
    display_order = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'related_products'
        verbose_name_plural = 'Похожие товары'
        unique_together = [['product', 'related_product']]
    
    def __str__(self):
        return f"{self.product.product_name} -> {self.related_product.product_name}"

class CollectionProduct(models.Model):
    id = models.AutoField(primary_key=True)
    collection = models.ForeignKey(
        Collection, 
        on_delete=models.CASCADE, 
        related_name='collection_products'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='collection_memberships'
    )
    display_order = models.IntegerField(default=1)

    class Meta:
        db_table = 'collection_products'
        verbose_name_plural = 'Коллекционные товары'
        unique_together = [['collection', 'product']]
    
    def __str__(self):
        return f"{self.collection.collection_name} - {self.product.product_name}"
    


