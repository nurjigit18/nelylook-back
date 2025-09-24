from django.db import models
from django.conf import settings
from django.utils import timezone

class ShoppingCart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,  # Changed from SET_NULL to CASCADE
        null=True, blank=True, 
        related_name='carts'
    )
    session_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_cart'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        who = str(self.user) if self.user else self.session_id or 'anonymous'
        return f'Cart {self.cart_id} ({who})'

class CartItems(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    cart = models.ForeignKey(
        ShoppingCart, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant', 
        on_delete=models.CASCADE,  # Changed from PROTECT to CASCADE
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = [['cart', 'variant']]
    
    def __str__(self):
        return f'CartItem {self.cart_item_id} ({self.variant})'
