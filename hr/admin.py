from django.contrib import admin
from .models import Department, Employee, Salary, Payroll, PayrollItem

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'manager', 'created_at']
    list_filter = ['business']
    search_fields = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'full_name', 'job_title', 'department', 'is_active', 'phone']
    list_filter = ['is_active', 'department', 'employment_type', 'business']
    search_fields = ['employee_number', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('business', 'employee_number', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Employment', {
            'fields': ('department', 'job_title', 'employment_type', 'hire_date', 'termination_date', 'is_active')
        }),
        ('Commission', {
            'fields': ('commission_rate',)
        }),
        ('User Account', {
            'fields': ('user', 'role'),
            'classes': ('collapse',)
        }),
        ('Banking', {
            'fields': ('bank_name', 'bank_account_number', 'tin_number'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'effective_date', 'base_salary', 'total_allowances', 'total_deductions', 'net_salary']
    list_filter = ['effective_date']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['total_allowances', 'total_deductions', 'gross_salary', 'net_salary']
    
    fieldsets = (
        ('Salary Information', {
            'fields': ('employee', 'effective_date', 'base_salary')
        }),
        ('Allowances', {
            'fields': ('housing_allowance', 'transport_allowance', 'meal_allowance', 
                       'communication_allowance', 'risk_allowance', 'other_allowance'),
            'classes': ('collapse',)
        }),
        ('Deductions', {
            'fields': ('paye_tax', 'sdl', 'wcf', 'pension_contribution', 
                       'health_insurance', 'loan_deduction', 'other_deduction'),
            'classes': ('collapse',)
        }),
        ('Calculated Values', {
            'fields': ('total_allowances', 'total_deductions', 'gross_salary', 'net_salary'),
            'classes': ('collapse',)
        }),
    )
    
    def total_allowances(self, obj):
        return obj.total_allowances
    total_allowances.short_description = 'Total Allowances'
    
    def total_deductions(self, obj):
        return obj.total_deductions
    total_deductions.short_description = 'Total Deductions'
    
    def gross_salary(self, obj):
        return obj.gross_salary
    gross_salary.short_description = 'Gross Salary'
    
    def net_salary(self, obj):
        return obj.net_salary
    net_salary.short_description = 'Net Salary'


class PayrollItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 0
    fields = ['employee', 'base_salary', 'commission_amount', 'net_salary']
    readonly_fields = ['employee', 'base_salary', 'commission_amount', 'net_salary']
    can_delete = False
    show_change_link = True


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['business', 'month', 'year', 'total_net_salary', 'status', 'processed_date']
    list_filter = ['status', 'year', 'month', 'business']
    readonly_fields = ['processed_date', 'total_base_salary', 'total_allowances', 
                       'total_commission', 'total_deductions', 'total_net_salary']
    inlines = [PayrollItemInline]
    
    def has_add_permission(self, request):
        return False  # Payroll created via API only


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'employee', 'base_salary', 'commission_amount', 'net_salary']
    list_filter = ['payroll__status']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['base_salary', 'total_allowances', 'commission_amount', 
                       'gross_salary', 'total_deductions', 'net_salary']
    
    def has_add_permission(self, request):
        return False  # Payroll items created via API only