# bi/serializers.py

from rest_framework import serializers

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


class InsightSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    recommendation = serializers.CharField()
    metric_value = serializers.FloatField(allow_null=True)
    created_at = serializers.DateTimeField()
    is_read = serializers.BooleanField()


class ProfitLossSerializer(serializers.Serializer):
    period = serializers.DictField()
    income = serializers.DictField()
    expenses = serializers.DictField()
    profit = serializers.DictField()