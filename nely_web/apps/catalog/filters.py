# apps/catalog/filters.py
import django_filters
from django.db.models import Q
from .models import Product, Category, ClothingType, Color, Size


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    """Accepts comma-separated numbers: ?category=1,2,3"""
    pass


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """For season etc."""
    pass


class ProductFilter(django_filters.FilterSet):
    # Category ids
    category = NumberInFilter(
        field_name='category_id',  # or 'category' if FK name is category
        lookup_expr='in',
        label='Category IDs'
    )

    clothing_type = NumberInFilter(
        field_name='clothing_type_id',
        lookup_expr='in',
        label='Clothing Type IDs'
    )

    # Price
    min_price = django_filters.NumberFilter(
        field_name='base_price',
        lookup_expr='gte'
    )
    max_price = django_filters.NumberFilter(
        field_name='base_price',
        lookup_expr='lte'
    )

    # Colors from variants
    color = NumberInFilter(
        field_name='variants__color_id',
        lookup_expr='in',
        label='Color IDs'
    )

    # Sizes from variants
    size = NumberInFilter(
        field_name='variants__size_id',
        lookup_expr='in',
        label='Size IDs'
    )

    # Season (enum) – will accept ?season=summer,winter
    season = CharInFilter(
        field_name='season',
        lookup_expr='in'
    )

    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    featured = django_filters.BooleanFilter(field_name='is_featured')
    new_arrival = django_filters.BooleanFilter(field_name='is_new_arrival')
    bestseller = django_filters.BooleanFilter(field_name='is_bestseller')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')

    class Meta:
        model = Product
        fields = ['status']

    def filter_on_sale(self, queryset, name, value):
        if value:
            # products that actually have sale_price
            return queryset.filter(sale_price__isnull=False).exclude(sale_price=0)
        # if ?on_sale=false – just return queryset unchanged or opposite, your choice
        return queryset

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset
