# apps/catalog/serializers.py - ADD THESE TO YOUR EXISTING SERIALIZERS
from rest_framework import serializers
from .models import (
    Category, ClothingType, Product, ProductVariant, 
    ProductImage, Collection, Color, Size
)


# ===== Your existing serializers (keep these) =====
class CategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="category_id", read_only=True)
    name = serializers.CharField(source="category_name")
    parent = serializers.PrimaryKeyRelatedField(
        source="parent_category",
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
    )
    parent_name = serializers.CharField(
        source="parent_category.category_name", read_only=True
    )

    class Meta:
        model = Category
        fields = [
            "id", "name",
            "category_path", "description",
            "display_order", "is_active",
            "parent", "parent_name",
        ]


class ClothingTypeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="type_id", read_only=True)
    name = serializers.CharField(source="type_name")
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )

    class Meta:
        model = ClothingType
        fields = ["id", "name", "category", "category_name", "display_order", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="product_id", read_only=True)
    name = serializers.CharField(source="product_name")
    code = serializers.CharField(source="product_code", read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )
    clothing_type = serializers.PrimaryKeyRelatedField(queryset=ClothingType.objects.all())
    clothing_type_name = serializers.CharField(
        source="clothing_type.type_name", read_only=True
    )
    season_display = serializers.CharField(source="get_season_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "code", "name", "slug",
            "description", "short_description",
            "category", "category_name",
            "clothing_type", "clothing_type_name",
            "season", "season_display",
            "base_price", "sale_price", "cost_price",
            "is_featured", "is_new_arrival", "is_bestseller",
            "stock_quantity",
            "status", "status_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


# ===== NEW SERIALIZERS - ADD THESE =====

class ColorSerializer(serializers.ModelSerializer):
    """Serializer for Color model."""
    id = serializers.IntegerField(source="color_id", read_only=True)
    name = serializers.CharField(source="color_name")
    code = serializers.CharField(source="color_code", allow_null=True)
    family = serializers.CharField(source="color_family", allow_null=True)

    class Meta:
        model = Color
        fields = ["id", "name", "code", "family", "is_active"]


class SizeSerializer(serializers.ModelSerializer):
    """Serializer for Size model."""
    id = serializers.IntegerField(source="size_id", read_only=True)
    name = serializers.CharField(source="size_name")
    category = serializers.CharField(source="size_category", allow_null=True)
    group = serializers.CharField(source="size_group", allow_null=True)

    class Meta:
        model = Size
        fields = ["id", "name", "category", "group", "sort_order", "measurements", "is_active"]


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model."""
    id = serializers.IntegerField(source="image_id", read_only=True)
    color = ColorSerializer(read_only=True)
    color_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    url = serializers.CharField(source="image_url", read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            "id", "color", "color_id", "url", 
            "alt_text", "is_primary", "display_order", "image_type"
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant model."""
    id = serializers.IntegerField(source="variant_id", read_only=True)
    size = SizeSerializer(read_only=True)
    size_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    color = ColorSerializer(read_only=True)
    color_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Calculate availability
    is_available = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", 
            "size", "size_id",
            "color", "color_id",
            "barcode", "stock_quantity", "low_stock_threshold",
            "status", "is_available", "is_low_stock", "created_at"
        ]
        read_only_fields = ("created_at",)
    
    def get_is_available(self, obj):
        """Check if variant is available for purchase."""
        return obj.stock_quantity > 0 and obj.status == 'active'
    
    def get_is_low_stock(self, obj):
        """Check if variant is low on stock."""
        return 0 < obj.stock_quantity <= obj.low_stock_threshold


class ProductDetailSerializer(ProductSerializer):
    """
    Extended product serializer with variants and images.
    Used for product detail view.
    """
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Available colors and sizes (unique from variants)
    available_colors = serializers.SerializerMethodField()
    available_sizes = serializers.SerializerMethodField()
    
    # Price info
    price_info = serializers.SerializerMethodField()
    
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + [
            "variants", "images", 
            "available_colors", "available_sizes",
            "price_info"
        ]
    
    def get_available_colors(self, obj):
        """Get unique colors available for this product."""
        colors = Color.objects.filter(
            variants__product=obj,
            variants__status='active'
        ).distinct()
        return ColorSerializer(colors, many=True).data
    
    def get_available_sizes(self, obj):
        """Get unique sizes available for this product."""
        sizes = Size.objects.filter(
            variants__product=obj,
            variants__status='active'
        ).distinct().order_by('sort_order')
        return SizeSerializer(sizes, many=True).data
    
    def get_price_info(self, obj):
        """Get pricing information."""
        has_sale = obj.sale_price is not None
        return {
            "base_price": str(obj.base_price),
            "sale_price": str(obj.sale_price) if has_sale else None,
            "discount_percentage": round((1 - (obj.sale_price / obj.base_price)) * 100) if has_sale else 0,
            "on_sale": has_sale
        }


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model."""
    id = serializers.IntegerField(source="collection_id", read_only=True)
    name = serializers.CharField(source="collection_name")
    slug = serializers.CharField(source="collection_slug")
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            "id", "name", "slug", "description",
            "banner_image", "is_featured", "display_order",
            "is_active", "created_at", "product_count"
        ]
        read_only_fields = ("created_at",)
    
    def get_product_count(self, obj):
        """Count of active products in collection."""
        return obj.collection_products.filter(
            product__status='active'
        ).count()


class CollectionDetailSerializer(CollectionSerializer):
    """Extended collection serializer with products."""
    products = serializers.SerializerMethodField()
    
    class Meta(CollectionSerializer.Meta):
        fields = CollectionSerializer.Meta.fields + ["products"]
    
    def get_products(self, obj):
        """Get products in this collection."""
        products = Product.objects.filter(
            collection_memberships__collection=obj,
            status='active'
        ).select_related('category', 'clothing_type')[:20]
        return ProductSerializer(products, many=True).data