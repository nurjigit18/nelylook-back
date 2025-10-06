# apps/catalog/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CategoryViewSet,
    ClothingTypeViewSet,
    ColorViewSet,
    SizeViewSet,
    CollectionViewSet,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'clothing-types', ClothingTypeViewSet, basename='clothingtype')
router.register(r'colors', ColorViewSet, basename='color')
router.register(r'sizes', SizeViewSet, basename='size')
router.register(r'collections', CollectionViewSet, basename='collection')

urlpatterns = [path("", include(router.urls))]
