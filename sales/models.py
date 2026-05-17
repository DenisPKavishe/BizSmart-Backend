from django.db import models
from django.conf import settings
from core.models import Business
from inventory.models import Product
from decimal import Decimal
from hr.models import Employee

class Customer(models.Model):
    """Customer database"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='customers')
    
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Loyalty
    total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_visits = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-total_spent']


class Sale(models.Model):
    """Main sale record"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mpesa', 'M-Pesa'),
        ('tigo_pesa', 'Tigo Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('halopesa', 'HaloPesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit/Invoice'),
    ]
    
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Payment'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Sale details
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    
    # Financials
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    change_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        help_text="Employee who processed this sale"
    )
    
    def save(self, *args, **kwargs):
        # Calculate totals
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        if self.amount_paid > self.total_amount:
            self.change_amount = self.amount_paid - self.total_amount
        else:
            self.change_amount = 0
        super().save(*args, **kwargs)
    
    @property
    def balance_due(self):
        if self.amount_paid < self.total_amount:
            return self.total_amount - self.amount_paid
        return 0
    
    def __str__(self):
        return f"{self.invoice_number} - {self.sale_date.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-sale_date']


class SaleItem(models.Model):
    """Individual items in a sale"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)
    
    @property
    def profit(self):
        return (self.unit_price - self.cost_price) * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Return(models.Model):
    """Customer returns/refunds"""
    REASON_CHOICES = [
        ('damaged', 'Damaged Product'),
        ('wrong_item', 'Wrong Item'),
        ('expired', 'Expired'),
        ('customer_request', 'Customer Request'),
        ('other', 'Other'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='returns')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name='returns', null=True, blank=True)
    
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    quantity_returned = models.IntegerField(default=1)
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Return for {self.sale.invoice_number}"