from rest_framework import serializers
from django.utils import timezone
from .models import ShoppingCart, CartItems

class CartItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(source="variant_id", read_only=True)

    class Meta:
        model = CartItems
        fields = ["cart_item_id", "variant_id", "quantity", "price", "added_at"]

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
