# inventory/signals.py

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Product
from .barcode_generator import generate_barcode_for_product


@receiver(pre_save, sender=Product)
def auto_generate_barcode(sender, instance, **kwargs):
    """
    Automatically generate EAN-13 barcode for new products.
    """
    # Generate only if barcode is empty
    if not instance.barcode:
        # Use EAN-13 by default
        instance.barcode = generate_barcode_for_product(instance, method='ean13')
        print(f"🔖 Auto-generated EAN-13 barcode for {instance.name}: {instance.barcode}")