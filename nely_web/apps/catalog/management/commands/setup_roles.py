# apps/core/management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.catalog.models import ClothingType, Category

class Command(BaseCommand):
    help = "Create 'Manager' group and assign ClothingType CRUD permissions"

    def handle(self, *args, **options):
        mgr, _ = Group.objects.get_or_create(name="manager")

        # ClothingType permissions
        ct = ContentType.objects.get_for_model(ClothingType)
        perms = Permission.objects.filter(content_type=ct, codename__in=[
            "view_clothingtype", "add_clothingtype", "change_clothingtype", "delete_clothingtype",
        ])
        mgr.permissions.add(*perms)

        # Optional: allow viewing categories, but not adding/deleting
        ct_cat = ContentType.objects.get_for_model(Category)
        view_cat = Permission.objects.get(content_type=ct_cat, codename="view_category")
        mgr.permissions.add(view_cat)

        self.stdout.write(self.style.SUCCESS("✅ 'manager' group ready with ClothingType CRUD."))
