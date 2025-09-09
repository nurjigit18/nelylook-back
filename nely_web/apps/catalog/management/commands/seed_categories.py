# apps/catalog/management/commands/seed_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.catalog.models import Category

CATEGORIES = [
    "Tops", "Bottoms", "Dresses", "Outerwear",
    "Knitwear", "Activewear", "Loungewear", "Accessories",
]

class Command(BaseCommand):
    help = "Seed base categories only (no clothing types). Safe to run multiple times."

    def handle(self, *args, **options):
        # Always ensure a fallback
        Category.objects.get_or_create(
            category_name="Uncategorized",
            defaults=dict(category_path="uncategorized", display_order=9999, is_active=True),
        )

        order = 10
        for name in CATEGORIES:
            Category.objects.get_or_create(
                category_name=name,
                defaults=dict(category_path=slugify(name), display_order=order, is_active=True),
            )
            order += 10

        self.stdout.write(self.style.SUCCESS("✅ Categories seeded (idempotent)."))
