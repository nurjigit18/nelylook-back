from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
class ShoppingCart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')
    session_id = models.CharField(max_length=255, blank=True, null=True, db_comment='For guest users')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'shopping_cart'
        indexes = [
            models.Index(fields=['user', 'session_id']),
        ]

    def __str__(self):
        who = self.user_id or self.session_id or 'anonymous'
        return f'Cart {self.cart_id} ({who})'

class CartItems(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT, related_name='cart_items')
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_comment='Price when added to cart')
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'cart_items'
        constraints = [
            models.UniqueConstraint(fields=['cart', 'variant'], name='uniq_cart_variant'),
        ]
    def __str__(self):
        return f'CartItem {self.cart_item_id} (cart={self.cart_id}, variant={self.variant_id})'