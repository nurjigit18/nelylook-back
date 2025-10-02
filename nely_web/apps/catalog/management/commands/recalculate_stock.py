# apps/catalog/management/commands/recalculate_stock.py
from django.core.management.base import BaseCommand
from apps.catalog.models import Product

class Command(BaseCommand):
    help = 'Recalculate stock_quantity for all products based on their variants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=int,
            help='Recalculate stock for a specific product ID only',
        )

    def handle(self, *args, **options):
        product_id = options.get('product_id')
        
        if product_id:
            try:
                product = Product.objects.get(product_id=product_id)
                old_stock = product.stock_quantity
                product.update_stock_quantity()
                product.save(update_fields=['stock_quantity', 'status'])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Product {product_id} ({product.product_name}): '
                        f'{old_stock} → {product.stock_quantity}'
                    )
                )
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Product {product_id} not found')
                )
                return
        else:
            products = Product.objects.all()
            total = products.count()
            updated = 0
            
            self.stdout.write(f'Recalculating stock for {total} products...\n')
            
            for product in products:
                old_stock = product.stock_quantity
                product.update_stock_quantity()
                
                if old_stock != product.stock_quantity:
                    product.save(update_fields=['stock_quantity', 'status'])
                    updated += 1
                    
                    self.stdout.write(
                        f'  • {product.product_code} ({product.product_name}): '
                        f'{old_stock} → {product.stock_quantity}'
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Completed! Updated {updated} out of {total} products.'
                )
            )