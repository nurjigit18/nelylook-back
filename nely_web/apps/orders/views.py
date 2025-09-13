from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import Order, OrderItems, DeliveryZones
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderItemSerializer,
    DeliveryZoneSerializer,
)


class IsAdminOrOwner(permissions.BasePermission):
    """
    Admins: full access
    Users: only their own orders
    Guests: cannot list/retrieve (but can create via separate permission below)
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)


class OrderViewSet(viewsets.ModelViewSet):
    """
    - POST /orders/ (AllowAny): create order with nested items
    - GET /orders/ (auth): user sees own orders; admin sees all
    - GET /orders/{id}/ (auth): admin or owner
    - PATCH/DELETE: admin only (typical), you can relax if needed
    - POST /orders/{id}/confirm_payment/  -> set payment_status & transaction_id
    """
    queryset = Order.objects.all().select_related("user", "currency", "shipping_address", "billing_address").prefetch_related("items")
    permission_classes = [permissions.IsAuthenticated]  # default; overridden in get_permissions()

    def get_permissions(self):
        if self.action in ["create"]:
            return [permissions.AllowAny()]
        elif self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        else:
            # updates/deletes/payment confirmations restricted to admins by default
            return [permissions.IsAdminUser()]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_staff:
            return self.queryset.order_by("-created_at")
        if user and user.is_authenticated:
            return self.queryset.filter(user=user).order_by("-created_at")
        return Order.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def confirm_payment(self, request, pk=None):
        """
        Body: { "transaction_id": "..." , "payment_method": "..." }
        Sets payment_status=Paid.
        """
        order = self.get_object()
        txid = request.data.get("transaction_id")
        pm = request.data.get("payment_method")
        if not txid:
            return Response({"detail": "transaction_id is required."}, status=400)
        order.payment_transaction_id = txid
        if pm:
            order.payment_method = pm
        order.payment_status = "Paid"
        order.save(update_fields=["payment_transaction_id", "payment_method", "payment_status"])
        return Response(OrderSerializer(order).data, status=200)


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only items; admins see all, users see their own order items.
    """
    queryset = OrderItems.objects.select_related("order", "variant", "order__user")
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_staff:
            return self.queryset.order_by("-order_id", "-order__created_at")
        return self.queryset.filter(order__user=user).order_by("-order_id", "-order__created_at")


class DeliveryZoneViewSet(viewsets.ModelViewSet):
    """
    Delivery zones: public read, admin write.
    """
    queryset = DeliveryZones.objects.all().order_by("zone_name")
    serializer_class = DeliveryZoneSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
