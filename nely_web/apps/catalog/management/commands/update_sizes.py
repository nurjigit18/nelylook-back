from django.core.management.base import BaseCommand
from apps.catalog.models import Size


class Command(BaseCommand):
    help = 'Update size codes and sort order for existing sizes'

    def handle(self, *args, **options):
        # Size mapping: number -> (letter_code, sort_order)
        SIZE_MAPPING = {
            # Clothing sizes (European)
            '38': ('2XS', 38),
            '40': ('XS', 40),
            '42': ('S', 42),
            '44': ('M', 44),
            '46': ('L', 46),
            '48': ('XL', 48),
            '50': ('2XL', 50),
            '52': ('3XL', 52),
            '54': ('4XL', 54),
            '56': ('5XL', 56),

        }

        # Get all sizes
        sizes = Size.objects.all()

        self.stdout.write("\n📋 Current sizes in database:")
        for size in sizes:
            self.stdout.write(f"  ID: {size.size_id}, Name: {size.size_name}, Code: {size.size_code or 'None'}, Sort: {size.sort_order or 'None'}")

        self.stdout.write("\n🔄 Updating sizes...")

        updated_count = 0
        for size in sizes:
            size_name = size.size_name.strip()

            # Check if we have a mapping for this size
            if size_name in SIZE_MAPPING:
                letter_code, sort_order = SIZE_MAPPING[size_name]
                size.size_code = letter_code
                size.sort_order = sort_order
                size.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Updated {size_name}: code={letter_code}, sort={sort_order}"))
                updated_count += 1
            else:
                # Try to extract number and use as sort order
                try:
                    numeric_value = int(''.join(filter(str.isdigit, size_name)))
                    if size.sort_order is None:
                        size.sort_order = numeric_value
                        size.save()
                        self.stdout.write(self.style.WARNING(f"⚠️  {size_name}: No code mapping found, set sort_order={numeric_value}"))
                except:
                    self.stdout.write(self.style.ERROR(f"❌ {size_name}: Could not process (no mapping and no numeric value)"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Updated {updated_count} sizes"))

        self.stdout.write("\n📊 Final sizes (sorted):")
        sizes = Size.objects.all().order_by('sort_order', 'size_name')
        for size in sizes:
            self.stdout.write(f"  {size.size_name}: Code={size.size_code or 'None'}, Sort={size.sort_order}")

        self.stdout.write(self.style.SUCCESS("\n✨ Size update complete!"))
