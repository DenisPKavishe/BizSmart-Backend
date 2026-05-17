from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Supplier, Product, StockMovement, 
    PurchaseOrder, PurchaseOrderItem
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'created_at']
    list_filter = ['business']
    search_fields = ['name', 'business__name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'business']
    list_filter = ['business']
    search_fields = ['name', 'contact_person', 'phone']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'sku', 'name', 'category', 'quantity_on_hand', 
        'buying_price', 'selling_price', 'is_active'
    ]
    list_filter = ['category', 'supplier', 'is_active', 'unit', 'business']
    search_fields = ['sku', 'name', 'barcode']
    readonly_fields = ['total_investment', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'sku', 'name', 'barcode', 'description')
        }),
        ('Category & Supplier', {
            'fields': ('category', 'supplier')
        }),
        ('Pricing', {
            'fields': ('buying_price', 'selling_price')
        }),
        ('Stock Management', {
            'fields': ('quantity_on_hand', 'reorder_level', 'reorder_quantity', 'unit', 'total_investment')
        }),
        ('Status', {
            'fields': ('is_active', 'image')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'category', 'supplier')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'unit_cost', 'total_cost', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'reference_id']
    readonly_fields = ['business', 'product', 'quantity', 'movement_type', 'unit_cost', 
                       'total_cost', 'previous_quantity', 'new_quantity', 'created_by', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ['product', 'quantity', 'unit_cost', 'total_cost', 'quantity_received']
    readonly_fields = ['total_cost']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'total_amount', 'status', 'order_date', 'expected_delivery']
    list_filter = ['status', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['po_number', 'created_at', 'updated_at']
    inlines = [PurchaseOrderItemInline]
    
    fieldsets = (
        ('Purchase Order Information', {
            'fields': ('business', 'po_number', 'supplier', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery', 'actual_delivery')
        }),
        ('Financials', {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        ('Additional', {
            'fields': ('notes', 'created_by')
        }),
    )


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'product', 'quantity', 'unit_cost', 'total_cost', 'quantity_received']
    list_filter = ['purchase_order__status']
    search_fields = ['product__name', 'purchase_order__po_number']
    readonly_fields = ['total_cost']