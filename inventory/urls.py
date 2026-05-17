from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    SupplierListCreateView, SupplierDetailView,
    ProductListCreateView, ProductDetailView,
    LowStockProductsView,
    StockInView, StockOutView, StockMovementListView,
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
    
    # Stock Movements
    path('stock/in/', StockInView.as_view(), name='stock-in'),
    path('stock/out/', StockOutView.as_view(), name='stock-out'),
    path('stock/movements/', StockMovementListView.as_view(), name='stock-movements'),
    
    # Purchase Orders
    path('purchase-orders/', PurchaseOrderListCreateView.as_view(), name='purchase-orders'),
    path('purchase-orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('purchase-orders/<int:pk>/receive/', ReceivePurchaseOrderView.as_view(), name='receive-po'),
]