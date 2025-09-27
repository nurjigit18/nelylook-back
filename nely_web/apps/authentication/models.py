# authentication/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    id = None
    user_id = models.AutoField(primary_key=True)

    username = None
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name  = models.CharField(max_length=100, blank=True, null=True)
    phone      = models.CharField(max_length=20, blank=True, null=True)
    role       = models.CharField(max_length=20, default="customer")

    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Explicitly define the many-to-many relationships with custom db_table names
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="user_set",
        related_query_name="user",
        db_table='users_groups'  # This creates the table Django is looking for
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="user_set",
        related_query_name="user",
        db_table='users_user_permissions'  # Custom table name for user permissions
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # no username

    objects = UserManager()  # <-- IMPORTANT

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
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'user_addresses'
    
