from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FxRateViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"fx-rates", FxRateViewSet, basename="fx-rates")
router.register(r"payments-list", PaymentViewSet, basename="payments-list")

urlpatterns = [
    path("", include(router.urls)),
]
