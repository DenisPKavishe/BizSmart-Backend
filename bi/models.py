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
    data = models.JSONField()  # Stored JSON data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['business', 'report_type', 'period_start', 'period_end']
    
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
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.business.name} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']