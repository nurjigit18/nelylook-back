from django.db import migrations

def set_default_category(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ClothingType = apps.get_model("catalog", "ClothingType")

    # Create or get a safe fallback category.
    # Your 0001 shows fields: category_name, category_path, is_active, display_order, etc.
    default_cat, _ = Category.objects.get_or_create(
        category_name="Uncategorized",
        defaults={
            "category_path": "uncategorized",
            "is_active": True,
            "display_order": 0,
        },
    )

    # Backfill any NULL FKs (harmless on a fresh DB)
    ClothingType.objects.filter(category__isnull=True).update(category_id=default_cat.pk)

class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]
    operations = [migrations.RunPython(set_default_category, migrations.RunPython.noop)]
