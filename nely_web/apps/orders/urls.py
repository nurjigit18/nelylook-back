from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderItemViewSet, DeliveryZoneViewSet

router = DefaultRouter()
router.register(r"orders-list", OrderViewSet, basename="orders-list")
router.register(r"order-items", OrderItemViewSet, basename="order-items")
router.register(r"delivery-zones", DeliveryZoneViewSet, basename="delivery-zones")

urlpatterns = [
    path("", include(router.urls)),
]
