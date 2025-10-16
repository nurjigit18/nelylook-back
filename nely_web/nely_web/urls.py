from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.authentication.views import (
    RegisterView, LoginView, RefreshView, LogoutView, MeView, ChangePasswordView, ValidateTokenView
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Your other app routes, e.g.:
    path("auth/", include("apps.authentication.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("core/", include("apps.core.urls")),
    path("orders/", include("apps.orders.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("payments/", include("apps.payments.urls")),
    path("media/", include("apps.media.urls")),
]
