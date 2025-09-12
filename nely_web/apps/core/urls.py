# apps/analytics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewsViewSet, AdminLogsViewSet, CurrencyViewSet

router = DefaultRouter()
router.register(r"product-views", ProductViewsViewSet, basename="productviews")
router.register(r"admin-logs", AdminLogsViewSet, basename="adminlogs")
router.register(r"currencies", CurrencyViewSet, basename="currencies")

urlpatterns = [
    path("", include(router.urls)),
]
