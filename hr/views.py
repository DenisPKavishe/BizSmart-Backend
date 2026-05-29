# hr/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Sum, Count, Q, F, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import Business, User, Role
from sales.models import Sale
from financials.models import Transaction
from .models import Department, Employee, Salary, Payroll, PayrollItem, LeaveType, LeaveRequest
from .serializers import (
    DepartmentSerializer, EmployeeSerializer, CreateEmployeeSerializer,
    SalarySerializer, PayrollSerializer, PayrollItemSerializer,
    ProcessPayrollSerializer, SalesByEmployeeReportSerializer,
    LeaveTypeSerializer, LeaveRequestSerializer
)
from .permissions import (
    CanViewHR, CanManageEmployees, CanViewSalaries, CanManageSalaries,
    CanProcessPayroll, CanViewHRReports, IsAuditorHRReadOnly, CanManageLeave
)


# ==================== HELPER FUNCTIONS ====================
def generate_employee_number(business_id):
    """Generate unique employee number with lock to prevent race condition"""
    from django.db import transaction as db_transaction
    
    with db_transaction.atomic():
        last_employee = Employee.objects.select_for_update().filter(
            business_id=business_id
        ).order_by('-id').first()
        
        if last_employee and last_employee.employee_number:
            parts = last_employee.employee_number.split('-')
            if len(parts) == 3:
                try:
                    last_num = int(parts[2])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
        else:
            new_num = 1
        
        return f"EMP-{business_id}-{new_num:04d}"


# ==================== DEPARTMENTS ====================
class DepartmentListCreateView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Department.objects.none()
        return Department.objects.filter(business=self.request.user.business, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Department.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        department = self.get_object()
        if department.employees.filter(is_active=True).exists():
            return Response({
                'error': f'Cannot delete department with active employees'
            }, status=400)
        department.is_active = False
        department.save()
        return Response({'message': 'Department deactivated successfully'})


# ==================== EMPLOYEES ====================
class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Employee.objects.none()
        # Optimized with select_related
        return Employee.objects.filter(
            business=self.request.user.business
        ).select_related('department', 'role', 'user')
    
    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        
        serializer = CreateEmployeeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        business = request.user.business
        
        # Generate employee number (fixed race condition)
        employee_number = generate_employee_number(business.id)
        
        department = None
        if data.get('department_id'):
            try:
                department = Department.objects.get(id=data['department_id'], business=business, is_active=True)
            except Department.DoesNotExist:
                return Response({'error': 'Department not found'}, status=404)
        
        role = None
        if data.get('role_id'):
            try:
                role = Role.objects.get(id=data['role_id'])
            except Role.DoesNotExist:
                return Response({'error': 'Role not found'}, status=404)
        
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
    serializer_class = EmployeeSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageEmployees(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Employee.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - deactivate instead of delete"""
        employee = self.get_object()
        reason = request.data.get('reason', '')
        employee.deactivate(reason)
        return Response({'message': 'Employee deactivated successfully'})


# ==================== SALARIES ====================
class SalaryListCreateView(generics.ListCreateAPIView):
    serializer_class = SalarySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Salary.objects.none()
        return Salary.objects.filter(employee__business=self.request.user.business).select_related('employee')
    
    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        
        data = request.data
        business = request.user.business
        
        # Check for duplicate salary month
        effective_date = data.get('effective_date')
        if effective_date:
            from datetime import datetime
            eff_date = datetime.strptime(effective_date, '%Y-%m-%d').date()
            
            existing = Salary.objects.filter(
                employee_id=data['employee_id'],
                effective_date__year=eff_date.year,
                effective_date__month=eff_date.month
            ).exists()
            
            if existing:
                return Response({
                    'error': 'Salary already exists for this employee for this month'
                }, status=400)
        
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
    serializer_class = SalarySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Salary.objects.filter(employee__business=self.request.user.business)


# ==================== PAYROLL ====================
class PayrollListCreateView(generics.ListAPIView):
    serializer_class = PayrollSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payroll.objects.none()
        return Payroll.objects.filter(business=self.request.user.business).prefetch_related('items', 'items__employee')
    
    def create(self, request, *args, **kwargs):
        return Response({
            'error': 'Use POST /api/v1/hr/payroll/process/ to process payroll'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class PayrollDetailView(generics.RetrieveAPIView):
    serializer_class = PayrollSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return Payroll.objects.filter(business=self.request.user.business)


class ProcessPayrollView(APIView):
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
        
        if Payroll.objects.filter(business=business, month=month, year=year).exists():
            return Response({
                'error': f'Payroll for {month}/{year} already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        employees = Employee.objects.filter(
            business=business,
            is_active=True,
            hire_date__lte=datetime(year, month, 1)
        ).select_related('user')
        
        if not employees.exists():
            return Response({'error': 'No active employees found'}, status=400)
        
        payroll = Payroll.objects.create(
            business=business,
            month=month,
            year=year,
            processed_by=request.user,
            status='processed'
        )
        
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
        
        # Optimized: Prefetch sales for all employees at once
        employee_ids = list(employees.values_list('id', flat=True))
        sales_data = Sale.objects.filter(
            business=business,
            employee_id__in=employee_ids,
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            status='completed'
        ).values('employee_id').annotate(
            total_sales=Sum('total_amount'),
            transaction_count=Count('id')
        )
        
        sales_dict = {item['employee_id']: item for item in sales_data}
        
        for employee in employees:
            current_salary = employee.salaries.filter(
                effective_date__lte=start_date
            ).order_by('-effective_date').first()
            
            if not current_salary:
                continue
            
            emp_sales = sales_dict.get(employee.id, {})
            total_sales = emp_sales.get('total_sales', Decimal('0'))
            transaction_count = emp_sales.get('transaction_count', 0)
            
            commission = Decimal('0')
            if include_commission and employee.commission_rate > 0:
                commission = total_sales * (employee.commission_rate / 100)
            
            gross = current_salary.base_salary + current_salary.total_allowances + commission
            net = gross - current_salary.total_deductions
            
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
        
        payroll.total_base_salary = total_base
        payroll.total_allowances = total_allowances
        payroll.total_commission = total_commission
        payroll.total_deductions = total_deductions
        payroll.total_net_salary = total_net
        payroll.save()
        
        transaction_obj = Transaction.objects.create(
            business=business,
            created_by=request.user,
            type='expense',
            cost_type='fixed',
            category='salaries',
            amount=total_net,
            description=f"Payroll for {month}/{year} - {employees.count()} employees",
            transaction_date=timezone.now().date()
        )
        
        payroll.transaction = transaction_obj
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
        
        if payroll.transaction:
            payroll.transaction.transaction_date = timezone.now().date()
            payroll.transaction.save()
        
        return Response({
            'message': f'Payroll for {payroll.month}/{payroll.year} marked as paid'
        })


# ==================== REPORTS ====================
class SalesByEmployeeReportView(APIView):
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
        
        if start_date and end_date:
            date_filter = Q(sale_date__date__gte=start_date, sale_date__date__lte=end_date)
        elif month and year:
            date_filter = Q(sale_date__month=month, sale_date__year=year)
        else:
            today = timezone.now()
            date_filter = Q(sale_date__month=today.month, sale_date__year=today.year)
        
        sales_query = Sale.objects.filter(
            business=business,
            status='completed',
            employee__isnull=False
        ).filter(date_filter).select_related('employee')
        
        if employee_id:
            sales_query = sales_query.filter(employee_id=employee_id)
        
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
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalaries(), IsAuditorHRReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        business = request.user.business
        year = request.query_params.get('year')
        
        if not year:
            year = timezone.now().year
        
        # Add pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        
        payrolls = Payroll.objects.filter(
            business=business,
            year=year
        ).order_by('month')
        
        paginator = Paginator(payrolls, page_size)
        page_obj = paginator.get_page(page)
        
        monthly_data = []
        for payroll in page_obj:
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
            'page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'monthly_breakdown': monthly_data,
            'annual_totals': totals
        })


# ==================== LEAVE MANAGEMENT (NEW) ====================
class LeaveTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveTypeSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageLeave(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return LeaveType.objects.none()
        return LeaveType.objects.filter(business=self.request.user.business, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeaveTypeSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageLeave(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return LeaveType.objects.filter(business=self.request.user.business)


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageLeave(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return LeaveRequest.objects.none()
        return LeaveRequest.objects.filter(employee__business=self.request.user.business).select_related('employee', 'leave_type')
    
    def perform_create(self, serializer):
        employee_id = self.request.data.get('employee_id')
        try:
            employee = Employee.objects.get(id=employee_id, business=self.request.user.business)
            serializer.save(employee=employee, status='pending')
        except Employee.DoesNotExist:
            raise serializers.ValidationError('Employee not found')


class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeaveRequestSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewHR(), IsAuditorHRReadOnly()]
        return [permissions.IsAuthenticated(), CanManageLeave(), IsAuditorHRReadOnly()]
    
    def get_queryset(self):
        return LeaveRequest.objects.filter(employee__business=self.request.user.business)


class ApproveLeaveRequestView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageLeave(), IsAuditorHRReadOnly()]
    
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            leave = LeaveRequest.objects.get(pk=pk, employee__business=request.user.business)
        except LeaveRequest.DoesNotExist:
            return Response({'error': 'Leave request not found'}, status=404)
        
        leave.status = 'approved'
        leave.approved_by = request.user
        leave.approved_date = timezone.now().date()
        leave.save()
        
        return Response({'message': 'Leave request approved successfully'})