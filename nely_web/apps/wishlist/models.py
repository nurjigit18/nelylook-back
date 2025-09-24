from django.db import models
from django.conf import settings
from django.utils import timezone

class Wishlists(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        null=True, blank=True
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)

    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='wishlisted_in',
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlists'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
            models.Index(fields=['variant']),
        ]
        constraints = [
            models.CheckConstraint(
                name='wishlist_has_user_or_session',
                check=(models.Q(user__isnull=False) | models.Q(session_id__isnull=False)),
            ),
            models.UniqueConstraint(
                fields=['user', 'variant'],
                name='uniq_user_variant_wishlist',
                condition=models.Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['session_id', 'variant'],
                name='uniq_session_variant_wishlist',
                condition=models.Q(session_id__isnull=False),
            ),
        ]

    def __str__(self):
        who = str(self.user) if self.user else self.session_id or 'anon'
        return f'WishlistItem {self.id} ({who} → {self.variant})'
