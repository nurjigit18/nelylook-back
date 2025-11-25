from rest_framework import serializers
from django.utils import timezone
from .models import ShoppingCart, CartItems

class CartItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(read_only=True)
    product = serializers.SerializerMethodField()

    class Meta:
        model = CartItems
        fields = ["cart_item_id", "variant_id", "quantity", "price", "added_at", "product"]

    def get_product(self, obj):
        """
        Get full product details from the variant (similar to wishlist)
        """
        try:
            variant = obj.variant
            product = variant.product

            # Get image for this specific variant's color
            primary_image = None
            if variant.color:
                # First try: primary image for this color
                primary_image = product.images.filter(
                    color=variant.color,
                    is_primary=True
                ).first()

                # Second try: any image for this color
                if not primary_image:
                    primary_image = product.images.filter(
                        color=variant.color
                    ).order_by('-is_primary').first()

            # Fallback to any primary image
            if not primary_image:
                primary_image = product.images.filter(is_primary=True).first()

            # Last fallback: first available image
            if not primary_image:
                primary_image = product.images.first()

            return {
                "id": product.product_id,
                "name": product.product_name,
                "slug": product.slug,
                "base_price": str(product.base_price),
                "sale_price": str(product.sale_price) if product.sale_price else None,
                "primary_image": primary_image.image_url if primary_image else None,
                "category_name": product.category.category_name if product.category else None,
                "color_name": variant.color.color_name if variant.color else None,
                "color_code": variant.color.color_code if variant.color else None,
                "size_name": variant.size.size_name if variant.size else None,
                "in_stock": variant.stock_quantity > 0,
                "stock_quantity": variant.stock_quantity,
                "status": product.status,
            }
        except Exception as e:
            # Log the error but don't fail the entire request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting product data for cart item {obj.cart_item_id}: {e}")

            return {
                "id": None,
                "name": "Error loading product",
                "slug": "",
                "base_price": "0",
                "sale_price": None,
                "primary_image": None,
                "category_name": None,
                "color_name": None,
                "color_code": None,
                "size_name": None,
                "in_stock": False,
                "stock_quantity": 0,
                "status": "error",
            }

class CartItemWriteSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ["cart_id", "user", "session_id", "created_at", "updated_at", "items"]

    def to_representation(self, instance):
        # ensure timestamps are present in case model allowed NULLs
        if not instance.created_at:
            instance.created_at = timezone.now()
        instance.updated_at = timezone.now()
        instance.save(update_fields=["created_at", "updated_at"])
        return super().to_representation(instance)
