# bi/urls.py

from django.urls import path
from .views import (
    # Main Dashboard
    MainDashboardView,
    DashboardTrendsView,
    DashboardAlertsView,
    DashboardMilestonesView,
    AvailableMonthsView,
    
    # KPI Dashboard
    KPIDashboardView,
    TrendAnalysisView,
    
    # Sales Analytics
    TopProductsView,
    SalesPerformanceView,
    SalesForecastView,
    
    # Inventory Analytics
    InventoryAnalyticsView,
    SlowMovingProductsView,
    
    # Customer Analytics
    CustomerInsightsView,
    
    # Financial Analytics
    FinancialSummaryView,
    ProfitLossView,
    
    # HR Analytics
    HRAnalyticsView,
    
    # Insights
    InsightsView,
    MarkInsightReadView,
    
    # Goals
    GoalsListView,
    GoalDetailView,
    
    # Dashboard Widgets
    DashboardWidgetsView,
    DashboardWidgetReorderView,
    
    # Executive Dashboard
    ExecutiveDashboardView,
    
    # Cache
    ClearCacheView,
)

urlpatterns = [
    # Main Dashboard
    path('dashboard/', MainDashboardView.as_view(), name='main-dashboard'),
    path('dashboard/trends/', DashboardTrendsView.as_view(), name='dashboard-trends'),
    path('dashboard/alerts/', DashboardAlertsView.as_view(), name='dashboard-alerts'),
    path('dashboard/milestones/', DashboardMilestonesView.as_view(), name='dashboard-milestones'),
    path('dashboard/available-months/', AvailableMonthsView.as_view(), name='available-months'),
    
    # KPI & Trends
    path('kpi/', KPIDashboardView.as_view(), name='kpi-dashboard'),
    path('trends/', TrendAnalysisView.as_view(), name='trends'),
    
    # Sales Analytics
    path('sales/top-products/', TopProductsView.as_view(), name='top-products'),
    path('sales/performance/', SalesPerformanceView.as_view(), name='sales-performance'),
    path('sales/forecast/', SalesForecastView.as_view(), name='forecast'),
    
    # Inventory Analytics
    path('inventory/analytics/', InventoryAnalyticsView.as_view(), name='inventory-analytics'),
    path('inventory/slow-moving/', SlowMovingProductsView.as_view(), name='slow-products'),
    
    # Customer Analytics
    path('customer/insights/', CustomerInsightsView.as_view(), name='customer-insights'),
    
    # Financial Analytics
    path('financial/summary/', FinancialSummaryView.as_view(), name='financial-summary'),
    path('financial/profit-loss/', ProfitLossView.as_view(), name='profit-loss'),
    
    # HR Analytics
    path('hr/analytics/', HRAnalyticsView.as_view(), name='hr-analytics'),
    
    # Insights
    path('insights/', InsightsView.as_view(), name='insights'),
    path('insights/<int:pk>/mark-read/', MarkInsightReadView.as_view(), name='mark-insight-read'),
    
    # Goals
    path('goals/', GoalsListView.as_view(), name='goals-list'),
    path('goals/<int:pk>/', GoalDetailView.as_view(), name='goal-detail'),
    
    # Dashboard Widgets
    path('widgets/', DashboardWidgetsView.as_view(), name='dashboard-widgets'),
    path('widgets/reorder/', DashboardWidgetReorderView.as_view(), name='widgets-reorder'),
    
    # Executive Dashboard
    path('executive/', ExecutiveDashboardView.as_view(), name='executive-dashboard'),
    
    # Cache
    path('clear-cache/', ClearCacheView.as_view(), name='clear-cache'),
]