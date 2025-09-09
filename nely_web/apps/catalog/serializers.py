# apps/catalog/serializers.py
from rest_framework import serializers
from .models import Category, ClothingType, Product

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

    # write FK by PK; read a friendly label
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

    # nice human-readable labels for choices
    season_display = serializers.CharField(source="get_season_display", read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "code", "name", "slug",
            "description", "short_description",
            "category", "category_name",
            "clothing_type", "clothing_type_name",
            "season", "season_display",
            "gender", "gender_display",
            "base_price", "sale_price", "cost_price",
            "is_featured", "is_new_arrival", "is_bestseller",
            "status", "status_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")
