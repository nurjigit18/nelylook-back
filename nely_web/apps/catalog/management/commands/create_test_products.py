# apps/catalog/management/commands/create_test_products.py
from django.core.management.base import BaseCommand
from apps.catalog.models import (
    Category, ClothingType, Product, ProductVariant, 
    Color, Size, ProductImage
)


class Command(BaseCommand):
    help = 'Creates test products for development'

    def handle(self, *args, **options):
        self.stdout.write('Creating test data...')

        # Create categories
        women_cat, _ = Category.objects.get_or_create(
            category_name='Женская одежда',
            defaults={
                'display_order': 1,
                'is_active': True
            }
        )

        men_cat, _ = Category.objects.get_or_create(
            category_name='Мужская одежда',
            defaults={
                'display_order': 2,
                'is_active': True
            }
        )

        # Create clothing types
        tops, _ = ClothingType.objects.get_or_create(
            type_name='Верх',
            category=women_cat,
            defaults={
                'display_order': 1,
                'is_active': True
            }
        )

        dresses, _ = ClothingType.objects.get_or_create(
            type_name='Платья',
            category=women_cat,
            defaults={
                'display_order': 2,
                'is_active': True
            }
        )

        # Create colors
        black, _ = Color.objects.get_or_create(
            color_name='Черный',
            defaults={
                'color_code': '#000000',
                'color_family': 'dark',
                'is_active': True
            }
        )

        white, _ = Color.objects.get_or_create(
            color_name='Белый',
            defaults={
                'color_code': '#FFFFFF',
                'color_family': 'light',
                'is_active': True
            }
        )

        beige, _ = Color.objects.get_or_create(
            color_name='Бежевый',
            defaults={
                'color_code': '#F5F5DC',
                'color_family': 'neutral',
                'is_active': True
            }
        )

        # Create sizes
        sizes_data = [
            ('XS', 1),
            ('S', 2),
            ('M', 3),
            ('L', 4),
            ('XL', 5),
            ('XXL', 6),
        ]

        size_objects = {}
        for size_name, order in sizes_data:
            size_obj, _ = Size.objects.get_or_create(
                size_name=size_name,
                defaults={
                    'size_category': 'standard',
                    'sort_order': order,
                    'is_active': True
                }
            )
            size_objects[size_name] = size_obj

        # Create products
        products_data = [
            {
                'name': 'Минималистичная открытая рубашка',
                'slug': 'minimalist-open-shirt',
                'category': women_cat,
                'clothing_type': tops,
                'price': 2999,
                'sale_price': 2499,
                'description': 'Элегантная открытая рубашка в минималистичном стиле',
                'season': 'all',
            },
            {
                'name': 'Повседневный топ с завязками',
                'slug': 'casual-drawstring-top',
                'category': women_cat,
                'clothing_type': tops,
                'price': 1999,
                'description': 'Удобный топ с завязками для повседневной носки',
                'season': 'summer',
            },
            {
                'name': 'Классическое платье-футболка',
                'slug': 'classic-tshirt-dress',
                'category': women_cat,
                'clothing_type': dresses,
                'price': 3499,
                'sale_price': 2799,
                'description': 'Комфортное платье-футболка для любого случая',
                'season': 'spring',
            },
            {
                'name': 'Шелковая блузка',
                'slug': 'silk-blouse',
                'category': women_cat,
                'clothing_type': tops,
                'price': 4999,
                'description': 'Роскошная шелковая блузка премиум качества',
                'season': 'all',
            },
            {
                'name': 'Льняная рубашка оверсайз',
                'slug': 'linen-oversized-shirt',
                'category': women_cat,
                'clothing_type': tops,
                'price': 3299,
                'description': 'Свободная льняная рубашка в стиле оверсайз',
                'season': 'summer',
            },
        ]

        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                slug=prod_data['slug'],
                defaults={
                    'product_name': prod_data['name'],
                    'category': prod_data['category'],
                    'clothing_type': prod_data['clothing_type'],
                    'base_price': prod_data['price'],
                    'sale_price': prod_data.get('sale_price'),
                    'description': prod_data['description'],
                    'season': prod_data['season'],
                    'status': 'active',
                    'is_featured': True,
                    'is_new_arrival': True,
                }
            )

            if created:
                self.stdout.write(f'  ✓ Created product: {product.product_name}')

                # Create variants for each color and size
                for color in [black, white, beige]:
                    for size_name in ['S', 'M', 'L', 'XL']:
                        variant, v_created = ProductVariant.objects.get_or_create(
                            product=product,
                            color=color,
                            size=size_objects[size_name],
                            defaults={
                                'stock_quantity': 10,
                                'status': 'active'
                            }
                        )
                        if v_created:
                            # Update product stock
                            product.stock_quantity += 10
                            product.save(update_fields=['stock_quantity'])

        self.stdout.write(self.style.SUCCESS('✓ Test data created successfully!'))
        self.stdout.write(f'Total products: {Product.objects.count()}')
        self.stdout.write(f'Total variants: {ProductVariant.objects.count()}')