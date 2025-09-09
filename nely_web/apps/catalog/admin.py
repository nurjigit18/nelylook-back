from django.contrib import admin
from .models import Category, ClothingType

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_id", "category_name", "category_path", "is_active", "display_order", "parent_category")
    search_fields = ("category_name", "category_path")
    list_filter = ("is_active",)
    autocomplete_fields = ("parent_category",)

    # Lock down category creation/deletion to superusers only
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(ClothingType)
class ClothingTypeAdmin(admin.ModelAdmin):
    list_display = ("type_id", "type_name", "category", "is_active", "display_order")
    search_fields = ("type_name", "category__category_name")
    list_filter = ("is_active", "category")
    autocomplete_fields = ("category",)
