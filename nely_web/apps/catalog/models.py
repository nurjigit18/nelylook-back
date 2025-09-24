# apps/catalog/models.py - FIXED VERSION
from django.db import models
import uuid

class Season(models.TextChoices):
    SPRING = "spring", "Spring"
    SUMMER = "summer", "Summer"
    AUTUMN = "autumn", "Autumn"
    WINTER = "winter", "Winter"
    ALL    = "all",    "All-season"

class Gender(models.TextChoices):
    WOMEN = "women", "Women"
    MEN   = "men",   "Men"

class Status(models.TextChoices):
    DRAFT     = "draft", "Draft"
    ACTIVE    = "active","Active"
    ARCHIVED  = "archived","Archived"
    OUTOFSTOCK= "oos",   "Out of stock"

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        blank=True, null=True
    )    
    category_path = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        
    def __str__(self): 
        return self.category_name

class ClothingType(models.Model):
    type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(unique=True, max_length=50)
    category = models.ForeignKey(
        Category,  # Direct reference, not string
        on_delete=models.CASCADE,
        related_name='clothing_types',
        # Remove null constraint for now to avoid migration issues
    )    
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'clothing_types'
    
    def __str__(self): 
        return f"{self.category.category_name} · {self.type_name}"

class Color(models.Model):
    color_id = models.AutoField(primary_key=True)
    color_name = models.CharField(max_length=50, unique=True)
    color_code = models.CharField(max_length=10, blank=True, null=True)
    color_family = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'colors'
    
    def __str__(self):
        return self.color_name

class Size(models.Model):
    size_id = models.AutoField(primary_key=True)
    size_name = models.CharField(max_length=20, unique=True)
    size_category = models.CharField(max_length=20, blank=True, null=True)
    size_group = models.CharField(max_length=20, blank=True, null=True)
    sort_order = models.IntegerField(blank=True, null=True)
    measurements = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'sizes'
        ordering = ['sort_order', 'size_name']
    
    def __str__(self):
        return self.size_name

class Collection(models.Model):
    collection_id = models.AutoField(primary_key=True)
    collection_name = models.CharField(max_length=100)
    collection_slug = models.CharField(unique=True, max_length=255)
    description = models.TextField(blank=True, null=True)
    banner_image = models.CharField(max_length=500, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collections'
    
    def __str__(self):
        return self.collection_name

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.TextField(blank=True, null=True)
    
    # Fixed foreign key references
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products'
    )
    clothing_type = models.ForeignKey(
        ClothingType, 
        on_delete=models.PROTECT, 
        related_name='products'
    )
    
    season = models.CharField(max_length=10, choices=Season.choices, default=Season.ALL)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
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
        related_name='variants'
    )   
    sku = models.CharField(unique=True, max_length=100, blank=True)
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        blank=True, null=True,
        related_name='variants'
    )    
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        blank=True, null=True,
        related_name='variants'
    )    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    barcode = models.CharField(max_length=50, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    status = models.CharField(max_length=20, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_variants'
        unique_together = [['product', 'size', 'color']]
        ordering = ['product', 'color', 'size']
    
    def save(self, *args, **kwargs):
        if not self.sku:
            color_code = self.color.color_name[:2].upper() if self.color else 'NA'
            size_code = self.size.size_name if self.size else 'OS'
            self.sku = f"{self.product.product_code}-{color_code}-{size_code}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.product_name} - {self.color} - {self.size}"

class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        blank=True, null=True
    )    
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='images',
        blank=True, null=True
    )    
    image_url = models.URLField(max_length=500)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=1)
    image_type = models.CharField(max_length=20, default='Main')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['display_order']
    
    def __str__(self):
        return f"Image for {self.product or self.variant}"

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
        unique_together = [['collection', 'product']]
    
    def __str__(self):
        return f"{self.collection.collection_name} - {self.product.product_name}"