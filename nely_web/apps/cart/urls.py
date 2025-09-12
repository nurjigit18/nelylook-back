from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CartViewSet

router = SimpleRouter()
router.register(r"", CartViewSet, basename="cart")

urlpatterns = [
    path("", include(router.urls)),
]
