"""
Django management command to fix existing ProductImage URLs

Run this command to update all existing product image URLs to include the proper path:
python manage.py fix_product_image_urls

This will update URLs like:
  https://.../product-images/3_pink.JPG
to:
  https://.../product-images/products/3_pink.JPG
"""

from django.core.management.base import BaseCommand
from apps.catalog.models import ProductImage


class Command(BaseCommand):
    help = 'Fix product image URLs to include the products/ path'

    def handle(self, *args, **options):
        images = ProductImage.objects.all()
        fixed_count = 0
        
        self.stdout.write(self.style.WARNING(f'Found {images.count()} product images to check...'))
        
        for img in images:
            if img.image_file and img.image_url:
                # Get the correct URL from storage
                correct_url = img.image_file.storage.url(img.image_file.name)
                
                if img.image_url != correct_url:
                    self.stdout.write(
                        f'Fixing image {img.image_id}:\n'
                        f'  Old: {img.image_url}\n'
                        f'  New: {correct_url}'
                    )
                    img.image_url = correct_url
                    img.save(update_fields=['image_url'])
                    fixed_count += 1
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully fixed {fixed_count} image URLs!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ All image URLs are already correct!')
            )