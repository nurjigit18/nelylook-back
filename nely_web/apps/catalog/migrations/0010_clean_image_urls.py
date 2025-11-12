from django.db import migrations

def clean_image_urls(apps, schema_editor):
    """Remove trailing ? from existing image URLs"""
    ProductImage = apps.get_model('catalog', 'ProductImage')
    
    images_to_update = []
    for image in ProductImage.objects.all():
        if image.image_url and image.image_url.endswith('?'):
            image.image_url = image.image_url.rstrip('?')
            images_to_update.append(image)
    
    if images_to_update:
        ProductImage.objects.bulk_update(images_to_update, ['image_url'])
        print(f"✅ Cleaned {len(images_to_update)} image URLs")

class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_alter_product_clothing_type'),  # Replace with your last migration
    ]

    operations = [
        migrations.RunPython(clean_image_urls, migrations.RunPython.noop),
    ]
