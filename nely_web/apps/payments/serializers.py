from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone

from .models import FxRate, Payment
from apps.core.models import Currency
from apps.orders.models import Order


# --------------------- FX RATES ---------------------

class FxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxRate
        fields = [
            "fx_rate_id",
            "base_currency", "base_currency_id",
            "quote_currency", "quote_currency_id",
            "rate", "source", "as_of",
        ]
        read_only_fields = ["fx_rate_id", "as_of"]


class FxLatestQuerySerializer(serializers.Serializer):
    base = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())
    quote = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())


# --------------------- PAYMENTS ---------------------

class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "payment_id",
            "order", "order_number",
            "payment_method", "payment_provider",
            "transaction_id",
            "amount", "currency",
            "status",
            "gateway_response",
            "processed_at", "created_at",
        ]
        read_only_fields = ["payment_id", "created_at", "processed_at"]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Admin CRUD create."""
    class Meta:
        model = Payment
        fields = [
            "order",
            "payment_method", "payment_provider",
            "transaction_id",
            "amount", "currency",
            "status", "gateway_response",
        ]

    def validate(self, attrs):
        order = attrs.get("order")
        currency = attrs.get("currency")
        if order and currency and order.currency_id != currency.pk:
            raise serializers.ValidationError("Payment currency must match order currency.")
        return attrs


class PaymentInitiateSerializer(serializers.Serializer):
    """
    Public/owner-initiated payment (creates a Pending payment).
    One of: authenticated owner OR matching guest_email must be provided.
    """
    order_number = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())
    payment_method = serializers.CharField(max_length=50)
    payment_provider = serializers.CharField(max_length=50, allow_blank=True, required=False)
    transaction_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    guest_email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        # lookup order
        try:
            order = Order.objects.select_related("user").get(order_number=attrs["order_number"])
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order_number": "Order not found."})

        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Ownership / guest validation
        guest_email = attrs.get("guest_email")
        if user and user.is_authenticated:
            if order.user_id != user.id:
                raise serializers.ValidationError("Not your order.")
        else:
            if not guest_email or guest_email != (order.guest_email or ""):
                raise serializers.ValidationError("Guest email does not match the order.")

        # currency check
        if order.currency_id != attrs["currency"].pk:
            raise serializers.ValidationError("Payment currency must match order currency.")

        # amount basic sanity
        if Decimal(attrs["amount"]) <= 0:
            raise serializers.ValidationError({"amount": "Amount must be positive."})

        attrs["__order"] = order
        return attrs

    def create(self, validated):
        order = validated["__order"]
        transaction_id = validated.get("transaction_id") or None
        payment = Payment.objects.create(
            order=order,
            payment_method=validated["payment_method"],
            payment_provider=validated.get("payment_provider") or None,
            transaction_id=transaction_id,
            amount=validated["amount"],
            currency=validated["currency"],
            status="Pending",
        )
        return payment


class PaymentConfirmSerializer(serializers.Serializer):
    """Admin/webhook confirm by payment_id or transaction_id."""
    payment_id = serializers.IntegerField(required=False)
    transaction_id = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=["Completed", "Failed", "Refunded", "Partially Refunded"])
    gateway_response = serializers.JSONField(required=False)

    def validate(self, attrs):
        pid = attrs.get("payment_id")
        tx = attrs.get("transaction_id")
        if not pid and not tx:
            raise serializers.ValidationError("Provide payment_id or transaction_id.")
        return attrs
