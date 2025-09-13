from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Order, OrderItems, DeliveryZones
from apps.core.models import Currency
from apps.catalog.models import ProductVariant


# ---- Order Items ------------------------------------------------------------

class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItems
        fields = [
            "order_item_id", "variant_id", "product_name", "variant_details",
            "quantity", "unit_price", "discount_amount", "total_price"
        ]
        read_only_fields = ["order_item_id", "product_name", "variant_details",
                            "unit_price", "total_price"]


class OrderItemWriteSerializer(serializers.Serializer):
    """
    Input for each item when creating an order.
    Server computes unit_price/total_price from ProductVariant.
    """
    variant = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"))


# ---- Orders -----------------------------------------------------------------

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_id", "order_number", "user", "guest_email",
            "order_date", "order_status",
            "payment_status", "payment_method", "payment_transaction_id",
            "shipping_address", "billing_address",
            "delivery_date", "tracking_number",
            "fx_rate_to_base", "fx_source",
            "subtotal_base", "shipping_cost_base", "discount_base", "total_amount_base",
            "currency", "currency_id",
            "admin_notes", "created_at", "updated_at",
            "items",
        ]
        read_only_fields = ["order_id", "order_number", "user", "created_at", "updated_at", "subtotal_base", "total_amount_base"]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    For POST /orders/  (guest or authed)
    Accepts nested items and computes money fields server-side.
    """
    items = OrderItemWriteSerializer(many=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())
    shipping_cost_base = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    discount_base = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))

    class Meta:
        model = Order
        fields = [
            "guest_email",
            "shipping_address", "billing_address",
            "payment_method",
            "currency",
            "items",
            "shipping_cost_base", "discount_base",
            "admin_notes",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        guest_email = attrs.get("guest_email")
        if not (user and user.is_authenticated) and not guest_email:
            raise serializers.ValidationError("Either authenticated user or guest_email is required.")
        return attrs

    def _gen_order_number(self) -> str:
        """
        Generate unique human-readable order number, e.g. 20250913-ABC123.
        """
        from django.utils.crypto import get_random_string
        base = timezone.now().strftime("%Y%m%d")
        while True:
            candidate = f"{base}-{get_random_string(6).upper()}"
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate

    @transaction.atomic
    def create(self, validated):
        request = self.context.get("request")
        user = request.user if (request and request.user.is_authenticated) else None

        items_data = validated.pop("items")
        shipping_cost_base = validated.pop("shipping_cost_base", Decimal("0.00"))
        discount_base = validated.pop("discount_base", Decimal("0.00"))

        order = Order.objects.create(
            order_number=self._gen_order_number(),
            user=user,
            order_status="Pending",
            payment_status="Pending",
            **validated
        )

        # Build items from variants; snapshot product/variant names; compute totals
        subtotal = Decimal("0.00")

        for item in items_data:
            variant = ProductVariant.objects.select_related("product").get(pk=item["variant"])
            qty = int(item["quantity"])
            unit_price = Decimal(variant.price)  # trust server DB
            disc = Decimal(item.get("discount_amount", "0.00"))

            product_name = getattr(variant.product, "name", None) or "Product"
            # Adjust to your actual variant attributes
            variant_details = getattr(variant, "sku", None) or getattr(variant, "name", None) or "Variant"

            line_total = unit_price * qty - disc
            if line_total < 0:
                line_total = Decimal("0.00")

            OrderItems.objects.create(
                order=order,
                variant=variant,
                product_name=product_name,
                variant_details=variant_details,
                quantity=qty,
                unit_price=unit_price,
                discount_amount=disc,
                total_price=line_total,
            )
            subtotal += line_total

        order.subtotal_base = subtotal
        order.shipping_cost_base = shipping_cost_base
        order.discount_base = discount_base
        order.total_amount_base = subtotal + shipping_cost_base - discount_base
        if order.total_amount_base < 0:
            order.total_amount_base = Decimal("0.00")
        order.save(update_fields=["subtotal_base", "shipping_cost_base", "discount_base", "total_amount_base"])

        return order


# ---- Delivery Zones ---------------------------------------------------------

class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZones
        fields = "__all__"
