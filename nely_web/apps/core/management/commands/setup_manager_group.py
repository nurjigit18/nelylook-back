from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Set up Manager group with permissions for specific catalog models'

    def handle(self, *args, **options):
        # Create or get the Manager group
        manager_group, created = Group.objects.get_or_create(name='Manager')

        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created "Manager" group'))
        else:
            self.stdout.write(self.style.WARNING('• "Manager" group already exists'))

        # Define the models that managers can access
        # These correspond to the MANAGER_ALLOWED_MODELS in admin_mixins.py
        allowed_models = [
            ('catalog', 'product'),           # Товары
            ('catalog', 'productvariant'),    # Вариации товаров
            ('catalog', 'category'),          # Категории
            ('catalog', 'collection'),        # Коллекции
            ('catalog', 'color'),             # Цвета
        ]

        # Permission types to grant
        permission_types = ['view', 'add', 'change', 'delete']

        permissions_added = 0

        for app_label, model_name in allowed_models:
            try:
                # Get the content type for this model
                content_type = ContentType.objects.get(
                    app_label=app_label,
                    model=model_name
                )

                # Add all permission types for this model
                for perm_type in permission_types:
                    codename = f'{perm_type}_{model_name}'

                    try:
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type=content_type
                        )

                        # Add permission to group if not already added
                        if permission not in manager_group.permissions.all():
                            manager_group.permissions.add(permission)
                            permissions_added += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Added: {app_label}.{codename}'
                                )
                            )
                        else:
                            self.stdout.write(
                                f'  • Already has: {app_label}.{codename}'
                            )

                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Permission not found: {app_label}.{codename}'
                            )
                        )

            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Model not found: {app_label}.{model_name}'
                    )
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('━' * 50))
        if permissions_added > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Setup complete! Added {permissions_added} new permissions to Manager group'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Manager group is already properly configured'
                )
            )
        self.stdout.write('')
        self.stdout.write('To assign a user to the Manager group:')
        self.stdout.write('  python manage.py shell')
        self.stdout.write('  >>> from django.contrib.auth.models import User, Group')
        self.stdout.write('  >>> user = User.objects.get(username="username")')
        self.stdout.write('  >>> manager_group = Group.objects.get(name="Manager")')
        self.stdout.write('  >>> user.groups.add(manager_group)')
        self.stdout.write(self.style.SUCCESS('━' * 50))
