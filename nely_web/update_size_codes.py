#!/usr/bin/env python
"""
Script to update size codes and sort order for existing sizes.
Run this with: python manage.py shell < update_size_codes.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nely_web.settings')
django.setup()

from apps.catalog.models import Size

# Size mapping: number -> (letter_code, sort_order)
SIZE_MAPPING = {
    # Clothing sizes (European)
    '38': ('XS', 38),
    '40': ('XS', 40),
    '42': ('S', 42),
    '44': ('S', 44),
    '46': ('M', 46),
    '48': ('M', 48),
    '50': ('L', 50),
    '52': ('L', 52),
    '54': ('XL', 54),
    '56': ('XL', 56),
    '58': ('XXL', 58),
    '60': ('XXL', 60),

    # Shoe sizes (European)
    '35': ('XS', 35),
    '36': ('XS', 36),
    '37': ('S', 37),
    '38': ('S', 38),
    '39': ('M', 39),
    '40': ('M', 40),
    '41': ('L', 41),
    '42': ('L', 42),
    '43': ('XL', 43),
    '44': ('XL', 44),
    '45': ('XXL', 45),
    '46': ('XXL', 46),
}

# Get all sizes
sizes = Size.objects.all()

print("Current sizes in database:")
for size in sizes:
    print(f"  ID: {size.size_id}, Name: {size.size_name}, Code: {size.size_code}, Sort: {size.sort_order}")

print("\nUpdating sizes...")

updated_count = 0
for size in sizes:
    size_name = size.size_name.strip()

    # Check if we have a mapping for this size
    if size_name in SIZE_MAPPING:
        letter_code, sort_order = SIZE_MAPPING[size_name]
        size.size_code = letter_code
        size.sort_order = sort_order
        size.save()
        print(f"✅ Updated {size_name}: code={letter_code}, sort={sort_order}")
        updated_count += 1
    else:
        # Try to extract number and use as sort order
        try:
            numeric_value = int(''.join(filter(str.isdigit, size_name)))
            if size.sort_order is None:
                size.sort_order = numeric_value
                size.save()
                print(f"⚠️  {size_name}: No code mapping found, set sort_order={numeric_value}")
        except:
            print(f"❌ {size_name}: Could not process (no mapping and no numeric value)")

print(f"\n✅ Updated {updated_count} sizes")

print("\nFinal sizes (sorted):")
sizes = Size.objects.all().order_by('sort_order', 'size_name')
for size in sizes:
    print(f"  {size.size_name}: Code={size.size_code or 'None'}, Sort={size.sort_order}")
