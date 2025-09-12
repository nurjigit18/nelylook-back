# apps/analytics/serializers.py
from rest_framework import serializers
from .models import ProductViews, AdminLogs, Currency

class ProductViewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductViews
        fields = "__all__"

class AdminLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminLogs
        fields = "__all__"

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"
