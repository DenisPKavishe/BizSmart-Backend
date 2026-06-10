# bi/serializers.py

from rest_framework import serializers
from .models import BusinessInsight, BusinessGoal, DashboardWidget


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessInsight
        fields = ['id', 'insight_type', 'category', 'title', 'description', 
                  'recommendation', 'metric_value', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']


class GoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessGoal
        fields = ['id', 'name', 'description', 'category', 'target_amount', 
                  'current_amount', 'progress_percentage', 'remaining_amount',
                  'start_date', 'target_date', 'is_completed']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_progress_percentage(self, obj):
        if obj.target_amount > 0:
            return min(100, float((obj.current_amount / obj.target_amount) * 100))
        return 0
    
    def get_remaining_amount(self, obj):
        return float(obj.target_amount - obj.current_amount)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = ['id', 'widget_type', 'title', 'config', 'position', 
                  'is_visible', 'width', 'height']
        read_only_fields = ['id', 'created_at', 'updated_at']


# Dashboard Response Serializers
class KPIDashboardSerializer(serializers.Serializer):
    period = serializers.DictField()
    revenue = serializers.DictField()
    expenses = serializers.DictField()
    profit = serializers.DictField()
    margins = serializers.DictField()
    inventory = serializers.DictField()
    sales = serializers.DictField()
    customers = serializers.DictField()
    employees = serializers.DictField()


class TrendSerializer(serializers.Serializer):
    daily = serializers.ListField()
    weekly = serializers.ListField()
    monthly = serializers.ListField()
    summary = serializers.DictField()


class TopProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField()
    selling_price = serializers.FloatField()
    quantity_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    profit = serializers.FloatField()
    profit_margin = serializers.FloatField()


class CustomerInsightSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    segments = serializers.DictField()
    retention_rate = serializers.FloatField()
    repeat_customers = serializers.IntegerField()
    top_customers = serializers.ListField()


class SalesForecastSerializer(serializers.Serializer):
    period = serializers.CharField()
    forecast = serializers.ListField()
    total_forecast = serializers.FloatField()
    average_daily_forecast = serializers.FloatField()
    confidence = serializers.FloatField()
    based_on_days = serializers.IntegerField()


class ProfitLossSerializer(serializers.Serializer):
    period = serializers.DictField()
    income = serializers.DictField()
    expenses = serializers.DictField()
    profit = serializers.DictField()


class InventoryAnalyticsSerializer(serializers.Serializer):
    inventory_summary = serializers.DictField()
    top_products = serializers.ListField()
    slow_moving_products = serializers.ListField()
    stock_status = serializers.DictField()


class HRAnalyticsSerializer(serializers.Serializer):
    employee_summary = serializers.DictField()
    department_distribution = serializers.ListField()
    attendance_rate = serializers.FloatField()
    upcoming_leave = serializers.ListField()
    payroll_summary = serializers.DictField()