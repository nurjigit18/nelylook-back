# apps/payments/models.py
from django.db import models

class FxRate(models.Model):
    fx_rate_id = models.AutoField(primary_key=True)
    base_currency  = models.ForeignKey(
        'core.Currency', on_delete=models.CASCADE, related_name='fx_base_rates'
    )
    quote_currency = models.ForeignKey(
        'core.Currency', on_delete=models.CASCADE, related_name='fx_quote_rates'
    )
    rate = models.DecimalField(max_digits=18, decimal_places=8)  # 1 base = rate quote
    source = models.CharField(max_length=50, default='manual', blank=True)
    as_of = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fx_rates"
        indexes = [
            models.Index(fields=['base_currency', 'quote_currency', 'as_of'], name='idx_fx_pair_time'),
        ]

    def __str__(self):
        return f"{self.base_currency}->{self.quote_currency} @ {self.rate}"


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='payments')
    payment_method = models.CharField(max_length=50)  # e.g. FreedomPay KG, COD
    payment_provider = models.CharField(max_length=50, blank=True, null=True, help_text='FreedomPay KG')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey('core.Currency', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, blank=True, null=True)  # Pending, Completed, etc.
    gateway_response = models.JSONField(blank=True, null=True)       # store raw gateway JSON
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment {self.payment_id} for order {self.order_id}"
