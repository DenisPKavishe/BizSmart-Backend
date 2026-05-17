from django.urls import path
from .views import (
    # Transactions
    TransactionListCreateView,
    TransactionDetailView,
    # Invoices
    InvoiceListCreateView,
    InvoiceDetailView,
    RecordPaymentView,
    # Loans
    LoanListCreateView,
    LoanDetailView,
    # Petty Cash
    PettyCashListCreateView,
    PettyCashDetailView,
    # Cash Flow
    CashFlowForecastView,
    # Dashboard
    CompleteFinancialDashboardView,
    # Export
    ExportFinancialReportView
)

urlpatterns = [
    # Transactions
    path('transactions/', TransactionListCreateView.as_view(), name='transactions'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
    
    # Invoices
    path('invoices/', InvoiceListCreateView.as_view(), name='invoices'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/pay/', RecordPaymentView.as_view(), name='record-payment'),
    
    # Loans
    path('loans/', LoanListCreateView.as_view(), name='loans'),
    path('loans/<int:pk>/', LoanDetailView.as_view(), name='loan-detail'),
    
    # Petty Cash (Full CRUD)
    path('petty-cash/', PettyCashListCreateView.as_view(), name='petty-cash'),
    path('petty-cash/<int:pk>/', PettyCashDetailView.as_view(), name='petty-cash-detail'),
    
    # Cash Flow
    path('cash-flow/', CashFlowForecastView.as_view(), name='cash-flow'),
    
    # Dashboard
    path('dashboard/', CompleteFinancialDashboardView.as_view(), name='financial-dashboard'),
    
    # Export
    path('export/', ExportFinancialReportView.as_view(), name='export-report'),
]