# apps/core/management/commands/populate_db.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random
from faker import Faker

from apps.authentication.models import User, UserAddress
from apps.catalog.models import (
    Category, ClothingType, Product, ProductVariant, Color, Size,
    Collection, CollectionProduct, ProductImage, RelatedProduct
)
from apps.cart.models import ShoppingCart, CartItems
from apps.orders.models import Order, OrderItems, DeliveryZones
from apps.wishlist.models import Wishlists
from apps.core.models import Currency
from apps.payments.models import Payment, FxRate

fake = Faker()
User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with fake data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of users to create'
        )
        parser.add_argument(
            '--products',
            type=int,
            default=100,
            help='Number of products to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Creating fake data...')
        
        # Create data in correct order (dependencies first)
        self.create_currencies()
        self.create_delivery_zones()
        self.create_categories()
        self.create_clothing_types()
        self.create_colors()
        self.create_sizes()
        self.create_collections()
        self.create_users(options['users'])
        self.create_products(options['products'])
        self.create_product_variants()
        self.create_product_images()
        self.create_related_products()
        self.create_collection_products()
        self.create_shopping_carts()
        self.create_orders()
        self.create_wishlists()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with fake data!')
        )

    def clear_data(self):
        """Clear all data (be careful with this!)"""
        models_to_clear = [
            OrderItems, Order, CartItems, ShoppingCart, Wishlists,
            ProductImage, RelatedProduct, CollectionProduct, ProductVariant,
            Product, Collection, ClothingType, Category, Color, Size,
            UserAddress, User, Currency, DeliveryZones, Payment, FxRate
        ]
        
        for model in models_to_clear:
            model.objects.all().delete()
            self.stdout.write(f'Cleared {model.__name__}')

    def create_currencies(self):
        currencies = [
            ('KGS', 'Kyrgyz Som', 'с', 1.0, True),
            ('USD', 'US Dollar', '$', 0.012, False),
            ('EUR', 'Euro', '€', 0.011, False),
            ('RUB', 'Russian Ruble', '₽', 1.1, False),
        ]
        
        for code, name, symbol, rate, is_base in currencies:
            Currency.objects.get_or_create(
                currency_code=code,
                defaults={
                    'currency_name': name,
                    'currency_symbol': symbol,
                    'exchange_rate': Decimal(str(rate)),
                    'is_base_currency': is_base,
                    'is_active': True,
                    'decimal_places': 2,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                }
            )
        self.stdout.write('Created currencies')

    def create_delivery_zones(self):
        zones = [
            ('Bishkek City', 'Bishkek', 150, 1),
            ('Chui Region', 'Kant,Tokmok,Kemin', 250, 2),
            ('Osh City', 'Osh', 300, 3),
            ('Issyk-Kul', 'Karakol,Balykchy,Cholpon-Ata', 400, 4),
            ('Naryn Region', 'Naryn,At-Bashy', 500, 5),
        ]
        
        for name, cities, cost, days in zones:
            DeliveryZones.objects.get_or_create(
                zone_name=name,
                defaults={
                    'cities': cities,
                    'delivery_cost': Decimal(str(cost)),
                    'delivery_time_days': days,
                    'is_active': True,
                }
            )
        self.stdout.write('Created delivery zones')

    def create_categories(self):
        # Main categories
        main_categories = ['Clothing', 'Shoes', 'Accessories']
        categories = {}
        
        for cat_name in main_categories:
            cat = Category.objects.get_or_create(
                category_name=cat_name,
                defaults={
                    'category_path': cat_name,
                    'description': f'{cat_name} category',
                    'display_order': main_categories.index(cat_name) + 1,
                    'is_active': True,
                }
            )[0]
            categories[cat_name] = cat

        # Subcategories
        subcategories = {
            'Clothing': ['Tops', 'Bottoms', 'Dresses', 'Outerwear'],
            'Shoes': ['Sneakers', 'Boots', 'Heels', 'Flats'],
            'Accessories': ['Bags', 'Jewelry', 'Hats', 'Belts']
        }

        for parent_name, subs in subcategories.items():
            parent = categories[parent_name]
            for sub_name in subs:
                Category.objects.get_or_create(
                    category_name=sub_name,
                    defaults={
                        'parent_category': parent,
                        'category_path': f'{parent_name} > {sub_name}',
                        'description': f'{sub_name} subcategory',
                        'display_order': subs.index(sub_name) + 1,
                        'is_active': True,
                    }
                )

        self.stdout.write('Created categories')

    def create_clothing_types(self):
        clothing_types = {
            'Tops': ['T-Shirt', 'Shirt', 'Blouse', 'Tank Top', 'Sweater'],
            'Bottoms': ['Jeans', 'Pants', 'Shorts', 'Skirt', 'Leggings'],
            'Dresses': ['Casual Dress', 'Evening Dress', 'Maxi Dress', 'Mini Dress'],
            'Outerwear': ['Jacket', 'Coat', 'Hoodie', 'Cardigan'],
            'Sneakers': ['Running Shoes', 'Casual Sneakers', 'High-tops'],
            'Boots': ['Ankle Boots', 'Knee-high Boots', 'Combat Boots'],
        }

        for category_name, types in clothing_types.items():
            try:
                category = Category.objects.get(category_name=category_name)
                for type_name in types:
                    ClothingType.objects.get_or_create(
                        type_name=type_name,
                        category=category,
                        defaults={
                            'display_order': types.index(type_name) + 1,
                            'is_active': True,
                        }
                    )
            except Category.DoesNotExist:
                continue

        self.stdout.write('Created clothing types')

    def create_colors(self):
        colors = [
            ('Black', '#000000', 'Black'),
            ('White', '#FFFFFF', 'White'),
            ('Red', '#FF0000', 'Red'),
            ('Blue', '#0000FF', 'Blue'),
            ('Green', '#008000', 'Green'),
            ('Navy', '#000080', 'Blue'),
            ('Gray', '#808080', 'Gray'),
            ('Pink', '#FFC0CB', 'Pink'),
            ('Yellow', '#FFFF00', 'Yellow'),
            ('Purple', '#800080', 'Purple'),
            ('Brown', '#A52A2A', 'Brown'),
            ('Orange', '#FFA500', 'Orange'),
        ]

        for name, code, family in colors:
            Color.objects.get_or_create(
                color_name=name,
                defaults={
                    'color_code': code,
                    'color_family': family,
                    'is_active': True,
                }
            )

        self.stdout.write('Created colors')

    def create_sizes(self):
        sizes = [
            # Clothing sizes
            ('XS', 'Clothing', 'Letter', 1),
            ('S', 'Clothing', 'Letter', 2),
            ('M', 'Clothing', 'Letter', 3),
            ('L', 'Clothing', 'Letter', 4),
            ('XL', 'Clothing', 'Letter', 5),
            ('XXL', 'Clothing', 'Letter', 6),
            # Shoe sizes
            ('36', 'Shoes', 'EU', 1),
            ('37', 'Shoes', 'EU', 2),
            ('38', 'Shoes', 'EU', 3),
            ('39', 'Shoes', 'EU', 4),
            ('40', 'Shoes', 'EU', 5),
            ('41', 'Shoes', 'EU', 6),
            ('42', 'Shoes', 'EU', 7),
            ('43', 'Shoes', 'EU', 8),
        ]

        for name, category, group, order in sizes:
            Size.objects.get_or_create(
                size_name=name,
                defaults={
                    'size_category': category,
                    'size_group': group,
                    'sort_order': order,
                    'is_active': True,
                }
            )

        self.stdout.write('Created sizes')

    def create_collections(self):
        collections = [
            ('Summer 2024', 'summer-2024', 'Hot summer collection'),
            ('Winter Essentials', 'winter-essentials', 'Cozy winter wear'),
            ('New Arrivals', 'new-arrivals', 'Latest fashion trends'),
            ('Best Sellers', 'best-sellers', 'Customer favorites'),
            ('Sale Items', 'sale-items', 'Discounted products'),
        ]

        for name, slug, desc in collections:
            Collection.objects.get_or_create(
                collection_slug=slug,
                defaults={
                    'collection_name': name,
                    'description': desc,
                    'is_featured': random.choice([True, False]),
                    'display_order': collections.index((name, slug, desc)) + 1,
                    'is_active': True,
                    'created_at': timezone.now(),
                }
            )

        self.stdout.write('Created collections')

    def create_users(self, count):
        # Create superuser
        if not User.objects.filter(email='admin@nelylook.com').exists():
            User.objects.create_superuser(
                email='admin@nelylook.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role='admin'
            )

        # Create regular users
        for i in range(count):
            user = User.objects.create_user(
                email=fake.unique.email(),
                password='password123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone=fake.phone_number()[:20],
                role=random.choice(['customer', 'customer', 'customer', 'admin']),
                is_active=True,
                email_verified=random.choice([True, False]),
            )

            # Create address for user
            UserAddress.objects.create(
                user=user,
                address_type=random.choice(['Billing', 'Shipping', 'Both']),
                first_name=user.first_name,
                last_name=user.last_name,
                address_line1=fake.street_address(),
                city=random.choice(['Bishkek', 'Osh', 'Karakol', 'Naryn']),
                country='Kyrgyzstan',
                postal_code=fake.postcode(),
                phone=fake.phone_number()[:20],
                is_default=True,
                created_at=timezone.now(),
            )

        self.stdout.write(f'Created {count} users')

    def create_products(self, count):
        categories = list(Category.objects.filter(parent_category__isnull=False))
        clothing_types = list(ClothingType.objects.all())
        
        clothing_names = [
            'Cotton T-Shirt', 'Denim Jeans', 'Silk Blouse', 'Wool Sweater',
            'Casual Dress', 'Sports Shorts', 'Leather Jacket', 'Knit Cardigan',
            'Chino Pants', 'Maxi Dress', 'Polo Shirt', 'Pencil Skirt',
            'Hoodie', 'Blazer', 'Tank Top', 'Wide Leg Pants', 'Midi Dress',
            'Crop Top', 'Joggers', 'Trench Coat', 'Button-down Shirt',
            'A-line Skirt', 'Pullover', 'Cargo Pants', 'Slip Dress'
        ]

        for i in range(count):
            category = random.choice(categories)
            clothing_type = random.choice(
                [ct for ct in clothing_types if ct.category == category]
            ) if clothing_types else None

            base_name = random.choice(clothing_names)
            product_name = f"{base_name} - {fake.color_name()}"
            
            base_price = Decimal(str(random.uniform(20, 200)))
            
            product = Product.objects.create(
                product_name=product_name,
                slug=f"{product_name.lower().replace(' ', '-').replace(',', '')}-{i}",
                description=fake.text(max_nb_chars=500),
                short_description=fake.text(max_nb_chars=150),
                category=category,
                clothing_type=clothing_type,
                season=random.choice(['spring', 'summer', 'autumn', 'winter', 'all']),
                gender=random.choice(['women', 'men']),
                base_price=base_price,
                sale_price=base_price * Decimal('0.8') if random.choice([True, False]) else None,
                cost_price=base_price * Decimal('0.6'),
                is_featured=random.choice([True, False]),
                is_new_arrival=random.choice([True, False]),
                is_bestseller=random.choice([True, False]),
                status=random.choice(['draft', 'active', 'active', 'active']),  # More active
            )

        self.stdout.write(f'Created {count} products')

    def create_product_variants(self):
        products = Product.objects.all()
        colors = list(Color.objects.all())
        sizes = list(Size.objects.all())

        for product in products:
            # Create 2-5 variants per product
            variant_count = random.randint(2, 5)
            used_combinations = set()

            for _ in range(variant_count):
                color = random.choice(colors)
                size = random.choice(sizes)
                
                # Ensure unique color-size combination
                combo = (color.color_id, size.size_id)
                if combo in used_combinations:
                    continue
                used_combinations.add(combo)

                variant_price = product.base_price + Decimal(str(random.uniform(-10, 30)))
                
                ProductVariant.objects.create(
                    product=product,
                    sku=f"{product.product_code}-{color.color_name[:2].upper()}-{size.size_name}",
                    size=size,
                    color=color,
                    price=variant_price,
                    sale_price=variant_price * Decimal('0.85') if random.choice([True, False]) else None,
                    weight=Decimal(str(random.uniform(0.1, 2.0))),
                    stock_quantity=random.randint(0, 100),
                    low_stock_threshold=10,
                    status=random.choice(['Active', 'Active', 'Inactive']),  # More active
                    created_at=timezone.now(),
                )

        self.stdout.write('Created product variants')

    def create_product_images(self):
        variants = ProductVariant.objects.all()
        
        # Sample image URLs (you can replace with real URLs)
        sample_images = [
            'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500',
            'https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=500',
            'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?w=500',
            'https://images.unsplash.com/photo-1503341733017-1901578f9f1e?w=500',
            'https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=500',
        ]

        for variant in variants:
            # Create 1-3 images per variant
            image_count = random.randint(1, 3)
            
            for i in range(image_count):
                ProductImage.objects.create(
                    product=variant.product,
                    variant=variant,
                    image_url=random.choice(sample_images),
                    alt_text=f"{variant.product.product_name} image",
                    is_primary=(i == 0),  # First image is primary
                    display_order=i + 1,
                    image_type=random.choice(['Main', 'Gallery', 'Thumbnail']),
                    created_at=timezone.now(),
                )

        self.stdout.write('Created product images')

    def create_related_products(self):
        products = list(Product.objects.all())
        
        for product in random.sample(products, min(50, len(products))):
            # Create 2-4 related products
            related_count = random.randint(2, 4)
            potential_related = [p for p in products if p != product]
            
            for related in random.sample(potential_related, min(related_count, len(potential_related))):
                RelatedProduct.objects.get_or_create(
                    product=product,
                    related_product=related,
                    defaults={
                        'relation_type': random.choice(['related', 'similar', 'upsell', 'crosssell']),
                        'display_order': random.randint(1, 10),
                        'created_at': timezone.now(),
                    }
                )

        self.stdout.write('Created related products')

    def create_collection_products(self):
        collections = Collection.objects.all()
        products = list(Product.objects.filter(status='active'))

        for collection in collections:
            # Add 10-20 products to each collection
            product_count = random.randint(10, min(20, len(products)))
            selected_products = random.sample(products, product_count)

            for i, product in enumerate(selected_products):
                CollectionProduct.objects.get_or_create(
                    collection=collection,
                    product=product,
                    defaults={'display_order': i + 1}
                )

        self.stdout.write('Created collection products')

    def create_shopping_carts(self):
        users = list(User.objects.all())
        variants = list(ProductVariant.objects.filter(stock_quantity__gt=0))

        # Create carts for 30% of users
        for user in random.sample(users, len(users) // 3):
            cart = ShoppingCart.objects.create(
                user=user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

            # Add 1-5 items to cart
            item_count = random.randint(1, 5)
            cart_variants = random.sample(variants, min(item_count, len(variants)))

            for variant in cart_variants:
                CartItems.objects.create(
                    cart=cart,
                    variant=variant,
                    quantity=random.randint(1, 3),
                    price=variant.price,
                    added_at=timezone.now(),
                )

        self.stdout.write('Created shopping carts')

    def create_orders(self):
        users = list(User.objects.all())
        variants = list(ProductVariant.objects.filter(stock_quantity__gt=0))
        currency = Currency.objects.get(currency_code='KGS')
        addresses = list(UserAddress.objects.all())

        # Create orders for 50% of users
        for user in random.sample(users, len(users) // 2):
            order_count = random.randint(1, 3)
            
            for _ in range(order_count):
                user_addresses = [addr for addr in addresses if addr.user == user]
                address = random.choice(user_addresses) if user_addresses else None

                order = Order.objects.create(
                    order_number=f"NL-{fake.unique.random_number(digits=8)}",
                    user=user,
                    order_date=fake.date_time_between(start_date='-6m', end_date='now', tzinfo=timezone.get_current_timezone()),
                    order_status=random.choice(['Pending', 'Confirmed', 'Processing', 'Shipped', 'Delivered']),
                    payment_status=random.choice(['Pending', 'Paid', 'Failed']),
                    payment_method=random.choice(['FreedomPay KG', 'Cash on Delivery']),
                    shipping_address=address,
                    billing_address=address,
                    currency=currency,
                    subtotal_base=Decimal('0'),
                    total_amount_base=Decimal('0'),
                )

                # Add order items
                item_count = random.randint(1, 4)
                order_variants = random.sample(variants, min(item_count, len(variants)))
                
                subtotal = Decimal('0')
                for variant in order_variants:
                    quantity = random.randint(1, 2)
                    unit_price = variant.price
                    total_price = unit_price * quantity
                    subtotal += total_price

                    OrderItems.objects.create(
                        order=order,
                        variant=variant,
                        product_name=variant.product.product_name,
                        variant_details=f"{variant.color.color_name}, {variant.size.size_name}",
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                    )

                # Update order totals
                order.subtotal_base = subtotal
                order.total_amount_base = subtotal + Decimal('150')  # Add shipping
                order.save()

        self.stdout.write('Created orders')

    def create_wishlists(self):
        users = list(User.objects.all())
        variants = list(ProductVariant.objects.all())

        # Create wishlist items for 40% of users
        for user in random.sample(users, len(users) * 2 // 5):
            # Add 3-8 items to wishlist
            item_count = random.randint(3, 8)
            wishlist_variants = random.sample(variants, min(item_count, len(variants)))

            for variant in wishlist_variants:
                Wishlists.objects.create(
                    user=user,
                    variant=variant,
                    added_at=fake.date_time_between(start_date='-3m', end_date='now', tzinfo=timezone.get_current_timezone()),
                )

        self.stdout.write('Created wishlists')