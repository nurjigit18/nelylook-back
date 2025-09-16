from rest_framework import serializers
from .models import Wishlists

class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlists
        fields = ["id", "user", "session_id", "variant_id", "added_at"]
        read_only_fields = ["id", "user", "session_id", "added_at"]


class WishlistAddSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
