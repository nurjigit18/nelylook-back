# apps/catalog/models.py - FIXED VERSION
from django.db import models
from apps.core.storage import SupabaseStorage
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
    banner_image = models.CharField(max_length=500, blank=True, null=True)
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    display_order = models.IntegerField(blank=True, null=True, verbose_name="Приоритет")
    is_active = models.BooleanField(default=True, verbose_name="В наличии")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = 'collections'
        verbose_name_plural = 'Коллекции'
    
    def __str__(self):
        return self.collection_name

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
        verbose_name='Тип одежды'
    )
    
    season = models.CharField(max_length=10, choices=Season.choices, default=Season.ALL, verbose_name="Сезон")
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая цена")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Цена по скидке")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Расходная цена")
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    is_new_arrival = models.BooleanField(default=False, verbose_name="Новое")
    is_bestseller = models.BooleanField(default=False, verbose_name="Популярное")
    stock_quantity = models.IntegerField(default=0, editable=False, verbose_name="В наличии")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        db_table = 'products'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.stock_quantity <= 0:
            self.status = Status.OUT_OF_STOCK
        else:
            if self.status == Status.OUT_OF_STOCK:
                self.status = Status.ACTIVE
        super().save(*args, **kwargs)
        if is_new and not self.product_code:
            self.product_code = f"NL-{self.product_id:06d}"
            super().save(update_fields=['product_code'])

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
    sku = models.CharField(unique=True, max_length=100, blank=True, verbose_name="Артикул")
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
    barcode = models.CharField(max_length=50, blank=True, null=True, verbose_name="Баркод")
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


class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        verbose_name='Модель'
    )
    
    # Link to Color (required) - this is the key!
    color = models.ForeignKey(
        'Color',
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name='product_images',
        verbose_name='Цвет'
    )
    
    # NEW: File upload field - uploads to Supabase
    image_file = models.ImageField(
        upload_to='products/',
        storage=SupabaseStorage,
        blank=True,
        null=True,
        verbose_name='Загрузить фото',
        help_text='Загрузите фото (будет сохранено в Supabase)'
    )
    
    # Existing URL field - auto-populated from Supabase
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Фото товара'
        verbose_name_plural = 'Фото товаров'
        ordering = ['product', 'color', 'display_order']
        # Ensure each color has one primary image
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'color'],
                condition=models.Q(is_primary=True),
                name='one_primary_per_color'
            )
        ]
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically populate image_url from uploaded file
        """
        if self.image_file and not self.image_url:
            # Get the public URL from Supabase
            storage = SupabaseStorage()
            self.image_url = storage.url(self.image_file.name)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.product_name} - {self.color.color_name}"


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