from django.db import models
from django.conf import settings
from django.utils import timezone

class Wishlists(models.Model):
    id = models.AutoField(primary_key=True)

    # who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,           # delete wishlist rows when user is deleted
        related_name='wishlist_items',
        null=True, blank=True
    )
    session_id = models.CharField(         # for guests
        max_length=255, null=True, blank=True
    )

    # what
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        related_name='wishlisted_in',
        null=True, blank=True,   # <- TEMPORARY
    )

    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # Default table name is fine, or add db_table='wishlist' if you want
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
            models.Index(fields=['variant']),
        ]
        constraints = [
            # require either a user OR a session_id
            models.CheckConstraint(
                name='wishlist_has_user_or_session',
                check=(models.Q(user__isnull=False) | models.Q(session_id__isnull=False)),
            ),
            # enforce uniqueness per owner
            models.UniqueConstraint(
                fields=['user', 'variant'],
                name='uniq_user_variant',
                condition=models.Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['session_id', 'variant'],
                name='uniq_session_variant',
                condition=models.Q(session_id__isnull=False),
            ),
        ]

    def __str__(self):
        who = self.user_id or self.session_id or 'anon'
        return f'WishlistItem {self.id} ({who} → variant {self.variant_id})'