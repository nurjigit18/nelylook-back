from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Assign a user to the Manager group'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username of the user to add to Manager group'
        )

    def handle(self, *args, **options):
        username = options['username']

        # Check if Manager group exists
        try:
            manager_group = Group.objects.get(name='Manager')
        except Group.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '✗ Manager group does not exist. Run "python manage.py setup_manager_group" first.'
                )
            )
            return

        # Get the user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ User "{username}" not found.'
                )
            )
            self.stdout.write('')
            self.stdout.write('Available users:')
            for u in User.objects.all()[:10]:
                self.stdout.write(f'  • {u.username}')
            return

        # Check if user is already in the group
        if user.groups.filter(name='Manager').exists():
            self.stdout.write(
                self.style.WARNING(
                    f'• User "{username}" is already in the Manager group.'
                )
            )
            return

        # Add user to group
        user.groups.add(manager_group)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('━' * 50))
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ User "{username}" has been added to the Manager group!'
            )
        )
        self.stdout.write('')
        self.stdout.write('This user now has access to:')
        self.stdout.write('  • Товары (Products)')
        self.stdout.write('  • Вариации товаров (Product Variants)')
        self.stdout.write('  • Категории (Categories)')
        self.stdout.write('  • Коллекции (Collections)')
        self.stdout.write('  • Цвета (Colors)')
        self.stdout.write('')
        self.stdout.write('They will NOT see other admin sections.')
        self.stdout.write(self.style.SUCCESS('━' * 50))
