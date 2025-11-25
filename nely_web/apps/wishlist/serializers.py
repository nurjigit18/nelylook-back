from rest_framework import serializers
from .models import Wishlists
from apps.catalog.models import ProductVariant

class WishlistItemSerializer(serializers.ModelSerializer):
    """
    Enhanced wishlist serializer with full product details
    """
    product = serializers.SerializerMethodField()
    variant_id = serializers.IntegerField(source='variant.variant_id', read_only=True)
    
    class Meta:
        model = Wishlists
        fields = ["id", "variant_id", "product", "added_at"]
        read_only_fields = ["id", "added_at"]
    
    def get_product(self, obj):
        """
        Get product details from the variant with proper color-specific image
        """
        try:
            variant = obj.variant
            product = variant.product

            # Collect all images for this variant's color (up to 3 for hover effect)
            color_images = []
            primary_img_url = None

            if variant.color:
                for img in product.images.filter(color=variant.color).order_by('-is_primary', 'display_order'):
                    img_url = img.image_url
                    if img_url:
                        if img.is_primary:
                            primary_img_url = img_url
                        else:
                            color_images.append(img_url)

            # Fallback to any primary image (if no color-specific image)
            if not primary_img_url and not color_images:
                primary_image = product.images.filter(is_primary=True).first()
                if primary_image:
                    primary_img_url = primary_image.image_url

            # Last fallback: first available image
            if not primary_img_url and not color_images:
                first_image = product.images.first()
                if first_image:
                    primary_img_url = first_image.image_url

            # Build images array: primary first, then others (limit to 3)
            all_images = []
            if primary_img_url:
                all_images.append(primary_img_url)
            all_images.extend(color_images)
            all_images = all_images[:3]

            return {
                "id": product.product_id,
                "name": product.product_name,
                "slug": product.slug,
                "base_price": str(product.base_price),
                "sale_price": str(product.sale_price) if product.sale_price else None,
                "primary_image": all_images[0] if all_images else None,
                "images": all_images,  # All images for hover effect
                "category_name": product.category.category_name if product.category else None,
                "color_id": variant.color.color_id if variant.color else None,
                "color_name": variant.color.color_name if variant.color else None,
                "color_code": variant.color.color_code if variant.color else None,
                "size_name": variant.size.size_name if variant.size else None,
                "in_stock": variant.stock_quantity > 0,
                "status": product.status,
            }
        except Exception as e:
            # Log the error but don't fail the entire request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting product data for wishlist item {obj.id}: {e}")

            return {
                "id": None,
                "name": "Error loading product",
                "slug": "",
                "base_price": "0",
                "sale_price": None,
                "primary_image": None,
                "images": [],
                "category_name": None,
                "color_id": None,
                "color_name": None,
                "color_code": None,
                "size_name": None,
                "in_stock": False,
                "status": "error",
            }


class WishlistAddSerializer(serializers.Serializer):
    """
    Serializer for adding items to wishlist
    """
    variant = serializers.IntegerField(
        help_text="ID of the product variant to add to wishlist"
    )
    
    def validate_variant(self, value):
        """
        Validate that the variant exists and is available
        """
        try:
            variant = ProductVariant.objects.select_related('product').get(variant_id=value)
            
            # Check if product is active
            if variant.product.status != 'active':
                raise serializers.ValidationError("This product is not available")
            
            return value
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError("Product variant not found")