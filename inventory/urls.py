# inventory/urls.py

from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    SupplierListCreateView, SupplierDetailView,
    ProductListCreateView, ProductDetailView,
    LowStockProductsView, ProductByBarcodeView, StockValuationReportView,
    GenerateProductBarcodeView, BulkGenerateBarcodesView,
    PrintBarcodeLabelView, BulkPrintBarcodeLabelsView,
    StockInView, StockOutView, StockMovementListView, StockMovementReportView,
    PurchaseOrderListCreateView, PurchaseOrderDetailView,
    ReceivePurchaseOrderView
)

urlpatterns = [
    # Categories
    path('categories/', CategoryListCreateView.as_view(), name='categories'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Suppliers
    path('suppliers/', SupplierListCreateView.as_view(), name='suppliers'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),
    
    # Products
    path('products/', ProductListCreateView.as_view(), name='products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/low-stock/', LowStockProductsView.as_view(), name='low-stock'),
    path('products/barcode/<str:barcode>/', ProductByBarcodeView.as_view(), name='product-by-barcode'),
    path('products/stock-valuation/', StockValuationReportView.as_view(), name='stock-valuation'),
    
    # Barcode Generation
    path('products/<int:pk>/generate-barcode/', GenerateProductBarcodeView.as_view(), name='generate-barcode'),
    path('products/bulk-generate-barcodes/', BulkGenerateBarcodesView.as_view(), name='bulk-generate-barcodes'),
    path('products/<int:pk>/print-label/', PrintBarcodeLabelView.as_view(), name='print-label'),
    path('products/bulk-print-labels/', BulkPrintBarcodeLabelsView.as_view(), name='bulk-print-labels'),
    
    # Stock Movements
    path('stock/in/', StockInView.as_view(), name='stock-in'),
    path('stock/out/', StockOutView.as_view(), name='stock-out'),
    path('stock/movements/', StockMovementListView.as_view(), name='stock-movements'),
    path('stock/movements/report/', StockMovementReportView.as_view(), name='stock-movements-report'),
    
    # Purchase Orders
    path('purchase-orders/', PurchaseOrderListCreateView.as_view(), name='purchase-orders'),
    path('purchase-orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('purchase-orders/<int:pk>/receive/', ReceivePurchaseOrderView.as_view(), name='receive-po'),
]