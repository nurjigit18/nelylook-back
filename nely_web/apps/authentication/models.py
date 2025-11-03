# authentication/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.utils import timezone

class Roles(models.TextChoices):
    CUSTOMER = "customer", "клиент"
    MANAGER = "manager", "менеджер"
    ADMIN = "admin", "админ"
    

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

    first_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Имя")
    phone      = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    role       = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CUSTOMER, verbose_name="Роль")

    is_active = models.BooleanField(default=True, verbose_name="Активен")
    email_verified = models.BooleanField(default=False, verbose_name="Почта подтверждена")

    created_at = models.DateTimeField(auto_now_add=True, null=False, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

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
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

class UserAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь")
    address_type = models.CharField(max_length=20, blank=True, null=True, db_comment='Billing, Shipping, Both')
    first_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Имя")
    address_line1 = models.CharField(max_length=255, verbose_name="Адресс 1")
    address_line2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адресс 2")
    city = models.CharField(max_length=100, verbose_name="Город")
    region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Область")
    country = models.CharField(max_length=100, verbose_name="Страна")
    postal_code = models.CharField(max_length=20, verbose_name="Почтовый индекс")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    is_default = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False, verbose_name="Дата создания")

    class Meta:
        db_table = 'user_addresses'
        verbose_name = 'Адрес пользователя'
        verbose_name_plural = 'Адреса пользователей'
    
