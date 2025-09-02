# authentication/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    id = None  # <- block Django from creating implicit "id"
    user_id = models.AutoField(primary_key=True)

    # If you want email-login (recommended):
    username = None
    email = models.EmailField(unique=True)

    # DO NOT keep your own password_hash; Django already has "password"
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name  = models.CharField(max_length=100, blank=True, null=True)
    phone      = models.CharField(max_length=20, blank=True, null=True)
    role       = models.CharField(max_length=20, default="customer", db_comment="admin, manager, customer")

    # Booleans should not be null
    is_active = models.BooleanField(default=True)          # null=False by default
    email_verified = models.BooleanField(default=False)    # null=False

    # Timestamps: give a default now so existing NULLs can be filled
    created_at = models.DateTimeField(default=timezone.now)   # temp default
    updated_at = models.DateTimeField(default=timezone.now)   # temp default

    # Email-based login (optional but consistent)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

class UserAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True)
    address_type = models.CharField(max_length=20, blank=True, null=True, db_comment='Billing, Shipping, Both')
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'user_addresses'