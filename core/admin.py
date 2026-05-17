from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Role, Business, User
from .models import AuditLog

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']
    
    fieldsets = (
        ('Role Information', {
            'fields': ('name', 'description')
        }),
    )


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'city_display', 'phone', 'email', 'created_at']
    list_filter = ['city', 'created_at']
    search_fields = ['name', 'registration_number', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Business Information', {
            'fields': ('name', 'registration_number', 'city')
        }),
        ('Contact Details', {
            'fields': ('phone', 'email', 'address', 'postal_code')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def city_display(self, obj):
        return obj.get_city_display()
    city_display.short_description = 'City'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'role_display', 'business_link', 'is_active', 'is_superuser', 'last_login']
    list_filter = ['role', 'is_active', 'business', 'is_superuser']
    search_fields = ['email', 'username', 'phone']
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('BizSmart Info', {
            'fields': ('role', 'business', 'phone'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('BizSmart Info', {
            'fields': ('role', 'business', 'phone'),
        }),
    )
    
    def role_display(self, obj):
        if obj.role:
            return format_html(
                '<span style="color: blue;">{}</span>',
                obj.role.get_name_display()
            )
        return '-'
    role_display.short_description = 'Role'
    
    def business_link(self, obj):
        if obj.business:
            return format_html(
                '<a href="/admin/core/business/{}/change/">{}</a>',
                obj.business.id, obj.business.name
            )
        return '-'
    business_link.short_description = 'Business'
    
    actions = ['activate_users', 'deactivate_users']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'


# Register Inventory Models in Core Admin (Optional)
# This makes inventory appear under Core section if you want
# Comment out if you want inventory in its own section

from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered

# Try to register inventory models (if they exist)
try:
    from inventory.models import Category, Supplier, Product, StockMovement, PurchaseOrder, PurchaseOrderItem
    from inventory.admin import (
        CategoryAdmin, SupplierAdmin, ProductAdmin, 
        StockMovementAdmin, PurchaseOrderAdmin, PurchaseOrderItemAdmin
    )
    
    admin.site.register(Category, CategoryAdmin)
    admin.site.register(Supplier, SupplierAdmin)
    admin.site.register(Product, ProductAdmin)
    admin.site.register(StockMovement, StockMovementAdmin)
    admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
    admin.site.register(PurchaseOrderItem, PurchaseOrderItemAdmin)
except (ImportError, AlreadyRegistered):
    pass

# Try to register financials models (if they exist)
try:
    from financials.models import Transaction, Invoice, Loan, PettyCash, CashFlowForecast
    from financials.admin import (
        TransactionAdmin, InvoiceAdmin, LoanAdmin, 
        PettyCashAdmin, CashFlowForecastAdmin
    )
    
    admin.site.register(Transaction, TransactionAdmin)
    admin.site.register(Invoice, InvoiceAdmin)
    admin.site.register(Loan, LoanAdmin)
    admin.site.register(PettyCash, PettyCashAdmin)
    admin.site.register(CashFlowForecast, CashFlowForecastAdmin)
except (ImportError, AlreadyRegistered):
    pass





@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'action', 'module', 'description', 'ip_address']
    list_filter = ['action', 'module', 'created_at']
    search_fields = ['user__email', 'description']
    readonly_fields = ['created_at', 'user', 'action', 'module', 'description', 'details', 'ip_address', 'user_agent']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False