# apps/catalog/serializers.py
from rest_framework import serializers
from .models import (
    Category, ClothingType, Product, ProductVariant,
    ProductImage, ProductVideo, Collection, Color, Size
)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    id = serializers.IntegerField(source="category_id", read_only=True)
    name = serializers.CharField(source="category_name")
    slug = serializers.SlugField(source="category_slug", read_only=True)  
    parent = serializers.PrimaryKeyRelatedField(
        source="parent_category",
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
    )
    parent_name = serializers.CharField(
        source="parent_category.category_name", 
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug",
            "category_path", "description",
            "display_order", "is_active",
            "parent", "parent_name",
        ]


class ClothingTypeSerializer(serializers.ModelSerializer):
    """Serializer for ClothingType model."""
    id = serializers.IntegerField(source="type_id", read_only=True)
    name = serializers.CharField(source="type_name")
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )

    class Meta:
        model = ClothingType
        fields = ["id", "name", "category", "category_name", "display_order", "is_active"]


class ColorSerializer(serializers.ModelSerializer):
    """Serializer for Color model."""
    id = serializers.IntegerField(source="color_id", read_only=True)
    name = serializers.CharField(source="color_name")
    code = serializers.CharField(source="color_code", allow_null=True, required=False)
    family = serializers.CharField(source="color_family", allow_null=True, required=False)

    class Meta:
        model = Color
        fields = ["id", "name", "code", "family", "is_active"]


class SizeSerializer(serializers.ModelSerializer):
    """Serializer for Size model."""
    id = serializers.IntegerField(source="size_id", read_only=True)
    name = serializers.CharField(source="size_name")
    code = serializers.CharField(source="size_code", allow_null=True, required=False)
    category = serializers.CharField(source="size_category", allow_null=True, required=False)
    group = serializers.CharField(source="size_group", allow_null=True, required=False)

    class Meta:
        model = Size
        fields = ["id", "name", "code", "category", "group", "sort_order", "measurements", "is_active"]


class ProductImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="image_id", read_only=True)
    url = serializers.SerializerMethodField()
    color = ColorSerializer(read_only=True)
    color_id = serializers.IntegerField(source="color.color_id", read_only=True, allow_null=True)
    
    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt_text", "is_primary", "display_order", "color", "color_id"]
    
    def get_url(self, obj):
        """Get the image URL, handling both image_url field and image_file"""
        if obj.image_url:
            return obj.image_url
        elif obj.image_file:
            from apps.core.storage import SupabaseStorage
            storage = SupabaseStorage()
            filename = obj.image_file.name
            if '/' in filename:
                filename = filename.split('/')[-1]
            return storage.url(filename)
        return None


class ProductVideoSerializer(serializers.ModelSerializer):
    """Serializer for ProductVideo model."""
    id = serializers.IntegerField(read_only=True)
    color_id = serializers.IntegerField(source='color.color_id', read_only=True, allow_null=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductVideo
        fields = ["id", "url", "video_url", "thumbnail_url", "display_order", "duration", "color_id"]

    def get_url(self, obj):
        """Get the video URL, handling both video_file and video_url"""
        if obj.video_file:
            from apps.core.storage import SupabaseStorage
            storage = SupabaseStorage()
            filename = obj.video_file.name
            if '/' in filename:
                filename = filename.split('/')[-1]
            return storage.url(filename)
        elif obj.video_url:
            return obj.video_url
        return None


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for ProductVariant model."""
    id = serializers.IntegerField(source="variant_id", read_only=True)
    size = SizeSerializer(read_only=True)
    size_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    color = ColorSerializer(read_only=True)
    color_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    is_available = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku",
            "size", "size_id",
            "color", "color_id",
            "stock_quantity", "low_stock_threshold",
            "status", "is_available", "is_low_stock", "created_at"
        ]
        read_only_fields = ("created_at",)
    
    def get_is_available(self, obj):
        """Check if variant is available for purchase."""
        return obj.stock_quantity > 0 and obj.status == 'active'
    
    def get_is_low_stock(self, obj):
        """Check if variant stock is low."""
        return 0 < obj.stock_quantity <= obj.low_stock_threshold


class ProductSerializer(serializers.ModelSerializer):
    """
    Basic product serializer with images.
    Used for product list views.
    """
    id = serializers.IntegerField(source="product_id", read_only=True)
    name = serializers.CharField(source="product_name")
    code = serializers.CharField(source="product_code", read_only=True)
    
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(
        source="category.category_name", read_only=True
    )
    
    clothing_type = serializers.PrimaryKeyRelatedField(
        queryset=ClothingType.objects.all(),
        allow_null=True,
        required=False
    )
    clothing_type_name = serializers.CharField(
        source="clothing_type.type_name", 
        read_only=True, 
        allow_null=True
    )
    
    season_display = serializers.CharField(source="get_season_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # Images and Videos
    images = ProductImageSerializer(many=True, read_only=True)
    videos = ProductVideoSerializer(many=True, read_only=True)

    # Available sizes
    available_sizes = serializers.SerializerMethodField()
    
    # ✅ NEW: Wishlist support fields
    default_variant_id = serializers.SerializerMethodField()
    primary_color_id = serializers.SerializerMethodField()
    primary_color_name = serializers.SerializerMethodField()
    primary_color_code = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "code", "name", "slug",
            "description", "short_description",
            "fabric_composition", "care_instructions",
            "category", "category_name",
            "clothing_type", "clothing_type_name",
            "season", "season_display",
            "base_price", "sale_price", "cost_price",
            "is_featured", "is_new_arrival", "is_bestseller",
            "stock_quantity",
            "status", "status_display",
            "images",
            "videos",
            "available_sizes",
            "default_variant_id",      # ✅ For wishlist
            "primary_color_id",        # ✅ For reference
            "primary_color_name",      # ✅ For display
            "primary_color_code",      # ✅ For UI
            "created_at", "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at", "code")
    
    def get_available_sizes(self, obj):
        """Get unique sizes available for this product."""
        sizes = Size.objects.filter(
            variants__product=obj,
            variants__status='active',
            is_active=True
        ).distinct().order_by('sort_order')
        return SizeSerializer(sizes, many=True).data
    
    def get_primary_color_id(self, obj):
        """Get the color ID of the primary image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.color:
            return primary_image.color.color_id
        return None
    
    def get_primary_color_name(self, obj):
        """Get the color name of the primary image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.color:
            return primary_image.color.color_name
        return None
    
    def get_primary_color_code(self, obj):
        """Get the color code (hex) of the primary image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.color:
            return primary_image.color.color_code
        return None
    
    def get_default_variant_id(self, obj):
        """
        Get the first available variant ID for the primary color.
        This is used for wishlisting from product cards.
        
        Strategy:
        1. Get the color from the primary image
        2. Find first in-stock variant with that color (ordered by size)
        3. Fallback to any variant with that color
        4. Final fallback to any available variant
        """
        # Get primary image color
        primary_image = obj.images.filter(is_primary=True).first()
        
        if primary_image and primary_image.color:
            # Try to get in-stock variant with this color (smallest size first)
            variant = obj.variants.filter(
                color=primary_image.color,
                status='active',
                stock_quantity__gt=0
            ).order_by('size__sort_order', 'variant_id').first()
            
            # Fallback: any active variant with this color
            if not variant:
                variant = obj.variants.filter(
                    color=primary_image.color,
                    status='active'
                ).order_by('size__sort_order', 'variant_id').first()
            
            if variant:
                return variant.variant_id
        
        # Final fallback: any available variant
        variant = obj.variants.filter(
            status='active',
            stock_quantity__gt=0
        ).order_by('variant_id').first()
        
        return variant.variant_id if variant else None


class ProductColorVariantSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying products grouped by color.
    Each color variant appears as a separate product card.
    """
    id = serializers.IntegerField(source="product_id", read_only=True)
    name = serializers.CharField(source="product_name")
    slug = serializers.CharField(read_only=True)
    
    # Color-specific fields
    color_id = serializers.IntegerField()
    color_name = serializers.CharField()
    color_code = serializers.CharField()
    
    # Primary image for this color
    primary_image = serializers.CharField(allow_null=True)
    
    # Price fields
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    
    # Available sizes for this color
    available_sizes = serializers.ListField(child=serializers.CharField())
    
    class Meta:
        model = Product
        fields = [
            "id", "slug", "name",
            "color_id", "color_name", "color_code",
            "primary_image",
            "base_price", "sale_price",
            "available_sizes",
            "is_featured", "is_new_arrival", "is_bestseller",
            "category", "season"
        ]


class ProductDetailSerializer(ProductSerializer):
    """
    Extended product serializer for detail view.
    Shows more information but still hides sensitive data.
    """
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Full description for detail page
    description = serializers.CharField(read_only=True)
    
    # Available options
    available_colors = serializers.SerializerMethodField()
    available_sizes = serializers.SerializerMethodField()
    
    # Season info
    season_display = serializers.CharField(source="get_season_display", read_only=True)
    
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + [
            "description",
            "season_display",
            "variants", 
            "images", 
            "available_colors", 
            "available_sizes",
        ]
    
    def get_available_colors(self, obj):
        """Get unique colors available for this product."""
        colors = Color.objects.filter(
            variants__product=obj,
            variants__status='active',
            variants__stock_quantity__gt=0
        ).distinct()
        return ColorSerializer(colors, many=True).data
    
    def get_available_sizes(self, obj):
        """Get unique sizes available for this product."""
        sizes = Size.objects.filter(
            variants__product=obj,
            variants__status='active',
            variants__stock_quantity__gt=0
        ).distinct().order_by('sort_order')
        return SizeSerializer(sizes, many=True).data


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model."""
    id = serializers.IntegerField(source="collection_id", read_only=True)
    name = serializers.CharField(source="collection_name")
    slug = serializers.CharField(source="collection_slug")
    product_count = serializers.SerializerMethodField()
    banner_image = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            "id", "name", "slug", "description",
            "banner_image", "is_featured", "display_order",
            "is_active", "created_at", "product_count"
        ]
        read_only_fields = ("created_at",)

    def get_banner_image(self, obj):
        """Return full URL for banner image."""
        if obj.banner_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner_image.url)
            return obj.banner_image.url
        return None

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
        ).select_related('category', 'clothing_type').prefetch_related('images')[:20]
        return ProductSerializer(products, many=True).data