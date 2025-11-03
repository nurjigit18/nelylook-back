# apps/catalog/management/commands/sync_product_colors.py
"""
Management command to validate and fix product color assignments

Usage:
    python manage.py sync_product_colors           # Check all products
    python manage.py sync_product_colors --fix     # Fix issues automatically
    python manage.py sync_product_colors --product=123  # Check specific product
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from apps.catalog.models import Product, ProductVariant, ProductImage, Color


class Command(BaseCommand):
    help = 'Validate and sync product colors between variants and images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix issues',
        )
        parser.add_argument(
            '--product',
            type=int,
            help='Check specific product by ID',
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        product_id = options.get('product')
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Product Color Validation Tool'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        # Get products to check
        if product_id:
            products = Product.objects.filter(product_id=product_id)
            if not products.exists():
                self.stdout.write(self.style.ERROR(f'Product {product_id} not found!'))
                return
        else:
            products = Product.objects.filter(status='active')
        
        total_issues = 0
        total_fixed = 0
        
        for product in products:
            issues = self.check_product(product, fix_mode)
            total_issues += issues['total']
            total_fixed += issues['fixed']
        
        # Summary
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('SUMMARY'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(f'Total products checked: {products.count()}')
        self.stdout.write(f'Total issues found: {total_issues}')
        
        if fix_mode:
            self.stdout.write(self.style.SUCCESS(f'Total issues fixed: {total_fixed}'))
        else:
            self.stdout.write(self.style.WARNING('Run with --fix to automatically fix issues'))

    def check_product(self, product, fix_mode):
        """Check a single product for color issues"""
        issues = {'total': 0, 'fixed': 0}
        has_issues = False
        
        # Get colors from variants
        variant_colors = set(
            ProductVariant.objects.filter(product=product, color__isnull=False)
            .values_list('color_id', flat=True)
        )
        
        # Get colors from images
        image_colors = set(
            ProductImage.objects.filter(product=product, color__isnull=False)
            .values_list('color_id', flat=True)
        )
        
        # Check for images without matching variants
        orphan_colors = image_colors - variant_colors
        
        if orphan_colors:
            has_issues = True
            issues['total'] += len(orphan_colors)
            
            self.stdout.write(f'\n❌ Product: {product.product_name} (ID: {product.product_id})')
            self.stdout.write(self.style.ERROR(
                f'   Found {len(orphan_colors)} image(s) with colors not in variants:'
            ))
            
            for color_id in orphan_colors:
                color = Color.objects.get(color_id=color_id)
                image_count = ProductImage.objects.filter(
                    product=product, color_id=color_id
                ).count()
                
                self.stdout.write(f'   - Color: {color.color_name} ({image_count} images)')
                
                if fix_mode:
                    # Option 1: Remove orphan images
                    # ProductImage.objects.filter(product=product, color_id=color_id).delete()
                    
                    # Option 2: Create variant for this color (safer)
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠️  Cannot auto-fix: Please manually create variant or remove images'
                    ))
                    # We can't auto-create variants because we don't know which size to use
        
        # Check for variants without images
        missing_image_colors = variant_colors - image_colors
        
        if missing_image_colors:
            has_issues = True
            issues['total'] += len(missing_image_colors)
            
            if not orphan_colors:  # Only print header if not already printed
                self.stdout.write(f'\n⚠️  Product: {product.product_name} (ID: {product.product_id})')
            
            self.stdout.write(self.style.WARNING(
                f'   Found {len(missing_image_colors)} variant color(s) without images:'
            ))
            
            for color_id in missing_image_colors:
                color = Color.objects.get(color_id=color_id)
                self.stdout.write(f'   - Color: {color.color_name} (missing images)')
        
        # Check for multiple primary images per color
        primary_issues = (
            ProductImage.objects.filter(product=product, is_primary=True)
            .values('color')
            .annotate(count=Count('image_id'))
            .filter(count__gt=1)
        )
        
        if primary_issues:
            has_issues = True
            issues['total'] += primary_issues.count()
            
            if not (orphan_colors or missing_image_colors):
                self.stdout.write(f'\n⚠️  Product: {product.product_name} (ID: {product.product_id})')
            
            self.stdout.write(self.style.ERROR(
                f'   Found colors with multiple primary images:'
            ))
            
            for issue in primary_issues:
                color = Color.objects.get(color_id=issue['color'])
                self.stdout.write(f'   - Color: {color.color_name} ({issue["count"]} primary images)')
                
                if fix_mode:
                    # Fix: Keep first primary, unset others
                    images = ProductImage.objects.filter(
                        product=product, 
                        color=color, 
                        is_primary=True
                    ).order_by('image_id')
                    
                    for img in images[1:]:
                        img.is_primary = False
                        img.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✓ Fixed: Set only first image as primary'
                    ))
                    issues['fixed'] += 1
        
        # Check for colors without primary image
        no_primary = variant_colors & image_colors  # Colors that have both variants and images
        
        for color_id in no_primary:
            has_primary = ProductImage.objects.filter(
                product=product,
                color_id=color_id,
                is_primary=True
            ).exists()
            
            if not has_primary:
                color = Color.objects.get(color_id=color_id)
                image_count = ProductImage.objects.filter(
                    product=product, color_id=color_id
                ).count()
                
                if image_count > 0:  # Only report if there are images
                    has_issues = True
                    issues['total'] += 1
                    
                    if not (orphan_colors or missing_image_colors or primary_issues):
                        self.stdout.write(f'\n⚠️  Product: {product.product_name} (ID: {product.product_id})')
                    
                    self.stdout.write(self.style.WARNING(
                        f'   Color: {color.color_name} has no primary image'
                    ))
                    
                    if fix_mode:
                        # Set first image as primary
                        first_image = ProductImage.objects.filter(
                            product=product, color=color
                        ).order_by('display_order', 'image_id').first()
                        
                        if first_image:
                            first_image.is_primary = True
                            first_image.save()
                            self.stdout.write(self.style.SUCCESS(
                                f'   ✓ Fixed: Set first image as primary'
                            ))
                            issues['fixed'] += 1
        
        if has_issues:
            self.stdout.write('')  # Blank line between products
        
        return issues