from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import FxRate, Payment
from .serializers import (
    FxRateSerializer, FxLatestQuerySerializer,
    PaymentSerializer, PaymentCreateSerializer,
    PaymentInitiateSerializer, PaymentConfirmSerializer,
)


# ---------- Permissions ----------

class IsAdminOrOwnerPayment(permissions.BasePermission):
    """Admins see all. Users see payments for their own orders."""
    def has_object_permission(self, request, view, obj: Payment):
        if request.user and request.user.is_staff:
            return True
        return getattr(obj.order, "user_id", None) == getattr(request.user, "id", None)


# ---------- FX Rates ----------

class FxRateViewSet(viewsets.ModelViewSet):
    """
    FX Rates: public read, admin write.
    """
    queryset = FxRate.objects.select_related("base_currency", "quote_currency").order_by("-as_of")
    serializer_class = FxRateSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    @extend_schema(
        request=FxLatestQuerySerializer,
        responses=FxRateSerializer,
        description="Get latest FX rate for a base/quote pair."
    )
    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        ser = FxLatestQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        base = ser.validated_data["base"].pk
        quote = ser.validated_data["quote"].pk
        obj = (FxRate.objects
               .filter(base_currency_id=base, quote_currency_id=quote)
               .order_by("-as_of")
               .first())
        if not obj:
            return Response({"detail": "Rate not found."}, status=404)
        return Response(FxRateSerializer(obj).data)
        

# ---------- Payments ----------

class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payments:
    - Admin CRUD via standard endpoints
    - Users can list/retrieve their payments
    - Public/owner 'initiate' endpoint to create a Pending payment by order_number (owner or matching guest email)
    - Admin/webhook 'confirm' endpoint to finalize status and store gateway_response
    """
    queryset = Payment.objects.select_related("order", "order__user", "currency").order_by("-created_at")
    serializer_class = PaymentSerializer  # default

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        if self.action in ["initiate"]:
            return [permissions.AllowAny()]
        if self.action in ["confirm"]:
            return [permissions.IsAdminUser()]
        # standard create/update/delete: admin
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_staff:
            return self.queryset
        if user and user.is_authenticated:
            return self.queryset.filter(order__user=user)
        return Payment.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        if self.action == "initiate":
            return PaymentInitiateSerializer
        if self.action == "confirm":
            return PaymentConfirmSerializer
        return PaymentSerializer

    @extend_schema(
        request=PaymentInitiateSerializer,
        responses=PaymentSerializer,
        description="Create a Pending payment for an order (owner or matching guest_email)."
    )
    @action(detail=False, methods=["post"])
    def initiate(self, request):
        ser = PaymentInitiateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        payment = ser.save()
        return Response(PaymentSerializer(payment).data, status=201)

    @extend_schema(
        request=PaymentConfirmSerializer,
        responses=PaymentSerializer,
        description="Admin/webhook: confirm or update a payment by payment_id or transaction_id."
    )
    @action(detail=False, methods=["post"])
    def confirm(self, request):
        ser = PaymentConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        pid = ser.validated_data.get("payment_id")
        tx = ser.validated_data.get("transaction_id")
        status_val = ser.validated_data["status"]
        gw = ser.validated_data.get("gateway_response")

        if pid:
            try:
                obj = Payment.objects.get(pk=pid)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=404)
        else:
            try:
                obj = Payment.objects.get(transaction_id=tx)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found for transaction_id."}, status=404)

        obj.status = status_val
        if gw is not None:
            obj.gateway_response = gw
        # set processed_at when terminal states are reached
        if status_val in ["Completed", "Failed", "Refunded", "Partially Refunded"]:
            obj.processed_at = timezone.now()
        obj.save(update_fields=["status", "gateway_response", "processed_at"])
        return Response(PaymentSerializer(obj).data, status=200)
