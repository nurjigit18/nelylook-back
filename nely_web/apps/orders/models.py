from django.db import models
from django.utils import timezone

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
    )
    guest_email = models.EmailField(blank=True, null=True, help_text='For guest checkout')

    order_date = models.DateTimeField(default=timezone.now)
    order_status = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Pending, Confirmed, Processing, Shipped, Delivered, Cancelled, Returned'
    )
    payment_status = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Pending, Paid, Failed, Refunded, Partially Refunded'
    )
    payment_method = models.CharField(max_length=50, blank=True, null=True, help_text='FreedomPay KG, Cash on Delivery')
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

    fx_rate_to_base = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, help_text='quote->base at purchase time')
    fx_source = models.CharField(max_length=50, blank=True, null=True)

    subtotal_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.PROTECT,  # don’t allow deleting a currency used by orders
        help_text='Order currency'
    )

    admin_notes = models.TextField(blank=True, null=True, help_text='Internal notes for managers')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Let Django use the default table name (orders_order) to avoid cross-app confusion.
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['order_date']),
            models.Index(fields=['order_status']),
        ]
        constraints = [
            # Either a registered user or a guest email must be present
            models.CheckConstraint(
                name='order_has_user_or_guest_email',
                check=(models.Q(user__isnull=False) | models.Q(guest_email__isnull=False)),
            ),
        ]

    def __str__(self):
        return f'Order {self.order_number}'


class OrderItems(models.Model):
    order_item_id = models.AutoField(primary_key=True)

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,              # delete items when the order is deleted
        related_name='items'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,              # variants in orders must not disappear
        related_name='order_items'
    )

    product_name = models.CharField(max_length=255, blank=True, null=True, help_text='Snapshot at time of order')
    variant_details = models.CharField(max_length=255, blank=True, null=True, help_text='Size, Color details snapshot')

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # Default table name (orders_orderitems) is fine and predictable
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['variant']),
        ]

    def __str__(self):
        return f'OrderItem {self.order_item_id} (order={self.order_id})'


class DeliveryZones(models.Model):
    zone_id = models.AutoField(primary_key=True)
    zone_name = models.CharField(max_length=100, unique=True)
    cities = models.TextField(blank=True, null=True, help_text='Comma-separated city names')
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time_days = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        # If you truly manage this table outside Django, flip to managed=False.
        db_table = 'delivery_zones'
        managed = True
        verbose_name = 'Delivery zone'
        verbose_name_plural = 'Delivery zones'

    def __str__(self):
        return self.zone_name
