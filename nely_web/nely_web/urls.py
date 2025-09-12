from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.authentication.views import (
    RegisterView, LoginView, RefreshView, LogoutView, MeView, ChangePasswordView, ValidateTokenView
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth endpoints
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/validate/", ValidateTokenView.as_view(), name="auth-validate"),

    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Your other app routes, e.g.:
    path("catalog/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
]
