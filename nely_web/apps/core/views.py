# apps/analytics/views.py
from rest_framework import viewsets, permissions
from django.utils import timezone

from .models import ProductViews, AdminLogs, Currency
from .serializers import ProductViewsSerializer, AdminLogsSerializer, CurrencySerializer


class ProductViewsViewSet(viewsets.ModelViewSet):
    """
    API for tracking product views.
    - Normal users/guests can POST to track a view
    - Admins can list all views
    """
    queryset = ProductViews.objects.all().order_by("-viewed_at")
    serializer_class = ProductViewsSerializer
    permission_classes = [permissions.AllowAny]  # allow guests to log views

    def perform_create(self, serializer):
        # auto-fill viewed_at, user, ip
        request = self.request
        user = request.user if request.user.is_authenticated else None
        ip = request.META.get("REMOTE_ADDR")
        session_id = request.META.get("HTTP_X_SESSION_ID")  # guest session

        serializer.save(
            user=user,
            ip_address=ip,
            session_id=session_id,
            viewed_at=timezone.now()
        )


class AdminLogsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for admin logs.
    """
    queryset = AdminLogs.objects.all().order_by("-created_at")
    serializer_class = AdminLogsSerializer
    permission_classes = [permissions.IsAdminUser]


class CurrencyViewSet(viewsets.ModelViewSet):
    """
    CRUD for currencies (admin only).
    """
    queryset = Currency.objects.all().order_by("-created_at")
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_at=timezone.now(), updated_at=timezone.now())

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())
