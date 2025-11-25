# apps/catalog/filters.py
import django_filters
from django.db.models import Q, F
from .models import Product

class ProductFilter(django_filters.FilterSet):
    # Category filter - accepts comma-separated IDs
    category = django_filters.CharFilter(method='filter_categories')

    # Color filter - accepts comma-separated IDs
    color = django_filters.CharFilter(method='filter_colors')

    # Size filter - accepts comma-separated IDs
    size = django_filters.CharFilter(method='filter_sizes')

    # Price range
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')

    # Season
    season = django_filters.CharFilter(method='filter_seasons')

    # Search
    search = django_filters.CharFilter(method='filter_search')

    # ✅ NEW: Special filters
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    is_new_arrival = django_filters.BooleanFilter(field_name='is_new_arrival')
    is_bestseller = django_filters.BooleanFilter(field_name='is_bestseller')

    # Collection filter - accepts collection ID
    collection = django_filters.NumberFilter(method='filter_collection')

    class Meta:
        model = Product
        fields = [
            'category', 'color', 'size', 'season',
            'min_price', 'max_price', 'search',
            'on_sale', 'is_featured', 'is_new_arrival', 'is_bestseller',
            'collection'
        ]
    
    def filter_categories(self, queryset, name, value):
        """Filter by multiple categories (comma-separated IDs)"""
        if not value:
            return queryset
        try:
            category_ids = [int(id.strip()) for id in value.split(',') if id.strip().isdigit()]
            if category_ids:
                return queryset.filter(category_id__in=category_ids)
        except (ValueError, AttributeError):
            pass
        return queryset
    
    def filter_colors(self, queryset, name, value):
        """Filter by multiple colors (comma-separated IDs)"""
        if not value:
            return queryset
        try:
            color_ids = [int(id.strip()) for id in value.split(',') if id.strip().isdigit()]
            if color_ids:
                return queryset.filter(variants__color_id__in=color_ids).distinct()
        except (ValueError, AttributeError):
            pass
        return queryset
    
    def filter_sizes(self, queryset, name, value):
        """Filter by multiple sizes (comma-separated IDs)"""
        if not value:
            return queryset
        try:
            size_ids = [int(id.strip()) for id in value.split(',') if id.strip().isdigit()]
            if size_ids:
                return queryset.filter(variants__size_id__in=size_ids).distinct()
        except (ValueError, AttributeError):
            pass
        return queryset
    
    def filter_seasons(self, queryset, name, value):
        """Filter by multiple seasons (comma-separated values)"""
        if not value:
            return queryset
        try:
            seasons = [s.strip() for s in value.split(',') if s.strip()]
            if seasons:
                return queryset.filter(season__in=seasons)
        except AttributeError:
            pass
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search in product name, description, and code"""
        if not value:
            return queryset
        return queryset.filter(
            Q(product_name__icontains=value) |
            Q(description__icontains=value) |
            Q(product_code__icontains=value)
        )
    
    def filter_on_sale(self, queryset, name, value):
        """
        Filter products that are on sale.
        A product is on sale if it has a sale_price that is not null and less than base_price.
        """
        if value:
            # Filter products where sale_price exists and is less than base_price
            return queryset.filter(
                sale_price__isnull=False
            ).exclude(
                sale_price__gte=F('base_price')
            ).exclude(
                sale_price=0
            )
        return queryset

    def filter_collection(self, queryset, name, value):
        """Filter products by collection ID"""
        if not value:
            return queryset
        try:
            return queryset.filter(
                collection_memberships__collection_id=value
            ).distinct()
        except (ValueError, TypeError):
            return queryset