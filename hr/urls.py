# hr/urls.py

from django.urls import path
from .views import (
    DepartmentListCreateView, DepartmentDetailView,
    EmployeeListCreateView, EmployeeDetailView,
    SalaryListCreateView, SalaryDetailView,
    PayrollListCreateView, PayrollDetailView,
    ProcessPayrollView, MarkPayrollPaidView,
    SalesByEmployeeReportView, TopPerformersReportView, PayrollReportView,
    LeaveTypeListCreateView, LeaveTypeDetailView,
    LeaveRequestListCreateView, LeaveRequestDetailView, ApproveLeaveRequestView
)

urlpatterns = [
    # Departments
    path('departments/', DepartmentListCreateView.as_view(), name='departments'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department-detail'),
    
    # Employees
    path('employees/', EmployeeListCreateView.as_view(), name='employees'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    
    # Salaries
    path('salaries/', SalaryListCreateView.as_view(), name='salaries'),
    path('salaries/<int:pk>/', SalaryDetailView.as_view(), name='salary-detail'),
    
    # Payroll
    path('payroll/', PayrollListCreateView.as_view(), name='payroll-list'),
    path('payroll/<int:pk>/', PayrollDetailView.as_view(), name='payroll-detail'),
    path('payroll/process/', ProcessPayrollView.as_view(), name='process-payroll'),
    path('payroll/<int:pk>/mark-paid/', MarkPayrollPaidView.as_view(), name='mark-payroll-paid'),
    
    # Reports
    path('reports/sales-by-employee/', SalesByEmployeeReportView.as_view(), name='sales-by-employee'),
    path('reports/top-performers/', TopPerformersReportView.as_view(), name='top-performers'),
    path('reports/payroll/', PayrollReportView.as_view(), name='payroll-report'),
    
    # Leave Management
    path('leave-types/', LeaveTypeListCreateView.as_view(), name='leave-types'),
    path('leave-types/<int:pk>/', LeaveTypeDetailView.as_view(), name='leave-type-detail'),
    path('leave-requests/', LeaveRequestListCreateView.as_view(), name='leave-requests'),
    path('leave-requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='leave-request-detail'),
    path('leave-requests/<int:pk>/approve/', ApproveLeaveRequestView.as_view(), name='approve-leave'),
]