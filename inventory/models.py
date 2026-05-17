from django.db import models
from django.conf import settings
from core.models import Business
from decimal import Decimal

class Category(models.Model):
    """Product categories like 'Electronics', 'Clothing', 'Food'"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ['business', 'name']


class Supplier(models.Model):
    """Suppliers who provide products"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True, help_text="TIN or VAT number")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Products for sale"""
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
        ('meter', 'Meter'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('dozen', 'Dozen'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit - unique identifier")
    barcode = models.CharField(max_length=100, blank=True, help_text="Barcode number")
    description = models.TextField(blank=True)
    
    # Pricing - with defaults
    buying_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Cost price per unit")
    selling_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Selling price per unit")
    
    # Stock levels
    quantity_on_hand = models.IntegerField(default=0, help_text="Current stock quantity")
    reorder_level = models.IntegerField(default=0, help_text="Alert when stock reaches this level")
    reorder_quantity = models.IntegerField(default=0, help_text="Quantity to reorder")
    
    # Other
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Tracking
    total_investment = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="buying_price * quantity_on_hand")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total investment
        self.total_investment = self.buying_price * self.quantity_on_hand
        super().save(*args, **kwargs)
    
    @property
    def profit_per_unit(self):
        if self.selling_price and self.buying_price:
            return self.selling_price - self.buying_price
        return Decimal('0.00')
    
    @property
    def profit_margin_percentage(self):
        if self.selling_price and self.selling_price > 0:
            return (self.profit_per_unit / self.selling_price) * 100
        return Decimal('0.00')
    
    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_level
    
    def __str__(self):
        return f"{self.name} ({self.sku}) - Stock: {self.quantity_on_hand} {self.unit}"
    
    class Meta:
        unique_together = ['business', 'sku']


class StockMovement(models.Model):
    """Track all stock movements in/out"""
    MOVEMENT_TYPES = [
        ('IN', 'Stock In - Purchase'),
        ('OUT', 'Stock Out - Sale'),
        ('ADJUST_IN', 'Adjustment - Increase'),
        ('ADJUST_OUT', 'Adjustment - Decrease'),
        ('RETURN_IN', 'Return from Customer'),
        ('RETURN_OUT', 'Return to Supplier'),
        ('DAMAGED', 'Damaged/Lost'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='stock_movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    
    quantity = models.IntegerField(default=0)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Cost at time of movement")
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    reference_id = models.CharField(max_length=100, blank=True, help_text="Reference ID (Sale ID, PO ID)")
    reference_type = models.CharField(max_length=50, blank=True, help_text="sale, purchase_order, adjustment")
    notes = models.TextField(blank=True)
    
    previous_quantity = models.IntegerField(default=0, help_text="Quantity before movement")
    new_quantity = models.IntegerField(default=0, help_text="Quantity after movement")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        # Store previous quantity
        if self.product_id:
            self.previous_quantity = self.product.quantity_on_hand
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.quantity} x {self.product.name}"
    
    class Meta:
        ordering = ['-created_at']


class PurchaseOrder(models.Model):
    """Order stock from suppliers"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('received', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    po_number = models.CharField(max_length=50, unique=True, help_text="Purchase Order Number")
    
    order_date = models.DateField(auto_now_add=True)
    expected_delivery = models.DateField()
    actual_delivery = models.DateField(null=True, blank=True)
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"
    
    class Meta:
        ordering = ['-order_date']


class PurchaseOrderItem(models.Model):
    """Items in a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quantity_received = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
    
    @property
    def remaining_quantity(self):
        return self.quantity - self.quantity_received
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} @ {self.unit_cost}"