# apps/catalog/management/commands/fix_category_slugs.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from unidecode import unidecode
from apps.catalog.models import Category


class Command(BaseCommand):
    help = 'Generate proper slugs for all categories'

    def handle(self, *args, **options):
        for cat in Category.objects.all():
            # Transliterate Cyrillic to Latin, then slugify
            transliterated = unidecode(cat.category_name)
            base_slug = slugify(transliterated)
            slug = base_slug
            counter = 1
            
            # Ensure unique
            while Category.objects.filter(category_slug=slug).exclude(category_id=cat.category_id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            cat.category_slug = slug
            cat.save(update_fields=['category_slug'])
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {cat.category_name} → {slug}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Updated {Category.objects.count()} categories')
        )