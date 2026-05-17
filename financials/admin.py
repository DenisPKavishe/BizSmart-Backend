from django.contrib import admin
from django.db.models import F
from .models import (
    Transaction, Invoice, InvoiceItem, Loan, 
    PettyCash, CashFlowForecast
)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'business', 'type', 'cost_type', 'category', 
        'amount', 'transaction_date'
    ]
    list_filter = ['type', 'cost_type', 'category', 'transaction_date']
    search_fields = ['business__name', 'description']
    date_hierarchy = 'transaction_date'
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'created_by', 'type', 'cost_type', 'category')
        }),
        ('Financial Details', {
            'fields': ('amount', 'quantity', 'description')
        }),
        ('Date & Receipt', {
            'fields': ('transaction_date', 'receipt_image')
        }),
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['description', 'quantity', 'unit_price', 'total']
    readonly_fields = ['total']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer_name', 'total_amount', 
        'amount_paid', 'status', 'due_date'
    ]
    list_filter = ['status', 'issue_date', 'due_date']
    search_fields = ['invoice_number', 'customer_name', 'customer_email']
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Invoice Info', {
            'fields': ('business', 'created_by', 'invoice_number', 'status')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'payment_date')
        }),
        ('Financials', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid')
        }),
        ('Payment', {
            'fields': ('payment_method', 'notes')
        }),
    )


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        'business', 'lender_name', 'loan_type', 
        'principal_amount', 'amount_paid', 'monthly_payment', 'status'
    ]
    list_filter = ['loan_type', 'status', 'start_date']
    search_fields = ['lender_name', 'business__name']
    
    fieldsets = (
        ('Loan Details', {
            'fields': ('business', 'created_by', 'lender_name', 'loan_type')
        }),
        ('Loan Terms', {
            'fields': ('principal_amount', 'interest_rate', 'term_months', 'monthly_payment')
        }),
        ('Payment Tracking', {
            'fields': ('amount_paid', 'next_payment_date', 'status')
        }),
        ('Dates', {
            'fields': ('start_date',)
        })
    )


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ['business', 'amount', 'purpose', 'category', 'approved_by', 'date']
    list_filter = ['category', 'date']
    search_fields = ['purpose', 'approved_by', 'business__name']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Petty Cash Entry', {
            'fields': ('business', 'created_by', 'amount', 'purpose', 'category')
        }),
        ('Approval', {
            'fields': ('approved_by', 'receipt_image')
        }),
        ('Date', {
            'fields': ('date',)
        })
    )


@admin.register(CashFlowForecast)
class CashFlowForecastAdmin(admin.ModelAdmin):
    list_display = [
        'business', 'forecast_date', 'expected_income', 
        'expected_expenses', 'opening_balance'
    ]
    list_filter = ['forecast_date']
    search_fields = ['business__name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Forecast Details', {
            'fields': ('business', 'created_by', 'forecast_date')
        }),
        ('Cash Flow Projections', {
            'fields': ('expected_income', 'expected_expenses', 'opening_balance')
        }),
    )


# Custom admin actions
@admin.action(description='Mark selected invoices as paid')
def mark_invoice_as_paid(modeladmin, request, queryset):
    from django.utils import timezone
    updated = queryset.update(status='paid', payment_date=timezone.now().date())
    modeladmin.message_user(request, f'{updated} invoices marked as paid.')


@admin.action(description='Mark selected invoices as overdue')
def mark_invoice_as_overdue(modeladmin, request, queryset):
    updated = queryset.update(status='overdue')
    modeladmin.message_user(request, f'{updated} invoices marked as overdue.')


# Add actions to InvoiceAdmin
InvoiceAdmin.actions = [mark_invoice_as_paid, mark_invoice_as_overdue]


# Admin site customization
admin.site.site_header = 'BizSmart Management'
admin.site.site_title = 'BizSmart Admin'
admin.site.index_title = 'Welcome to BizSmart'