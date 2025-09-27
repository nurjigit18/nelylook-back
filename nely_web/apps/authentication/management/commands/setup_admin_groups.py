# Create directory structure first:
# apps/authentication/management/
# apps/authentication/management/__init__.py  (empty file)
# apps/authentication/management/commands/
# apps/authentication/management/commands/__init__.py  (empty file)
# apps/authentication/management/commands/setup_admin_groups.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup admin groups and permissions'

    def handle(self, *args, **options):
        self.stdout.write('Setting up admin groups and permissions...')

        # Create Groups and their permissions
        groups_permissions = {
            'Product Managers': [
                # Product permissions
                'catalog.view_product',
                'catalog.add_product', 
                'catalog.change_product',
                # Category permissions
                'catalog.view_category',
                'catalog.add_category',
                'catalog.change_category',
                # Product variant permissions
                'catalog.view_productvariant',
                'catalog.add_productvariant',
                'catalog.change_productvariant',
                # Read-only access to attributes
                'catalog.view_color',
                'catalog.view_size',
                'catalog.view_clothingtype',
            ],
            
            'Inventory Managers': [
                # Inventory-focused permissions
                'catalog.view_productvariant',
                'catalog.change_productvariant',
                # Color and size management
                'catalog.view_color',
                'catalog.add_color',
                'catalog.change_color',
                'catalog.view_size',
                'catalog.add_size',
                'catalog.change_size',
                # Read-only product access
                'catalog.view_product',
            ],
            
            'Content Managers': [
                # Limited product editing (content only)
                'catalog.view_product',
                'catalog.change_product',
                # Collection management
                'catalog.view_collection',
                'catalog.add_collection',
                'catalog.change_collection',
                'catalog.delete_collection',
                # Image management
                'catalog.view_productimage',
                'catalog.add_productimage',
                'catalog.change_productimage',
                'catalog.delete_productimage',
                # Read-only category access
                'catalog.view_category',
            ],
            
            'Order Managers': [
                # Order management
                'orders.view_order',
                'orders.change_order',
                'orders.view_orderitems',
                'orders.change_orderitems',
                # Delivery zones
                'orders.view_deliveryzones',
                'orders.add_deliveryzones',
                'orders.change_deliveryzones',
                # Read-only product access for order processing
                'catalog.view_product',
                'catalog.view_productvariant',
            ],
            
            'Customer Service': [
                # User management
                'authentication.view_user',
                'authentication.change_user',
                'authentication.view_useraddress',
                'authentication.change_useraddress',
                # Order viewing and limited changes
                'orders.view_order',
                'orders.change_order',
            ],
            
            'Fulfillment': [
                # Shipping and tracking focus
                'orders.view_order',
                'orders.change_order',
                'orders.view_deliveryzones',
                # Read-only product access
                'catalog.view_product',
                'catalog.view_productvariant',
            ],
            
            'User Managers': [
                # Full user management
                'authentication.view_user',
                'authentication.add_user',
                'authentication.change_user',
                'authentication.delete_user',
                'authentication.view_useraddress',
                'authentication.add_useraddress',
                'authentication.change_useraddress',
                'authentication.delete_useraddress',
                # Group management
                'auth.view_group',
                'auth.add_group',
                'auth.change_group',
            ]
        }

        with transaction.atomic():
            for group_name, permission_codenames in groups_permissions.items():
                # Create or get the group
                group, created = Group.objects.get_or_create(name=group_name)
                
                if created:
                    self.stdout.write(f'✅ Created group: {group_name}')
                else:
                    self.stdout.write(f'📝 Updating group: {group_name}')
                
                # Clear existing permissions
                group.permissions.clear()
                
                # Add permissions
                permissions_added = 0
                for perm_codename in permission_codenames:
                    try:
                        app_label, codename = perm_codename.split('.')
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type__app_label=app_label
                        )
                        group.permissions.add(permission)
                        permissions_added += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Permission not found: {perm_codename}')
                        )
                    except ValueError:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Invalid permission format: {perm_codename}')
                        )
                
                self.stdout.write(f'   Added {permissions_added} permissions to {group_name}')

        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ Successfully setup admin groups!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Go to Django admin: /admin/')
        self.stdout.write('2. Navigate to Authentication → Users')
        self.stdout.write('3. Edit a user and:')
        self.stdout.write('   - Check "Staff status" ✅')
        self.stdout.write('   - Leave "Superuser status" unchecked ❌')
        self.stdout.write('   - Add them to appropriate Groups')
        self.stdout.write('\nAvailable groups:')
        for group_name in groups_permissions.keys():
            self.stdout.write(f'   • {group_name}')

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )