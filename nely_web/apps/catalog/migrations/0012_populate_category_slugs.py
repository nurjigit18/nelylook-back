# apps/catalog/migrations/XXXX_populate_category_slugs.py
from django.db import migrations
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    
    for category in Category.objects.all():
        if not category.category_slug:
            base_slug = slugify(category.category_name)
            slug = base_slug
            counter = 1
            
            # Ensure unique slug
            while Category.objects.filter(category_slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category.category_slug = slug
            category.save(update_fields=['category_slug'])
    
    print(f"✅ Populated slugs for {Category.objects.count()} categories")


def reverse_slugs(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    Category.objects.all().update(category_slug='')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_category_category_slug_alter_productimage_image_file'),  # Replace with your previous migration name
    ]

    operations = [
        migrations.RunPython(populate_slugs, reverse_slugs),
    ]