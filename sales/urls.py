from django.urls import path
from .views import (
    # Customers
    CustomerListCreateView, CustomerDetailView,
    # Sale Items
    SaleItemListCreateView, SaleItemDetailView,
    # Sales
    SaleListCreateView, SaleDetailView, SalePartialUpdateView,
    ProcessSaleView, SaleReceiptView,
    # Returns
    ReturnListCreateView, ReturnDetailView, ProcessReturnView,
    # Reports
    DailySalesReportView, TodaySalesView
)

urlpatterns = [
    # Customers (Full CRUD)
    path('customers/', CustomerListCreateView.as_view(), name='customers'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    
    # Sale Items (Full CRUD)
    path('items/', SaleItemListCreateView.as_view(), name='sale-items'),
    path('items/<int:pk>/', SaleItemDetailView.as_view(), name='sale-item-detail'),
    
    # Sales (Full CRUD)
    path('sales/', SaleListCreateView.as_view(), name='sales'),
    path('sales/<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
    path('sales/<int:pk>/partial/', SalePartialUpdateView.as_view(), name='sale-partial'),
    path('sales/process/', ProcessSaleView.as_view(), name='process-sale'),
    path('sales/<int:pk>/receipt/', SaleReceiptView.as_view(), name='sale-receipt'),
    
    # Returns (Full CRUD)
    path('returns/', ReturnListCreateView.as_view(), name='returns'),
    path('returns/<int:pk>/', ReturnDetailView.as_view(), name='return-detail'),
    path('returns/process/', ProcessReturnView.as_view(), name='process-return'),
    
    # Reports
    path('reports/daily/', DailySalesReportView.as_view(), name='daily-report'),
    path('reports/today/', TodaySalesView.as_view(), name='today-sales'),
]