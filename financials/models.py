from django.db import models
from django.conf import settings
from core.models import Business  # Import Business model

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    COST_TYPE_CHOICES = [
        ('direct', 'Direct Cost (Raw materials, packaging)'),
        ('variable', 'Variable Cost (Shipping, commissions)'),
        ('fixed', 'Fixed Cost (Rent, salaries, insurance)'),
        ('non_cost', 'Not a cost (Income or other)'),
    ]
    
    CATEGORY_CHOICES = [
        # Income categories
        ('sales', 'Sales Revenue'),
        ('service', 'Service Revenue'),
        ('other_income', 'Other Income'),
        
        # Direct Cost categories
        ('raw_materials', 'Raw Materials'),
        ('packaging', 'Packaging'),
        ('direct_labor', 'Direct Labor'),
        ('manufacturing', 'Manufacturing Costs'),
        
        # Variable Cost categories
        ('shipping', 'Shipping & Delivery'),
        ('commissions', 'Sales Commissions'),
        ('transaction_fees', 'Payment Fees'),
        ('marketing', 'Marketing & Advertising'),
        
        # Fixed Cost categories
        ('rent', 'Rent/Lease'),
        ('salaries', 'Salaries'),
        ('insurance', 'Insurance'),
        ('utilities', 'Utilities'),
        ('equipment', 'Equipment'),
        ('software', 'Software Subscriptions'),
        ('loan_interest', 'Loan Interest'),
        ('taxes', 'Taxes'),
        ('other', 'Other'),
    ]
    
    # FIXED: Connect to Business model, not User
    business = models.ForeignKey(
        Business,  # ← Changed from settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Track which user created the transaction
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions'
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    cost_type = models.CharField(max_length=20, choices=COST_TYPE_CHOICES, default='non_cost')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.quantity and self.amount and self.quantity > 0:
            self.unit_price = self.amount / self.quantity
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-transaction_date']


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    # FIXED: Connect to Business model
    business = models.ForeignKey(
        Business,  # ← Changed from settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status != 'paid'


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Loan(models.Model):
    LOAN_TYPE_CHOICES = [
        ('bank', 'Bank Loan'),
        ('sacco', 'SACCO'),
        ('microfinance', 'Microfinance'),
        ('family', 'Family/Friends'),
        ('other', 'Other'),
    ]
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='loans'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_loans'
    )
    lender_name = models.CharField(max_length=200)
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    term_months = models.IntegerField(default=0)
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def balance_remaining(self):
        if self.principal_amount and self.amount_paid:
            return self.principal_amount - self.amount_paid
        return self.principal_amount or 0


class PettyCash(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='petty_cash_entries'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_petty_cash'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    purpose = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    approved_by = models.CharField(max_length=100)
    receipt_image = models.ImageField(upload_to='petty_cash/', blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CashFlowForecast(models.Model):
    # FIXED: Connect to Business model
    business = models.ForeignKey(
        Business,  # ← Changed from settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='cash_forecasts'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_forecasts'
    )
    forecast_date = models.DateField()
    expected_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    expected_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)