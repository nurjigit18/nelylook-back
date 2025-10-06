# apps/catalog/filters.py
import django_filters
from .models import Product, ProductVariant


class ProductFilter(django_filters.FilterSet):
    """
    Advanced filtering for products.
    
    Usage examples:
    - /products/?category=1
    - /products/?season=summer
    - /products/?min_price=100&max_price=500
    - /products/?color=1&size=2
    - /products/?in_stock=true
    """
    
    # Category filter
    category = django_filters.NumberFilter(field_name='category__category_id')
    
    # Clothing type filter
    clothing_type = django_filters.NumberFilter(field_name='clothing_type__type_id')
    
    # Season filter
    season = django_filters.ChoiceFilter(choices=Product._meta.get_field('season').choices)
    
    # Price range filters
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')
    
    # Boolean filters
    is_featured = django_filters.BooleanFilter()
    is_new_arrival = django_filters.BooleanFilter()
    is_bestseller = django_filters.BooleanFilter()
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    # Color filter (through variants)
    color = django_filters.NumberFilter(method='filter_color')
    
    # Size filter (through variants)
    size = django_filters.NumberFilter(method='filter_size')
    
    # Collection filter
    collection = django_filters.NumberFilter(method='filter_collection')
    
    class Meta:
        model = Product
        fields = [
            'category', 'clothing_type', 'season',
            'min_price', 'max_price',
            'is_featured', 'is_new_arrival', 'is_bestseller',
            'on_sale', 'in_stock', 'color', 'size', 'collection'
        ]
    
    def filter_on_sale(self, queryset, name, value):
        """Filter products that have a sale price."""
        if value:
            return queryset.filter(sale_price__isnull=False)
        return queryset.filter(sale_price__isnull=True)
    
    def filter_in_stock(self, queryset, name, value):
        """Filter products that are in stock."""
        if value:
            return queryset.filter(stock_quantity__gt=0, status='active')
        return queryset
    
    def filter_color(self, queryset, name, value):
        """Filter products that have variants in the specified color."""
        return queryset.filter(
            variants__color_id=value,
            variants__status='active'
        ).distinct()
    
    def filter_size(self, queryset, name, value):
        """Filter products that have variants in the specified size."""
        return queryset.filter(
            variants__size_id=value,
            variants__status='active'
        ).distinct()
    
    def filter_collection(self, queryset, name, value):
        """Filter products that belong to a specific collection."""
        return queryset.filter(
            collection_memberships__collection_id=value
        ).distinct()