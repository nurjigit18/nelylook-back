from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.permissions import IsAdminUser
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.authentication.views import (
    RegisterView, LoginView, RefreshView, LogoutView, MeView, ChangePasswordView, ValidateTokenView
)
from apps.cms_content.api import api_router, social_links_api

# Secure API documentation views (require admin login)
class SecureSpectacularAPIView(SpectacularAPIView):
    permission_classes = [IsAdminUser]

class SecureSpectacularSwaggerView(SpectacularSwaggerView):
    permission_classes = [IsAdminUser]

class SecureSpectacularRedocView(SpectacularRedocView):
    permission_classes = [IsAdminUser]

urlpatterns = [
    path("admin/", admin.site.urls),

    # Wagtail CMS Admin
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),

    # OpenAPI / Swagger (ADMIN ONLY - requires authentication)
    path("api/schema/", SecureSpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SecureSpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SecureSpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Your other app routes, e.g.:
    path("auth/", include("apps.authentication.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("core/", include("apps.core.urls")),
    path("orders/", include("apps.orders.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("payments/", include("apps.payments.urls")),
    path("media/", include("apps.media.urls")),

    # Wagtail CMS API endpoints
    path("api/v2/", api_router.urls),  # Wagtail pages, images, documents API
    path("api/cms/social-links/", social_links_api, name="social-links"),  # Custom social links endpoint
]
