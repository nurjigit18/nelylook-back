from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    email = models.CharField(unique=True, max_length=255)
    password_hash = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, null=True, db_comment='admin, manager, customer', default='customer')
    is_active = models.BooleanField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'users'
        
        
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