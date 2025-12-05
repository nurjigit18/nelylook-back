# apps/catalog/admin_site.py
"""
Custom admin site with user-friendly dashboard for content managers
"""
from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.urls import path
from django.db.models import Count, Q
from django.utils.html import format_html


class NelyLookAdminSite(AdminSite):
    """
    Custom admin site with a user-friendly dashboard
    """
    site_header = "NelyLook - Управление магазином"
    site_title = "NelyLook Admin"
    index_title = "Добро пожаловать в панель управления"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='custom_dashboard'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        """
        Custom index page with quick stats and links
        """
        from apps.catalog.models import Product, Collection, ProductVariant

        # Get statistics
        stats = {
            'total_products': Product.objects.count(),
            'active_products': Product.objects.filter(status='active').count(),
            'low_stock_variants': ProductVariant.objects.filter(
                stock_quantity__lte=5,
                stock_quantity__gt=0
            ).count(),
            'out_of_stock': ProductVariant.objects.filter(stock_quantity=0).count(),
            'total_collections': Collection.objects.filter(is_active=True).count(),
            'featured_products': Product.objects.filter(is_featured=True).count(),
            'new_arrivals': Product.objects.filter(is_new_arrival=True).count(),
        }

        # Recent products
        recent_products = Product.objects.select_related('category').order_by('-created_at')[:5]

        # Low stock alerts
        low_stock_items = ProductVariant.objects.filter(
            stock_quantity__lte=5,
            stock_quantity__gt=0
        ).select_related('product', 'color', 'size').order_by('stock_quantity')[:10]

        extra_context = extra_context or {}
        extra_context.update({
            'stats': stats,
            'recent_products': recent_products,
            'low_stock_items': low_stock_items,
            'show_dashboard': True,
        })

        return super().index(request, extra_context)

    def dashboard_view(self, request):
        """
        Detailed dashboard view
        """
        from apps.catalog.models import Product, Collection, ProductVariant

        context = {
            'title': 'Панель управления',
            'site_title': self.site_title,
            'site_header': self.site_header,
        }

        return render(request, 'admin/custom_dashboard.html', context)


# Create instance of custom admin site
admin_site = NelyLookAdminSite(name='nelylook_admin')
