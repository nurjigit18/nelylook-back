# apps/catalog/filters.py
import django_filters
from django.db.models import Q
from .models import Product, Category, ClothingType, Color, Size


class ProductFilter(django_filters.FilterSet):
    """
    Advanced filtering for products.
    
    Usage examples:
    - /products/?category=1
    - /products/?min_price=100&max_price=500
    - /products/?color=1,2,3
    - /products/?size=S,M,L
    - /products/?season=summer
    - /products/?on_sale=true
    """
    
    # Category filters
    category = django_filters.ModelMultipleChoiceFilter(
        field_name='category',
        queryset=Category.objects.filter(is_active=True),
        label='Category IDs'
    )
    
    # Clothing type filter
    clothing_type = django_filters.ModelMultipleChoiceFilter(
        field_name='clothing_type',
        queryset=ClothingType.objects.filter(is_active=True),
        label='Clothing Type IDs'
    )
    
    # Price range filters
    min_price = django_filters.NumberFilter(
        field_name='base_price',
        lookup_expr='gte',
        label='Minimum price'
    )
    max_price = django_filters.NumberFilter(
        field_name='base_price',
        lookup_expr='lte',
        label='Maximum price'
    )
    
    # Color filter (filters by variants)
    color = django_filters.ModelMultipleChoiceFilter(
        field_name='variants__color',
        queryset=Color.objects.filter(is_active=True),
        label='Color IDs',
        distinct=True
    )
    
    # Size filter (filters by variants)
    size = django_filters.ModelMultipleChoiceFilter(
        field_name='variants__size',
        queryset=Size.objects.filter(is_active=True),
        label='Size IDs',
        distinct=True
    )
    
    # Season filter
    season = django_filters.MultipleChoiceFilter(
        field_name='season',
        choices=[(choice[0], choice[1]) for choice in Product._meta.get_field('season').choices],
        label='Season'
    )
    
    # Boolean filters
    on_sale = django_filters.BooleanFilter(
        method='filter_on_sale',
        label='On sale (has sale_price)'
    )
    featured = django_filters.BooleanFilter(
        field_name='is_featured',
        label='Featured products'
    )
    new_arrival = django_filters.BooleanFilter(
        field_name='is_new_arrival',
        label='New arrivals'
    )
    bestseller = django_filters.BooleanFilter(
        field_name='is_bestseller',
        label='Bestsellers'
    )
    
    # Stock availability
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        label='In stock'
    )
    
    class Meta:
        model = Product
        fields = {
            'status': ['exact'],
        }
    
    def filter_on_sale(self, queryset, name, value):
        """Filter products that have a sale price."""
        if value:
            return queryset.filter(sale_price__isnull=False).exclude(sale_price=0)
        return queryset.filter(Q(sale_price__isnull=True) | Q(sale_price=0))
    
    def filter_in_stock(self, queryset, name, value):
        """Filter products that have stock available."""
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)