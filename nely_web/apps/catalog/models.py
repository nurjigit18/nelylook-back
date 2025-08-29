from django.db import models

# Create your models here.

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,          # don’t allow deleting a parent that has children
        related_name='children',
        blank=True, null=True
    )    
    category_path = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'categories'
        db_table_comment = 'Hierarchical: Clothing > Shirts > T-Shirts'

class ClothingType(models.Model):
    type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(unique=True, max_length=50)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,         # if a category is removed, types survive (optional)
        blank=True, null=True
    )    
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'clothing_types'
        db_table_comment = 'Shirt, T-Shirt, Pants, Jeans, Dress, etc.'
        
class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(unique=True, max_length=50)
    slug = models.CharField(unique=True, max_length=255, db_comment='URL-friendly: blue-cotton-tshirt')
    description = models.TextField(blank=True, null=True)
    short_description = models.TextField(blank=True, null=True, db_comment='For product cards')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,         # keep products if a category is deleted
        blank=True, null=True
    )    
    clothing_type = models.ForeignKey(
        ClothingType,
        on_delete=models.SET_NULL,         # same idea for type
        blank=True, null=True
    )    
    season = models.CharField(max_length=50, blank=True, null=True, db_comment='Spring, Summer, Fall, Winter')
    gender = models.CharField(max_length=20, blank=True, null=True, db_comment='Men, Women, Unisex, Kids')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_comment='Discounted price if on sale')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_featured = models.BooleanField(blank=True, null=True, db_comment='Show on homepage')
    is_new_arrival = models.BooleanField(blank=True, null=True)
    is_bestseller = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True, db_comment='Active, Inactive, Draft')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'products'


class CollectionProduct(models.Model):
    id = models.AutoField(primary_key=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE, related_name='collection_products')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='collection_memberships')
    display_order = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'collection_products'
        constraints = [models.UniqueConstraint(fields=['collection','product'], name='uniq_collection_product')]


class Collection(models.Model):
    collection_id = models.AutoField(primary_key=True)
    collection_name = models.CharField(max_length=100)
    collection_slug = models.CharField(unique=True, max_length=255)
    description = models.TextField(blank=True, null=True)
    banner_image = models.CharField(max_length=500, blank=True, null=True)
    is_featured = models.BooleanField(blank=True, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'collections'

class Color(models.Model):
    color_id = models.AutoField(primary_key=True)
    color_name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=10, blank=True, null=True, db_comment='Hex color code #FF0000')
    color_family = models.CharField(max_length=30, blank=True, null=True, db_comment='Red, Blue, Green, etc.')
    is_active = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'colors'

class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,          # images are “owned” by the product
        blank=True, null=True
    )    
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='images',          # <- was 'cart_images'
        related_query_name='image',
    )    
    image_url = models.CharField(max_length=500)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(blank=True, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    image_type = models.CharField(max_length=20, blank=True, null=True, db_comment='Main, Gallery, Thumbnail, Hover')
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'product_images'

class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    product = models.ForeignKey('Product',on_delete=models.CASCADE)   
    sku = models.CharField(unique=True, max_length=100)
    size = models.ForeignKey(
        'Size',
        on_delete=models.PROTECT,          # don’t allow deleting a Size in use
        blank=True, null=True
    )    
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,          # same for Color; avoids silent data drift
        blank=True, null=True
    )    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True, db_comment='For shipping calculations')
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    barcode = models.CharField(max_length=50, blank=True, null=True)
    stock_quantity = models.IntegerField(blank=True, null=True, db_comment='Current stock level')
    low_stock_threshold = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True, db_comment='Active, Inactive, Out of Stock')
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'product_variants'
        managed = True

class RelatedProduct(models.Model):
    relation_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE           # if either product goes away, drop the relation row
    )    
    related_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='relatedproducts_related_product_set'
    )    
    relation_type = models.CharField(max_length=20, blank=True, null=True, db_comment='related, similar, upsell, crosssell')
    display_order = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'related_products'
        db_table_comment = 'For "See Also", "You might also like", "Similar Products"'

class Size(models.Model):
    size_id = models.AutoField(primary_key=True)
    size_name = models.CharField(max_length=20)
    size_category = models.CharField(max_length=20, blank=True, null=True, db_comment='Clothing, Shoes, Accessories')
    size_group = models.CharField(max_length=20, blank=True, null=True, db_comment='XS, S, M, L, XL or 28, 30, 32')
    sort_order = models.IntegerField(blank=True, null=True)
    measurements = models.TextField(blank=True, null=True, db_comment='chest, waist, hip measurements')  # This field type is a guess.
    is_active = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'sizes'