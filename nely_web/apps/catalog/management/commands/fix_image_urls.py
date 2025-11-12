from django.core.management.base import BaseCommand
from apps.catalog.models import ProductImage
from apps.core.storage import SupabaseStorage

class Command(BaseCommand):
    help = 'Fix image URLs for existing ProductImages'

    def handle(self, *args, **options):
        storage = SupabaseStorage()
        images = ProductImage.objects.all()
        
        fixed_count = 0
        for img in images:
            # If image_file exists but image_url is empty or incorrect
            if img.image_file and (not img.image_url or 'products/' in img.image_url):
                filename = img.image_file.name
                
                # Remove 'products/' prefix if present
                if '/' in filename:
                    filename = filename.split('/')[-1]
                
                # Generate correct URL
                img.image_url = storage.url(filename)
                img.save(update_fields=['image_url'])
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Fixed: {img.product.product_name} - {img.color.color_name if img.color else "No color"}')
                )
                fixed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Fixed {fixed_count} images')
        )
