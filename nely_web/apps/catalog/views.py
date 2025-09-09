from rest_framework import viewsets
from .models import Product, Category, ClothingType
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    ClothingTypeSerializer,
)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ClothingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClothingType.objects.all()
    serializer_class = ClothingTypeSerializer

    # optional: filter by category ?category=<id>
    def get_queryset(self):
        qs = super().get_queryset()
        cat_id = self.request.query_params.get("category")
        return qs.filter(category_id=cat_id) if cat_id else qs
