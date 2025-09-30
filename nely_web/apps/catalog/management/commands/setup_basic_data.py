from django.core.management.base import BaseCommand
from django.db import transaction
from apps.catalog.models import Category, ClothingType, Color, Size
from apps.core.models import Currency

class Command(BaseCommand):
    help = 'Setup basic data for the application'

    def handle(self, *args, **options):
        self.stdout.write('Setting up basic data...')

        with transaction.atomic():
            # Create Categories
            self.stdout.write('\n📁 Creating Categories...')
            categories_created = 0
            
            categories_data = [
                {'name': 'Women', 'path': 'women', 'order': 1},
                {'name': 'Men', 'path': 'men', 'order': 2},
                {'name': 'Clothing', 'path': 'clothing', 'order': 3},
                {'name': 'Accessories', 'path': 'accessories', 'order': 4},
                {'name': 'Shoes', 'path': 'shoes', 'order': 5},
            ]

            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    category_name=cat_data['name'],
                    defaults={
                        'category_path': cat_data['path'],
                        'is_active': True,
                        'display_order': cat_data['order']
                    }
                )
                if created:
                    categories_created += 1
                    self.stdout.write(f'   ✅ {category.category_name}')

            # Create Clothing Types
            self.stdout.write('\n👕 Creating Clothing Types...')
            clothing_types_created = 0
            
            try:
                clothing_category = Category.objects.get(category_name='Clothing')
                clothing_types = [
                    'T-Shirt', 'Shirt', 'Jeans', 'Dress', 'Pants', 
                    'Jacket', 'Sweater', 'Blouse', 'Skirt', 'Shorts'
                ]
                
                for i, type_name in enumerate(clothing_types, 1):
                    clothing_type, created = ClothingType.objects.get_or_create(
                        type_name=type_name,
                        defaults={
                            'category': clothing_category,
                            'is_active': True,
                            'display_order': i
                        }
                    )
                    if created:
                        clothing_types_created += 1
                        self.stdout.write(f'   ✅ {clothing_type.type_name}')
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING('   ⚠️  Clothing category not found, skipping clothing types'))

            # Create Colors
            self.stdout.write('\n🎨 Creating Colors...')
            colors_created = 0
            
            colors_data = [
                {'name': 'Black', 'code': '#000000', 'family': 'Black'},
                {'name': 'White', 'code': '#FFFFFF', 'family': 'White'},
                {'name': 'Red', 'code': '#FF0000', 'family': 'Red'},
                {'name': 'Blue', 'code': '#0000FF', 'family': 'Blue'},
                {'name': 'Green', 'code': '#008000', 'family': 'Green'},
                {'name': 'Navy', 'code': '#000080', 'family': 'Blue'},
                {'name': 'Gray', 'code': '#808080', 'family': 'Gray'},
                {'name': 'Pink', 'code': '#FFC0CB', 'family': 'Pink'},
                {'name': 'Brown', 'code': '#964B00', 'family': 'Brown'},
                {'name': 'Beige', 'code': '#F5F5DC', 'family': 'Neutral'},
            ]

            for color_data in colors_data:
                color, created = Color.objects.get_or_create(
                    color_name=color_data['name'],
                    defaults={
                        'color_code': color_data['code'],
                        'color_family': color_data['family'],
                        'is_active': True
                    }
                )
                if created:
                    colors_created += 1
                    self.stdout.write(f'   ✅ {color.color_name} ({color.color_code})')

            # Create Sizes
            self.stdout.write('\n📏 Creating Sizes...')
            sizes_created = 0
            
            sizes_data = [
                # Clothing sizes
                {'name': 'XS', 'category': 'Clothing', 'group': 'Standard', 'order': 1},
                {'name': 'S', 'category': 'Clothing', 'group': 'Standard', 'order': 2},
                {'name': 'M', 'category': 'Clothing', 'group': 'Standard', 'order': 3},
                {'name': 'L', 'category': 'Clothing', 'group': 'Standard', 'order': 4},
                {'name': 'XL', 'category': 'Clothing', 'group': 'Standard', 'order': 5},
                {'name': 'XXL', 'category': 'Clothing', 'group': 'Standard', 'order': 6},

                # One size fits all
                {'name': 'One Size', 'category': 'Accessories', 'group': 'Universal', 'order': 1},
            ]

            for size_data in sizes_data:
                size, created = Size.objects.get_or_create(
                    size_name=size_data['name'],
                    size_category=size_data['category'],
                    defaults={
                        'size_group': size_data['group'],
                        'sort_order': size_data['order'],
                        'is_active': True
                    }
                )
                if created:
                    sizes_created += 1
                    self.stdout.write(f'   ✅ {size.size_name} ({size.size_category})')

            # Create Currencies
            self.stdout.write('\n💰 Creating Currencies...')
            currencies_created = 0
            
            currencies_data = [
                {
                    'code': 'KGS',
                    'name': 'Kyrgyz Som',
                    'symbol': 'сом',
                    'rate': 1.0,
                    'is_base': True,
                    'decimals': 2
                },
                {
                    'code': 'USD',
                    'name': 'US Dollar',
                    'symbol': '$',
                    'rate': 0.011,  # Approximate rate - you'll need to update this
                    'is_base': False,
                    'decimals': 2
                },
                {
                    'code': 'EUR',
                    'name': 'Euro',
                    'symbol': '€',
                    'rate': 0.010,  # Approximate rate - you'll need to update this
                    'is_base': False,
                    'decimals': 2
                },
                {
                    'code': 'RUB',
                    'name': 'Russian Ruble',
                    'symbol': '₽',
                    'rate': 1.05,  # Approximate rate - you'll need to update this
                    'is_base': False,
                    'decimals': 2
                }
            ]

            for currency_data in currencies_data:
                currency, created = Currency.objects.get_or_create(
                    currency_code=currency_data['code'],
                    defaults={
                        'currency_name': currency_data['name'],
                        'currency_symbol': currency_data['symbol'],
                        'exchange_rate': currency_data['rate'],
                        'is_base_currency': currency_data['is_base'],
                        'is_active': True,
                        'decimal_places': currency_data['decimals']
                    }
                )
                if created:
                    currencies_created += 1
                    base_indicator = ' (BASE)' if currency.is_base_currency else ''
                    self.stdout.write(f'   ✅ {currency.currency_code} - {currency.currency_name}{base_indicator}')

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ Basic data setup completed!'))
        self.stdout.write('\nSummary:')
        self.stdout.write(f'   📁 Categories: {categories_created} created')
        self.stdout.write(f'   👕 Clothing Types: {clothing_types_created} created')
        self.stdout.write(f'   🎨 Colors: {colors_created} created')
        self.stdout.write(f'   📏 Sizes: {sizes_created} created')
        self.stdout.write(f'   💰 Currencies: {currencies_created} created')
        
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Run: python manage.py setup_admin_groups')
        self.stdout.write('2. Create superuser: python manage.py createsuperuser')
        self.stdout.write('3. Access admin: /admin/')
        self.stdout.write('4. Start creating products!')

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing basic data before creating new ones',
        )