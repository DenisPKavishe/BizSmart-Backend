# inventory/management/commands/update_barcodes.py

from django.core.management.base import BaseCommand
from inventory.models import Product
from inventory.barcode_generator import generate_barcode_for_product


class Command(BaseCommand):
    help = 'Update all product barcodes to EAN-13 format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        products = Product.objects.filter(is_active=True)
        total = products.count()
        updated = 0
        skipped = 0
        
        self.stdout.write(f"Found {total} active products")
        
        if dry_run:
            self.stdout.write("\n📋 DRY RUN - No changes will be saved\n")
        
        for product in products:
            old_barcode = product.barcode
            
            # Generate new EAN-13 barcode
            new_barcode = generate_barcode_for_product(product, method='ean13')
            
            if old_barcode == new_barcode:
                skipped += 1
                self.stdout.write(f"  ⏭️  {product.name}: Already correct")
            else:
                updated += 1
                self.stdout.write(f"  🔄 {product.name}: {old_barcode} → {new_barcode}")
                
                if not dry_run:
                    product.barcode = new_barcode
                    product.save()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"✅ Total products: {total}")
        self.stdout.write(f"✅ Updated: {updated}")
        self.stdout.write(f"⏭️  Skipped (already correct): {skipped}")
        
        if dry_run:
            self.stdout.write("\n⚠️  This was a DRY RUN. Run without --dry-run to apply changes.")