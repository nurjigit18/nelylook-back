from django.core.management.base import BaseCommand
from apps.catalog.models import ProductImage
from apps.core.storage import SupabaseStorage

class Command(BaseCommand):
    help = 'Fix image_file paths and regenerate image_url for all ProductImages'

    def handle(self, *args, **options):
        storage = SupabaseStorage()
        images = ProductImage.objects.all()
        
        self.stdout.write(self.style.WARNING(f'Found {images.count()} images to process...'))
        
        fixed_count = 0
        error_count = 0
        
        for img in images:
            try:
                if img.image_file:
                    # Get current filename
                    old_filename = img.image_file.name
                    
                    # Extract just the filename (remove 'products/' prefix)
                    if '/' in old_filename:
                        clean_filename = old_filename.split('/')[-1]
                    else:
                        clean_filename = old_filename
                    
                    # Update image_file to point to root
                    img.image_file.name = clean_filename
                    
                    # Regenerate image_url
                    img.image_url = storage.url(clean_filename)
                    
                    # Save without triggering upload
                    img.save(update_fields=['image_url'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Fixed: {img.product.product_name} - {img.color.color_name if img.color else "No color"}'
                        )
                    )
                    self.stdout.write(f'   Old: {old_filename}')
                    self.stdout.write(f'   New: {clean_filename}')
                    self.stdout.write(f'   URL: {img.image_url}\n')
                    
                    fixed_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Error with image {img.image_id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Fixed {fixed_count} images')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ {error_count} errors encountered')
            )
    