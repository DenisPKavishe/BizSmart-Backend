# bi/models.py

from django.db import models
from django.conf import settings
from core.models import Business
from decimal import Decimal


class BIReportCache(models.Model):
    """Cache for BI reports to improve performance"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='bi_caches')
    report_type = models.CharField(max_length=50)  # kpi, trends, forecast, etc.
    period_start = models.DateField()
    period_end = models.DateField()
    parameters = models.JSONField(default=dict, blank=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['business', 'report_type', 'period_start', 'period_end', 'parameters']
        indexes = [
            models.Index(fields=['business', 'report_type', '-updated_at']),
            models.Index(fields=['business', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.business.name} - {self.report_type}"


class BusinessInsight(models.Model):
    """Generated insights for the business"""
    INSIGHT_TYPES = [
        ('positive', 'Positive'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('opportunity', 'Opportunity'),
    ]
    
    CATEGORIES = [
        ('sales', 'Sales'),
        ('inventory', 'Inventory'),
        ('financial', 'Financial'),
        ('hr', 'Human Resources'),
        ('customer', 'Customer'),
        ('general', 'General'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    recommendation = models.TextField(blank=True)
    metric_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'is_active', '-created_at']),
            models.Index(fields=['business', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.business.name} - {self.title}"


class BusinessGoal(models.Model):
    """Business goals and targets"""
    CATEGORY_CHOICES = [
        ('revenue', 'Revenue'),
        ('profit', 'Profit'),
        ('customers', 'Customers'),
        ('margin', 'Profit Margin'),
        ('inventory', 'Inventory Turnover'),
        ('employees', 'Employees'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField()
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.target_amount}"


class DashboardWidget(models.Model):
    """Custom dashboard widgets configuration"""
    WIDGET_TYPES = [
        ('metric', 'Metric Card'),
        ('chart', 'Chart'),
        ('table', 'Table'),
        ('insight', 'Insight'),
        ('alert', 'Alert'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='dashboard_widgets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_widgets', null=True, blank=True)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    title = models.CharField(max_length=100)
    config = models.JSONField(default=dict)  # Store widget configuration
    position = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    width = models.IntegerField(default=4)  # 1-12 grid width
    height = models.IntegerField(default=2)  # Row height units
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position']
        unique_together = ['business', 'user', 'position']
    
    def __str__(self):
        user_str = f" - {self.user.username}" if self.user else " (default)"
        return f"{self.title}{user_str}"