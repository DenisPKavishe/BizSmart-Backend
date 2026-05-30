# inventory/barcode_generator.py

import random
import string
from decimal import Decimal


def generate_ean13(product_id, business_id):
    """
    Generate EAN-13 barcode number (13 digits).
    Format: [country_code][business_prefix][product_id][checksum]
    """
    # Tanzania country code (usually starts with 620 for local products)
    country_code = "620"  # 620 is Tanzania, 890 is India, 690 is China
    
    # Business code (3 digits - take from business_id)
    business_str = str(business_id).replace('-', '').replace('_', '')
    business_digits = ''.join(c for c in business_str if c.isdigit())
    business_code = business_digits.zfill(3)[:3]
    
    # Product code (6 digits)
    product_str = str(product_id)
    product_digits = ''.join(c for c in product_str if c.isdigit())
    product_code = product_digits.zfill(6)[:6]
    
    # Combine first 12 digits
    base = country_code + business_code + product_code
    base = base[:12]
    
    # Calculate checksum
    checksum = calculate_ean13_checksum(base)
    
    return base + str(checksum)


def calculate_ean13_checksum(barcode):
    """Calculate EAN-13 checksum digit"""
    total = 0
    for i, ch in enumerate(barcode):
        if not ch.isdigit():
            continue
        digit = int(ch)
        if i % 2 == 0:  # Odd position (1-indexed)
            total += digit
        else:  # Even position
            total += digit * 3
    
    remainder = total % 10
    if remainder == 0:
        return 0
    return 10 - remainder


def generate_code128(product_sku, product_id):
    """
    Generate Code 128 barcode from SKU.
    Good for internal use.
    """
    # Clean SKU (remove special characters)
    clean_sku = ''.join(c for c in product_sku.upper() if c.isalnum())
    
    if len(clean_sku) >= 8:
        return clean_sku[:12]
    
    # Pad with product ID
    product_id_str = str(product_id)
    result = (clean_sku + product_id_str).upper()
    
    return result[:12]


def generate_upc(product_id):
    """
    Generate UPC-A barcode (12 digits).
    """
    base = str(product_id).zfill(11)
    
    # Calculate checksum
    total = 0
    for i, digit in enumerate(base):
        digit = int(digit)
        if i % 2 == 0:
            total += digit * 3
        else:
            total += digit
    
    remainder = total % 10
    checksum = 0 if remainder == 0 else 10 - remainder
    
    return base + str(checksum)


def generate_random_barcode():
    """Generate random barcode for testing"""
    return ''.join(random.choices(string.digits, k=13))


def generate_barcode_for_product(product, method='ean13'):
    """
    Generate appropriate barcode for a product.
    
    Methods:
    - 'ean13': Generate EAN-13 (13 digits) - RECOMMENDED
    - 'code128': Generate Code 128 from SKU
    - 'upc': Generate UPC-A (12 digits)
    - 'auto': Try SKU first, then EAN-13
    """
    business_id = product.business.id if product.business else 1
    
    if method == 'code128':
        return generate_code128(product.sku, product.id)
    elif method == 'upc':
        return generate_upc(product.id)
    elif method == 'ean13':
        return generate_ean13(product.id, business_id)
    else:  # auto
        # If SKU is numeric and 13 digits, use it
        numeric_sku = ''.join(c for c in product.sku if c.isdigit())
        if len(numeric_sku) == 13:
            return numeric_sku
        # Otherwise generate EAN-13
        return generate_ean13(product.id, business_id)


def validate_barcode(barcode):
    """Validate if barcode is in correct EAN-13 format"""
    if not barcode or len(barcode) != 13:
        return False
    
    if not barcode.isdigit():
        return False
    
    # Validate checksum
    checksum = calculate_ean13_checksum(barcode[:12])
    return int(barcode[12]) == checksum