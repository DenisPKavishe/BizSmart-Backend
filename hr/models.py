from django.db import models
from django.conf import settings
from core.models import Business, User, Role
from decimal import Decimal

class Department(models.Model):
    """Department/Team within a business"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['business', 'name']


class Employee(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    EMPLOYMENT_TYPE = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
    ]
    
    # Link to existing tables
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='employees')
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='employee_profile',
        help_text="Linked user account for login"
    )
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, help_text="BizSmart role for user account")
    
    # Personal info
    employee_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Employment
    job_title = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='full_time')
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Commission settings
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Commission percentage on sales (0-100)")
    
    # Banking
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    tin_number = models.CharField(max_length=50, blank=True, help_text="Tax ID")
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.employee_number} - {self.full_name}"
    
    def create_user_account(self, password=None):
        """Create or update user account for this employee"""
        if not self.user:
            # Generate username from email
            username = self.email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user
            user = User.objects.create(
                email=self.email,
                username=username,
                first_name=self.first_name,
                last_name=self.last_name,
                phone=self.phone,
                business=self.business,
                role=self.role,
                is_active=True
            )
            if password:
                user.set_password(password)
            else:
                # Generate random password
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
                user.set_password(password)
            user.save()
            self.user = user
            self.save()
            return user, password
        return self.user, None
    
    class Meta:
        ordering = ['first_name', 'last_name']


class Salary(models.Model):
    """Employee salary structure"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    effective_date = models.DateField()
    
    # Base salary
    base_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Monthly base salary")
    
    # Allowances (add to salary)
    housing_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    meal_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    communication_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    risk_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_allowance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Deductions
    paye_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Pay As You Earn")
    sdl = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Skills Development Levy (3.5%)")
    wcf = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Workman's Compensation Fund")
    pension_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    health_insurance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_allowances(self):
        result = Decimal('0')
        if self.housing_allowance:
            result += self.housing_allowance
        if self.transport_allowance:
            result += self.transport_allowance
        if self.meal_allowance:
            result += self.meal_allowance
        if self.communication_allowance:
            result += self.communication_allowance
        if self.risk_allowance:
            result += self.risk_allowance
        if self.other_allowance:
            result += self.other_allowance
        return result
    
    @property
    def total_deductions(self):
        result = Decimal('0')
        if self.paye_tax:
            result += self.paye_tax
        if self.sdl:
            result += self.sdl
        if self.wcf:
            result += self.wcf
        if self.pension_contribution:
            result += self.pension_contribution
        if self.health_insurance:
            result += self.health_insurance
        if self.loan_deduction:
            result += self.loan_deduction
        if self.other_deduction:
            result += self.other_deduction
        return result
    
    @property
    def gross_salary(self):
        base = self.base_salary if self.base_salary else Decimal('0')
        return base + self.total_allowances
    
    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.effective_date}"
    
    class Meta:
        unique_together = ['employee', 'effective_date']
        ordering = ['-effective_date']


class Payroll(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payrolls')
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    processed_date = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_payrolls')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Totals
    total_base_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Link to Financials
    transaction = models.OneToOneField(
        'financials.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll',
        help_text="Links to expense transaction in financials"
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.business.name} - {self.month}/{self.year}"
    
    class Meta:
        unique_together = ['business', 'month', 'year']
        ordering = ['-year', '-month']


class PayrollItem(models.Model):
    """Individual employee payroll entry"""
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='items')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    salary = models.ForeignKey(Salary, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Salary components
    base_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Performance metrics
    total_sales_for_month = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_transactions = models.IntegerField(default=0)
    
    # Payment
    payment_reference = models.CharField(max_length=100, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.payroll} - {self.employee.full_name}"
    
    class Meta:
        unique_together = ['payroll', 'employee']