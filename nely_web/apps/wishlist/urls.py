from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import WishlistViewSet

router = SimpleRouter()
router.register(r"", WishlistViewSet, basename="wishlist")  # no extra prefix

urlpatterns = [path("", include(router.urls))]
