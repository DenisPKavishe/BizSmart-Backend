from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('general_manager', 'General Manager'),
        ('accountant', 'Accountant'),
        ('inventory_manager', 'Inventory Manager'),
        ('cashier', 'Cashier/Sales Rep'),
        ('auditor', 'Auditor/Viewer'),
    ]
    name = models.CharField(max_length=30, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True, help_text="What this role can do")
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        ordering = ['name']

class Business(models.Model):
    CITY_CHOICES = [
        ('ARUSHA', 'Arusha'),
        ('DAR_ES_SALAAM', 'Dar es Salaam'),
        ('ZANZIBAR', 'Zanzibar'),
    ]
    
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    city = models.CharField(max_length=30, choices=CITY_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField(help_text="Street address, building name, area")
    postal_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_city_display()}"
    
    class Meta:
        verbose_name_plural = "Businesses"

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    @property
    def role_name(self):
        return self.role.get_name_display() if self.role else None
    

class AuditLog(models.Model):
    """Track all user actions in the system"""
    
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    MODULE_CHOICES = [
        ('auth', 'Authentication'),
        ('financials', 'Financials'),
        ('inventory', 'Inventory'),
        ('sales', 'Sales'),
        ('hr', 'Human Resources'),
        ('bi', 'Business Intelligence'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']    