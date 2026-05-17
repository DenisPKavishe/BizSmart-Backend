from django.contrib import admin
from .models import Customer, Sale, SaleItem, Return

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ['product', 'quantity', 'unit_price', 'total_price']
    readonly_fields = ['total_price']
    can_delete = False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'total_spent', 'total_visits', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['total_spent', 'total_visits']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'sale_date', 'customer_name', 'total_amount', 'payment_method', 'status']
    list_filter = ['status', 'payment_method', 'sale_date']
    search_fields = ['invoice_number', 'customer__name']
    readonly_fields = ['invoice_number', 'sale_date', 'subtotal', 'discount_amount', 'total_amount', 'change_amount']
    inlines = [SaleItemInline]
    date_hierarchy = 'sale_date'
    
    def customer_name(self, obj):
        return obj.customer.name if obj.customer else 'Walk-in Customer'
    customer_name.short_description = 'Customer'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'product_name', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__sale_date']
    search_fields = ['product__name', 'sale__invoice_number']
    readonly_fields = ['total_price']
    
    def invoice_number(self, obj):
        return obj.sale.invoice_number
    invoice_number.short_description = 'Invoice'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ['id', 'invoice_number', 'product_name', 'quantity_returned', 'refund_amount', 'reason', 'created_at']
    list_filter = ['reason', 'created_at']
    search_fields = ['sale__invoice_number']
    readonly_fields = ['created_at']
    
    def invoice_number(self, obj):
        return obj.sale.invoice_number
    invoice_number.short_description = 'Invoice'
    
    def product_name(self, obj):
        return obj.sale_item.product.name if obj.sale_item else '-'
    product_name.short_description = 'Product'