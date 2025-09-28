from django.db import models

# Create your models here.
class ProductViews(models.Model):
    view_id = models.AutoField(primary_key=True)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    user    = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True, null=True, db_comment='For guest users')
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    viewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'product_views'
        db_table_comment = 'Track product views for analytics and recommendations'
        
class AdminLogs(models.Model):
    log_id = models.AutoField(primary_key=True)
    admin  = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100, blank=True, null=True, db_comment='CREATE_PRODUCT, UPDATE_ORDER, DELETE_USER')
    table_name = models.CharField(max_length=50, blank=True, null=True)
    record_id = models.IntegerField(blank=True, null=True)
    old_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    new_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'admin_logs'
        
class Currency(models.Model):
    currency_id = models.AutoField(primary_key=True)
    currency_code = models.CharField(unique=True, max_length=3, db_comment='KGS, USD, EUR, RUB')
    currency_name = models.CharField(max_length=50, db_comment='Kyrgyz Som, US Dollar')
    currency_symbol = models.CharField(max_length=5, blank=True, null=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, db_comment='Rate to base currency')
    is_base_currency = models.BooleanField(blank=True, null=True, db_comment='Only one base currency')
    is_active = models.BooleanField(blank=True, null=True)
    decimal_places = models.IntegerField(blank=True, null=True, db_comment='Number of decimal places')
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'currencies'
        verbose_name_plural = 'Валюты'
        db_table_comment = 'Base currency (KGS), others calculated via exchange rate'