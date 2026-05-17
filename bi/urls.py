from django.urls import path
from .views import (
    KPIDashboardView, TrendAnalysisView, TopProductsView,
    SlowMovingProductsView, CustomerInsightsView, SalesForecastView,
    InsightsView, ProfitLossView, ExecutiveDashboardView
)

urlpatterns = [
    path('dashboard/', KPIDashboardView.as_view(), name='kpi-dashboard'),
    path('trends/', TrendAnalysisView.as_view(), name='trends'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('slow-products/', SlowMovingProductsView.as_view(), name='slow-products'),
    path('customer-insights/', CustomerInsightsView.as_view(), name='customer-insights'),
    path('forecast/', SalesForecastView.as_view(), name='forecast'),
    path('insights/', InsightsView.as_view(), name='insights'),
    path('profit-loss/', ProfitLossView.as_view(), name='profit-loss'),
    path('executive/', ExecutiveDashboardView.as_view(), name='executive-dashboard'),
]