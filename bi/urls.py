# bi/urls.py

from django.urls import path
from .views import (
    KPIDashboardView, TrendAnalysisView, TopProductsView,
    SlowMovingProductsView, CustomerInsightsView, SalesForecastView,
    InsightsView, ProfitLossView, ExecutiveDashboardView,
    InventoryAnalyticsView, FinancialSummaryView, SalesPerformanceView,
    MarkInsightReadView, ClearCacheView
)

urlpatterns = [
    # Main Dashboards
    path('dashboard/', KPIDashboardView.as_view(), name='kpi-dashboard'),
    path('executive/', ExecutiveDashboardView.as_view(), name='executive-dashboard'),
    
    # Trends & Analytics
    path('trends/', TrendAnalysisView.as_view(), name='trends'),
    path('profit-loss/', ProfitLossView.as_view(), name='profit-loss'),
    path('forecast/', SalesForecastView.as_view(), name='forecast'),
    
    # Sales Analytics
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('sales-performance/', SalesPerformanceView.as_view(), name='sales-performance'),
    
    # Inventory Analytics
    path('slow-products/', SlowMovingProductsView.as_view(), name='slow-products'),
    path('inventory-analytics/', InventoryAnalyticsView.as_view(), name='inventory-analytics'),
    
    # Customer Analytics
    path('customer-insights/', CustomerInsightsView.as_view(), name='customer-insights'),
    
    # Financial Analytics
    path('financial-summary/', FinancialSummaryView.as_view(), name='financial-summary'),
    
    # Insights
    path('insights/', InsightsView.as_view(), name='insights'),
    path('insights/<int:pk>/mark-read/', MarkInsightReadView.as_view(), name='mark-insight-read'),
    
    # Cache Management
    path('clear-cache/', ClearCacheView.as_view(), name='clear-cache'),
]