from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, ClothingTypeViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"clothing-types", ClothingTypeViewSet, basename="clothingtype")

urlpatterns = [path("", include(router.urls))]
