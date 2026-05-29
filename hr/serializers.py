# hr/serializers.py

from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Department, Employee, Salary, Payroll, PayrollItem, LeaveType, LeaveRequest

class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True).count()


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'employee_number']


class CreateEmployeeSerializer(serializers.Serializer):
    """Serializer for creating employee with auto user creation"""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    job_title = serializers.CharField(max_length=100)
    hire_date = serializers.DateField()
    department_id = serializers.IntegerField(required=False, allow_null=True)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    address = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    employment_type = serializers.CharField(default='full_time')
    bank_name = serializers.CharField(required=False, allow_blank=True)
    bank_account_number = serializers.CharField(required=False, allow_blank=True)
    tin_number = serializers.CharField(required=False, allow_blank=True)
    
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    def validate_email(self, value):
        if Employee.objects.filter(email=value).exists():
            raise serializers.ValidationError("Employee with this email already exists")
        return value


class SalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    gross_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_allowances = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Salary
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollItemSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    
    class Meta:
        model = PayrollItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollSerializer(serializers.ModelSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payroll
        fields = '__all__'
        read_only_fields = ['id', 'processed_date', 'created_at', 'updated_at']


class ProcessPayrollSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    include_commission = serializers.BooleanField(default=True)


class SalesByEmployeeReportSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(required=False)
    month = serializers.IntegerField(required=False)
    year = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)


# ==================== LEAVE MANAGEMENT SERIALIZERS ====================
class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_requested = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'status', 'approved_by', 'approved_date']