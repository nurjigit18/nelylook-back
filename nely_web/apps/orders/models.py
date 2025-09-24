from django.db import models
from django.utils import timezone
from django.conf import settings

class DeliveryZones(models.Model):
    zone_id = models.AutoField(primary_key=True)
    zone_name = models.CharField(max_length=100, unique=True)
    cities = models.TextField(blank=True, null=True)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time_days = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'delivery_zones'
        verbose_name = 'Delivery Zone'
        verbose_name_plural = 'Delivery Zones'

    def __str__(self):
        return self.zone_name

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
    )
    guest_email = models.EmailField(blank=True, null=True)

    order_date = models.DateTimeField(auto_now_add=True)
    order_status = models.CharField(max_length=20, default='Pending')
    payment_status = models.CharField(max_length=20, default='Pending')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    shipping_address = models.ForeignKey(
        'authentication.UserAddress',
        related_name='shipping_orders',
        on_delete=models.PROTECT,
        null=True, blank=True
    )
    billing_address = models.ForeignKey(
        'authentication.UserAddress',
        related_name='billing_orders',
        on_delete=models.PROTECT,
        null=True, blank=True
    )

    delivery_date = models.DateField(blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    fx_rate_to_base = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)
    fx_source = models.CharField(max_length=50, blank=True, null=True)

    subtotal_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.PROTECT,
    )

    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['order_date']),
            models.Index(fields=['order_status']),
        ]
        constraints = [
            models.CheckConstraint(
                name='order_has_user_or_guest_email',
                check=(models.Q(user__isnull=False) | models.Q(guest_email__isnull=False)),
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order {self.order_number}'

class OrderItems(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    product_name = models.CharField(max_length=255, blank=True, null=True)
    variant_details = models.CharField(max_length=255, blank=True, null=True)

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['variant']),
        ]

    def __str__(self):
        return f'OrderItem {self.order_item_id} (order={self.order.order_number})'
