from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import Business, User, Role
from sales.models import Sale
from financials.models import Transaction
from .models import Department, Employee, Salary, Payroll, PayrollItem
from .serializers import (
    DepartmentSerializer, EmployeeSerializer, CreateEmployeeSerializer,
    SalarySerializer, PayrollSerializer, PayrollItemSerializer,
    ProcessPayrollSerializer, SalesByEmployeeReportSerializer
)
from .permissions import (
    CanViewHR, CanManageEmployees, CanViewSalaries, CanManageSalaries,
    CanProcessPayroll, CanViewHRReports, IsAuditorHRReadOnly
)


# ==================== DEPARTMENTS ====================
class DepartmentListCreateView(generics.ListCreateAPIView):
    """
    List all departments or create a new department.
    
    - View: Owner, Manager, Accountant, Auditor
    - Create/Edit: Owner, Accountant only
    """
    serializer_class = DepartmentSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Department.objects.none()
        return Department.objects.filter(business=self.request.user.business)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a department.
    
    - View: Owner, Manager, Accountant, Auditor
    - Update/Delete: Owner, Accountant only
    """
    serializer_class = DepartmentSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Department.objects.filter(business=self.request.user.business)


# ==================== EMPLOYEES ====================
class EmployeeListCreateView(generics.ListCreateAPIView):
    """
    List all employees or create a new employee.
    
    - View: Owner, Manager, Accountant, Auditor
    - Create: Owner, Accountant only
    """
    serializer_class = EmployeeSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Employee.objects.none()
        return Employee.objects.filter(business=self.request.user.business)
    
    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        
        serializer = CreateEmployeeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        business = request.user.business
        
        # Get or create employee number
        employee_count = Employee.objects.filter(business=business).count() + 1
        employee_number = f"EMP-{business.id}-{employee_count:04d}"
        
        # Get department and role
        department = None
        if data.get('department_id'):
            try:
                department = Department.objects.get(id=data['department_id'], business=business)
            except Department.DoesNotExist:
                return Response({'error': 'Department not found'}, status=404)
        
        role = None
        if data.get('role_id'):
            try:
                role = Role.objects.get(id=data['role_id'])
            except Role.DoesNotExist:
                return Response({'error': 'Role not found'}, status=404)
        
        # Create employee
        employee = Employee.objects.create(
            business=business,
            employee_number=employee_number,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data['phone'],
            job_title=data['job_title'],
            hire_date=data['hire_date'],
            department=department,
            role=role,
            commission_rate=data.get('commission_rate', 0),
            address=data.get('address', ''),
            gender=data.get('gender', ''),
            date_of_birth=data.get('date_of_birth'),
            employment_type=data.get('employment_type', 'full_time'),
            bank_name=data.get('bank_name', ''),
            bank_account_number=data.get('bank_account_number', ''),
            tin_number=data.get('tin_number', ''),
            is_active=True
        )
        
        # Create user account
        password = data.get('password', None)
        user, created_password = employee.create_user_account(password)
        
        return Response({
            'message': 'Employee created successfully',
            'employee': EmployeeSerializer(employee).data,
            'user': {
                'email': user.email,
                'username': user.username,
                'password': created_password if created_password else 'User already had account'
            }
        }, status=status.HTTP_201_CREATED)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an employee.
    
    - View: Owner, Manager, Accountant, Auditor
    - Update: Owner, Accountant only
    - Delete: Owner, Accountant only (deactivates)
    """
    serializer_class = EmployeeSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Employee.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        self.check_permissions(request)
        
        employee = self.get_object()
        # Deactivate instead of delete
        employee.is_active = False
        employee.termination_date = timezone.now().date()
        employee.save()
        
        # Deactivate user if exists
        if employee.user:
            employee.user.is_active = False
            employee.user.save()
        
        return Response({'message': 'Employee deactivated successfully'})


# ==================== SALARIES ====================
class SalaryListCreateView(generics.ListCreateAPIView):
    """
    List all salaries or create a new salary.
    
    - View: Owner, Accountant, Auditor
    - Create: Owner, Accountant only
    """
    serializer_class = SalarySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Salary.objects.none()
        return Salary.objects.filter(employee__business=self.request.user.business)
    
    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        
        data = request.data
        business = request.user.business
        
        try:
            employee = Employee.objects.get(id=data['employee_id'], business=business)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=404)
        
        salary = Salary.objects.create(
            employee=employee,
            effective_date=data['effective_date'],
            base_salary=data['base_salary'],
            housing_allowance=data.get('housing_allowance', 0),
            transport_allowance=data.get('transport_allowance', 0),
            meal_allowance=data.get('meal_allowance', 0),
            communication_allowance=data.get('communication_allowance', 0),
            risk_allowance=data.get('risk_allowance', 0),
            other_allowance=data.get('other_allowance', 0),
            paye_tax=data.get('paye_tax', 0),
            sdl=data.get('sdl', 0),
            wcf=data.get('wcf', 0),
            pension_contribution=data.get('pension_contribution', 0),
            health_insurance=data.get('health_insurance', 0),
            loan_deduction=data.get('loan_deduction', 0),
            other_deduction=data.get('other_deduction', 0),
        )
        
        return Response(SalarySerializer(salary).data, status=status.HTTP_201_CREATED)


class SalaryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a salary.
    
    - View: Owner, Accountant, Auditor
    - Update/Delete: Owner, Accountant only
    """
    serializer_class = SalarySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Salary.objects.filter(employee__business=self.request.user.business)


# ==================== PAYROLL ====================
class PayrollListCreateView(generics.ListAPIView):
    """
    List all payrolls.
    
    - View: Owner, Accountant, Auditor
    - Create: Use /process/ endpoint
    """
    serializer_class = PayrollSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payroll.objects.none()
        return Payroll.objects.filter(business=self.request.user.business)
    
    def create(self, request, *args, **kwargs):
        return Response({
            'error': 'Use POST /api/v1/hr/payroll/process/ to process payroll'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class PayrollDetailView(generics.RetrieveAPIView):
    """
    Retrieve payroll details.
    
    Access: Owner, Accountant, Auditor
    """
    serializer_class = PayrollSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Payroll.objects.filter(business=self.request.user.business)


class ProcessPayrollView(APIView):
    """
    Process monthly payroll.
    
    Access: Owner, Accountant only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanProcessPayroll(), IsAuditorHRReadOnly()]
    
    @transaction.atomic
    def post(self, request):
        self.check_permissions(request)
        
        serializer = ProcessPayrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        business = request.user.business
        month = data['month']
        year = data['year']
        include_commission = data.get('include_commission', True)
        
        # Check if payroll already exists
        if Payroll.objects.filter(business=business, month=month, year=year).exists():
            return Response({
                'error': f'Payroll for {month}/{year} already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get active employees
        employees = Employee.objects.filter(
            business=business,
            is_active=True,
            hire_date__lte=datetime(year, month, 1)
        )
        
        if not employees.exists():
            return Response({'error': 'No active employees found'}, status=400)
        
        # Create payroll header
        payroll = Payroll.objects.create(
            business=business,
            month=month,
            year=year,
            processed_by=request.user,
            status='processed'
        )
        
        # Get date range for sales
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        total_base = Decimal('0')
        total_allowances = Decimal('0')
        total_commission = Decimal('0')
        total_deductions = Decimal('0')
        total_net = Decimal('0')
        
        for employee in employees:
            # Get current salary
            current_salary = employee.salaries.filter(
                effective_date__lte=start_date
            ).order_by('-effective_date').first()
            
            if not current_salary:
                continue
            
            # Calculate sales for this employee
            employee_sales = Sale.objects.filter(
                business=business,
                employee=employee,
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date,
                status='completed'
            )
            
            total_sales = employee_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            transaction_count = employee_sales.count()
            
            # Calculate commission
            commission = Decimal('0')
            if include_commission and employee.commission_rate > 0:
                commission = total_sales * (employee.commission_rate / 100)
            
            # Calculate gross and net
            gross = current_salary.base_salary + current_salary.total_allowances + commission
            net = gross - current_salary.total_deductions
            
            # Create payroll item
            PayrollItem.objects.create(
                payroll=payroll,
                employee=employee,
                salary=current_salary,
                base_salary=current_salary.base_salary,
                total_allowances=current_salary.total_allowances,
                commission_amount=commission,
                gross_salary=gross,
                total_deductions=current_salary.total_deductions,
                net_salary=net,
                total_sales_for_month=total_sales,
                total_transactions=transaction_count
            )
            
            total_base += current_salary.base_salary
            total_allowances += current_salary.total_allowances
            total_commission += commission
            total_deductions += current_salary.total_deductions
            total_net += net
        
        # Update payroll totals
        payroll.total_base_salary = total_base
        payroll.total_allowances = total_allowances
        payroll.total_commission = total_commission
        payroll.total_deductions = total_deductions
        payroll.total_net_salary = total_net
        payroll.save()
        
        # Create financial transaction
        transaction = Transaction.objects.create(
            business=business,
            created_by=request.user,
            type='expense',
            cost_type='fixed',
            category='salaries',
            amount=total_net,
            description=f"Payroll for {month}/{year} - {employees.count()} employees",
            transaction_date=timezone.now().date()
        )
        
        payroll.transaction = transaction
        payroll.save()
        
        return Response({
            'message': f'Payroll for {month}/{year} processed successfully',
            'payroll': PayrollSerializer(payroll).data,
            'summary': {
                'total_employees': employees.count(),
                'total_base_salary': float(total_base),
                'total_allowances': float(total_allowances),
                'total_commission': float(total_commission),
                'total_deductions': float(total_deductions),
                'total_net_salary': float(total_net)
            }
        }, status=status.HTTP_201_CREATED)


class MarkPayrollPaidView(APIView):
    """
    Mark payroll as paid.
    
    Access: Owner, Accountant only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanProcessPayroll(), IsAuditorHRReadOnly()]
    
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            payroll = Payroll.objects.get(pk=pk, business=request.user.business)
        except Payroll.DoesNotExist:
            return Response({'error': 'Payroll not found'}, status=404)
        
        if payroll.status == 'paid':
            return Response({'error': 'Payroll already marked as paid'}, status=400)
        
        payroll.status = 'paid'
        payroll.save()
        
        # Update transaction paid date if needed
        if payroll.transaction:
            payroll.transaction.transaction_date = timezone.now().date()
            payroll.transaction.save()
        
        return Response({
            'message': f'Payroll for {payroll.month}/{payroll.year} marked as paid'
        })


# ==================== REPORTS ====================
class SalesByEmployeeReportView(APIView):
    """
    Report of sales by employee.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewHRReports(), IsAuditorHRReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        business = request.user.business
        
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        employee_id = request.query_params.get('employee_id')
        
        # Build date filter
        if start_date and end_date:
            date_filter = Q(sale_date__date__gte=start_date, sale_date__date__lte=end_date)
        elif month and year:
            date_filter = Q(sale_date__month=month, sale_date__year=year)
        else:
            # Default to current month
            today = timezone.now()
            date_filter = Q(sale_date__month=today.month, sale_date__year=today.year)
        
        # Base query
        sales_query = Sale.objects.filter(
            business=business,
            status='completed',
            employee__isnull=False
        ).filter(date_filter)
        
        if employee_id:
            sales_query = sales_query.filter(employee_id=employee_id)
        
        # Aggregate by employee
        employee_sales = sales_query.values(
            'employee__id',
            'employee__first_name',
            'employee__last_name',
            'employee__employee_number',
            'employee__job_title',
            'employee__commission_rate'
        ).annotate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id'),
            total_items=Sum('items__quantity')
        ).order_by('-total_sales')
        
        results = []
        for emp in employee_sales:
            commission = Decimal('0')
            if emp['employee__commission_rate'] > 0:
                commission = emp['total_sales'] * (emp['employee__commission_rate'] / 100)
            
            results.append({
                'employee_id': emp['employee__id'],
                'employee_name': f"{emp['employee__first_name']} {emp['employee__last_name']}",
                'employee_number': emp['employee__employee_number'],
                'job_title': emp['employee__job_title'],
                'commission_rate': float(emp['employee__commission_rate']),
                'total_sales': float(emp['total_sales']),
                'total_transactions': emp['total_transactions'],
                'total_items': emp['total_items'] or 0,
                'commission_amount': float(commission)
            })
        
        return Response({
            'filter': {
                'month': month,
                'year': year,
                'start_date': start_date,
                'end_date': end_date
            },
            'total_employees': len(results),
            'total_sales_all': sum(r['total_sales'] for r in results),
            'total_commission_all': sum(r['commission_amount'] for r in results),
            'employees': results
        })


class TopPerformersReportView(APIView):
    """
    Top performing employees by sales.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewHRReports(), IsAuditorHRReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        business = request.user.business
        limit = int(request.query_params.get('limit', 10))
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        sales_by_employee = Sale.objects.filter(
            business=business,
            status='completed',
            employee__isnull=False,
            sale_date__date__gte=start_date
        ).values('employee__id', 'employee__first_name', 'employee__last_name').annotate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id')
        ).order_by('-total_sales')[:limit]
        
        results = []
        for idx, emp in enumerate(sales_by_employee, 1):
            results.append({
                'rank': idx,
                'employee_id': emp['employee__id'],
                'employee_name': f"{emp['employee__first_name']} {emp['employee__last_name']}",
                'total_sales': float(emp['total_sales']),
                'total_transactions': emp['total_transactions']
            })
        
        return Response({
            'period': f'Last {days} days',
            'top_performers': results
        })


class PayrollReportView(APIView):
    """
    Get payroll report.
    
    Access: Owner, Accountant, Auditor
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        business = request.user.business
        year = request.query_params.get('year')
        
        if not year:
            year = timezone.now().year
        
        payrolls = Payroll.objects.filter(
            business=business,
            year=year
        ).order_by('month')
        
        monthly_data = []
        for payroll in payrolls:
            monthly_data.append({
                'month': payroll.month,
                'month_name': datetime(payroll.year, payroll.month, 1).strftime('%B'),
                'total_employees': payroll.items.count(),
                'total_base_salary': float(payroll.total_base_salary),
                'total_allowances': float(payroll.total_allowances),
                'total_commission': float(payroll.total_commission),
                'total_deductions': float(payroll.total_deductions),
                'total_net_salary': float(payroll.total_net_salary),
                'status': payroll.status
            })
        
        totals = {
            'total_base_salary': sum(m['total_base_salary'] for m in monthly_data),
            'total_allowances': sum(m['total_allowances'] for m in monthly_data),
            'total_commission': sum(m['total_commission'] for m in monthly_data),
            'total_deductions': sum(m['total_deductions'] for m in monthly_data),
            'total_net_salary': sum(m['total_net_salary'] for m in monthly_data)
        }
        
        return Response({
            'year': year,
            'monthly_breakdown': monthly_data,
            'annual_totals': totals
        })