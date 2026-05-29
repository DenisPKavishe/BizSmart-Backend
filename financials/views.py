# financials/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db import models as django_models
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from decimal import Decimal
from core.models import Business
from .models import Transaction, Invoice, InvoiceItem, Loan, PettyCash, CashFlowForecast, Budget, BudgetItem
from .serializers import (
    TransactionSerializer, InvoiceSerializer, LoanSerializer,
    PettyCashSerializer, CashFlowForecastSerializer, BudgetSerializer,
    BudgetItemSerializer, BudgetItemCreateSerializer, BudgetSummarySerializer
)
from .tax_calculator import TaxCalculator
from .permissions import (
    CanViewFinancials, CanEditFinancials, CanViewInvoices,
    CanCreateInvoices, CanViewLoans, CanViewPettyCash,
    CanExportReports, IsAuditorReadOnly, CanViewBudgets,
    CanManageBudgets, IsAuditorBudgetReadOnly
)


# ==================== TRANSACTIONS ====================
class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewFinancials()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Transaction.objects.none()
        if self.request.user.is_authenticated and self.request.user.business:
            return Transaction.objects.filter(business=self.request.user.business)
        return Transaction.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user
        )


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewFinancials()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.business:
            return Transaction.objects.filter(business=self.request.user.business)
        return Transaction.objects.none()


# ==================== INVOICES ====================
class InvoiceListCreateView(generics.ListCreateAPIView):
    serializer_class = InvoiceSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInvoices()]
        return [permissions.IsAuthenticated(), CanCreateInvoices(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Invoice.objects.none()
        if self.request.user.is_authenticated and self.request.user.business:
            return Invoice.objects.filter(business=self.request.user.business)
        return Invoice.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user
        )


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInvoices()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        return Invoice.objects.filter(business=self.request.user.business)


class RecordPaymentView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanCreateInvoices(), IsAuditorReadOnly()]
    
    @transaction.atomic
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            invoice = Invoice.objects.get(pk=pk, business=request.user.business)
            amount = Decimal(request.data.get('amount', 0))
            
            invoice.amount_paid += amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = 'paid'
                invoice.payment_date = timezone.now().date()
            else:
                invoice.status = 'sent'
            invoice.save()
            
            Transaction.objects.create(
                business=request.user.business,
                created_by=request.user,
                type='income',
                cost_type='non_cost',
                category='sales',
                amount=amount,
                description=f'Payment for invoice {invoice.invoice_number}',
                transaction_date=timezone.now().date()
            )
            
            return Response({'message': 'Payment recorded successfully'})
        except Invoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=404)


# ==================== LOANS ====================
class LoanListCreateView(generics.ListCreateAPIView):
    serializer_class = LoanSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewLoans()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Loan.objects.none()
        if self.request.user.is_authenticated and self.request.user.business:
            return Loan.objects.filter(business=self.request.user.business)
        return Loan.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user
        )


class LoanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LoanSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewLoans()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        return Loan.objects.filter(business=self.request.user.business)


class LoanPaymentView(APIView):
    """Record a loan payment (principal + interest)"""
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanEditFinancials()]
    
    @transaction.atomic
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            loan = Loan.objects.get(pk=pk, business=request.user.business)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=404)
        
        amount = Decimal(str(request.data.get('amount', 0)))
        interest_amount = Decimal(str(request.data.get('interest_amount', 0)))
        payment_date = request.data.get('payment_date', timezone.now().date())
        
        if amount <= 0:
            return Response({'error': 'Payment amount must be greater than zero'}, status=400)
        
        principal_amount = amount - interest_amount
        
        if principal_amount > loan.balance_remaining:
            return Response({
                'error': f'Principal payment exceeds remaining balance. Remaining: {loan.balance_remaining}'
            }, status=400)
        
        # Record interest as expense
        if interest_amount > 0:
            Transaction.objects.create(
                business=request.user.business,
                created_by=request.user,
                type='expense',
                cost_type='fixed',
                category='loan_interest',
                amount=interest_amount,
                description=f"Interest payment for loan {loan.id} - {loan.lender_name}",
                transaction_date=payment_date
            )
        
        # Update loan
        loan.amount_paid += principal_amount
        loan.save()
        
        return Response({
            'message': 'Loan payment recorded successfully',
            'loan': LoanSerializer(loan).data,
            'payment_breakdown': {
                'total_paid': float(amount),
                'principal_paid': float(principal_amount),
                'interest_paid': float(interest_amount),
                'remaining_balance': float(loan.balance_remaining)
            }
        })


# ==================== PETTY CASH ====================
class PettyCashListCreateView(generics.ListCreateAPIView):
    serializer_class = PettyCashSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewPettyCash()]
        return [permissions.IsAuthenticated(), CanCreateInvoices(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PettyCash.objects.none()
        if self.request.user.is_authenticated and self.request.user.business:
            return PettyCash.objects.filter(business=self.request.user.business)
        return PettyCash.objects.none()
    
    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user,
            date=timezone.now().date()
        )


class PettyCashDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PettyCashSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewPettyCash()]
        return [permissions.IsAuthenticated(), CanEditFinancials(), IsAuditorReadOnly()]
    
    def get_queryset(self):
        return PettyCash.objects.filter(business=self.request.user.business)


# ==================== CASH FLOW FORECAST ====================
class CashFlowForecastView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewFinancials()]
    
    def get(self, request):
        self.check_permissions(request)
        
        if getattr(self, 'swagger_fake_view', False):
            return Response({'message': 'Schema generation'})
        
        user = request.user
        business = user.business
        
        if not business:
            return Response({'error': 'No business associated with this user'}, status=400)
        
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        avg_daily_income = Transaction.objects.filter(
            business=business, type='income', transaction_date__gte=last_30_days
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        avg_daily_income = avg_daily_income / 30 if avg_daily_income > 0 else 0
        
        avg_daily_expense = Transaction.objects.filter(
            business=business, type='expense', transaction_date__gte=last_30_days
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        avg_daily_expense = avg_daily_expense / 30 if avg_daily_expense > 0 else 0
        
        current_balance = Transaction.objects.filter(business=business).aggregate(
            income=Sum('amount', filter=Q(type='income')),
            expense=Sum('amount', filter=Q(type='expense'))
        )
        balance = (current_balance['income'] or 0) - (current_balance['expense'] or 0)
        
        forecast = []
        for i in range(1, 31):
            balance += avg_daily_income - avg_daily_expense
            forecast.append({
                'day': i,
                'date': (today + timedelta(days=i)).isoformat(),
                'projected_balance': round(balance, 2)
            })
        
        warning = None
        min_balance = min(f['projected_balance'] for f in forecast)
        if min_balance < 0:
            warning = f'Cash shortage predicted in {next(i for i,f in enumerate(forecast) if f["projected_balance"] < 0) + 1} days'
        
        return Response({
            'current_balance': round(balance, 2),
            'avg_daily_income': round(avg_daily_income, 2),
            'avg_daily_expense': round(avg_daily_expense, 2),
            'forecast_30_days': forecast,
            'warning': warning
        })


# ==================== FINANCIAL DASHBOARD ====================
class CompleteFinancialDashboardView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewFinancials()]
    
    def get(self, request):
        self.check_permissions(request)
        
        if getattr(self, 'swagger_fake_view', False):
            return Response({'message': 'Schema generation'})
        
        user = request.user
        business = user.business
        
        if not business:
            return Response({'error': 'No business associated with this user'}, status=400)
        
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year
        
        total_revenue = Transaction.objects.filter(
            business=business, type='income',
            transaction_date__month=current_month,
            transaction_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_expenses = Transaction.objects.filter(
            business=business, type='expense',
            transaction_date__month=current_month,
            transaction_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        direct_costs = Transaction.objects.filter(
            business=business, type='expense', cost_type='direct',
            transaction_date__month=current_month,
            transaction_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        variable_costs = Transaction.objects.filter(
            business=business, type='expense', cost_type='variable',
            transaction_date__month=current_month,
            transaction_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        fixed_costs = Transaction.objects.filter(
            business=business, type='expense', cost_type='fixed',
            transaction_date__month=current_month,
            transaction_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        gross_profit = total_revenue - direct_costs
        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        net_profit = total_revenue - total_expenses
        net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        estimated_vat = TaxCalculator.calculate_vat(total_revenue)
        estimated_income_tax = TaxCalculator.calculate_income_tax(net_profit * 12)
        
        total_invoices = Invoice.objects.filter(business=business).count()
        paid_invoices = Invoice.objects.filter(business=business, status='paid').count()
        overdue_invoices = Invoice.objects.filter(business=business, status='overdue').count()
        total_outstanding = Invoice.objects.filter(business=business).aggregate(
            total=Sum('total_amount') - Sum('amount_paid')
        )['total'] or 0
        
        active_loans = Loan.objects.filter(business=business, status='active')
        total_loan_balance = sum(loan.balance_remaining for loan in active_loans)
        next_payment = active_loans.order_by('next_payment_date').first()
        
        recent = Transaction.objects.filter(business=business)[:10]
        
        return Response({
            'business_name': business.name,
            'business_city': business.get_city_display(),
            'summary': {
                'total_revenue': round(total_revenue, 2),
                'total_expenses': round(total_expenses, 2),
                'net_profit': round(net_profit, 2),
                'net_margin': round(net_margin, 1)
            },
            'costs': {
                'direct_costs': round(direct_costs, 2),
                'variable_costs': round(variable_costs, 2),
                'fixed_costs': round(fixed_costs, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_margin': round(gross_margin, 1)
            },
            'taxes': {
                'estimated_vat': round(estimated_vat, 2),
                'estimated_income_tax': round(estimated_income_tax, 2),
                'vat_rate': '18%'
            },
            'invoices': {
                'total': total_invoices,
                'paid': paid_invoices,
                'overdue': overdue_invoices,
                'total_outstanding': round(total_outstanding, 2)
            },
            'loans': {
                'active_loans': active_loans.count(),
                'total_balance': round(total_loan_balance, 2),
                'next_payment_date': next_payment.next_payment_date if next_payment else None,
                'next_payment_amount': float(next_payment.monthly_payment) if next_payment else None
            },
            'recent_transactions': TransactionSerializer(recent, many=True).data
        })


# ==================== EXPORT REPORTS ====================
from django.http import HttpResponse
import csv
import json

class ExportFinancialReportView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanExportReports(), IsAuditorReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        if getattr(self, 'swagger_fake_view', False):
            return Response({'message': 'Schema generation'})
        
        business = request.user.business
        format_type = request.query_params.get('format', 'csv')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not business:
            return Response({'error': 'No business associated'}, status=400)
        
        transactions = Transaction.objects.filter(business=business)
        if start_date:
            transactions = transactions.filter(transaction_date__gte=start_date)
        if end_date:
            transactions = transactions.filter(transaction_date__lte=end_date)
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="financial_report.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Type', 'Cost Type', 'Category', 'Amount', 'Description'])
            
            for t in transactions:
                writer.writerow([t.transaction_date, t.type, t.cost_type, t.category, t.amount, t.description])
            
            return response
        
        elif format_type == 'json':
            data = TransactionSerializer(transactions, many=True).data
            return Response(data)


# ==================== BUDGET MANAGEMENT ====================
class BudgetListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewBudgets()]
        return [permissions.IsAuthenticated(), CanManageBudgets(), IsAuditorBudgetReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Budget.objects.none()
        
        if self.request.user.is_authenticated and self.request.user.business:
            queryset = Budget.objects.filter(business=self.request.user.business)
            period = self.request.query_params.get('period')
            year = self.request.query_params.get('year')
            status = self.request.query_params.get('status')
            if period:
                queryset = queryset.filter(period=period)
            if year:
                queryset = queryset.filter(year=year)
            if status:
                queryset = queryset.filter(status=status)
            return queryset
        return Budget.objects.none()
    
    @transaction.atomic
    def perform_create(self, serializer):
        data = serializer.validated_data
        period = data['period']
        year = data['year']
        month = data.get('month')
        quarter = data.get('quarter')
        
        duplicate_exists = Budget.objects.filter(
            business=self.request.user.business,
            period=period,
            year=year,
            month=month if period == 'monthly' else None,
            quarter=quarter if period == 'quarterly' else None
        ).exists()
        
        if duplicate_exists:
            raise serializers.ValidationError({
                'error': 'A budget already exists for this period. Please edit existing budget or choose different period.'
            })
        
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user
        )


class BudgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewBudgets()]
        return [permissions.IsAuthenticated(), CanManageBudgets(), IsAuditorBudgetReadOnly()]
    
    def get_queryset(self):
        return Budget.objects.filter(business=self.request.user.business)


class BudgetItemListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetItemCreateSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewBudgets()]
        return [permissions.IsAuthenticated(), CanManageBudgets(), IsAuditorBudgetReadOnly()]
    
    def get_queryset(self):
        budget_id = self.kwargs.get('budget_id')
        if budget_id and self.request.user.is_authenticated:
            return BudgetItem.objects.filter(budget_id=budget_id, budget__business=self.request.user.business)
        return BudgetItem.objects.none()
    
    def perform_create(self, serializer):
        budget_id = self.kwargs.get('budget_id')
        budget = Budget.objects.get(id=budget_id, business=self.request.user.business)
        serializer.save(budget=budget)


class BudgetItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetItemCreateSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewBudgets()]
        return [permissions.IsAuthenticated(), CanManageBudgets(), IsAuditorBudgetReadOnly()]
    
    def get_queryset(self):
        return BudgetItem.objects.filter(budget__business=self.request.user.business)


class BudgetVsActualView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewBudgets()]
    
    def get(self, request, pk):
        self.check_permissions(request)
        
        if getattr(self, 'swagger_fake_view', False):
            return Response({'message': 'Schema generation'})
        
        cache_key = f"budget_vs_actual_{pk}_{request.user.id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return Response(cached_result)
        
        try:
            budget = Budget.objects.prefetch_related('items').get(pk=pk, business=request.user.business)
        except Budget.DoesNotExist:
            return Response({'error': 'Budget not found'}, status=404)
        
        serializer = BudgetSerializer(budget, context={'request': request})
        budget_data = serializer.data
        
        alerts = []
        for item in budget_data.get('items', []):
            if abs(item.get('variance_percentage', 0)) >= 10:
                alerts.append({
                    'category': item['category'],
                    'category_name': item['category_name'],
                    'type': item['type'],
                    'planned_amount': item['planned_amount'],
                    'actual_amount': item['actual_amount'],
                    'percentage': abs(item['variance_percentage']),
                    'severity': 'critical' if abs(item['variance_percentage']) >= 20 else 'warning',
                    'message': f"{item['category_name']} is {abs(item['variance_percentage']):.1f}% {'below' if item['variance'] < 0 else 'above'} budget"
                })
        
        response_data = {
            'budget': budget_data,
            'alerts': alerts,
            'overall_status': {
                'profit_variance': budget_data['actual_profit'] - budget_data['planned_profit'],
                'profit_variance_percentage': ((budget_data['actual_profit'] - budget_data['planned_profit']) / budget_data['planned_profit'] * 100) if budget_data['planned_profit'] > 0 else 0,
                'is_on_track': budget_data['actual_profit'] >= budget_data['planned_profit']
            }
        }
        
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data)


class CopyBudgetView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageBudgets()]
    
    @transaction.atomic
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            source_budget = Budget.objects.get(pk=pk, business=request.user.business)
        except Budget.DoesNotExist:
            return Response({'error': 'Source budget not found'}, status=404)
        
        target_name = request.data.get('name')
        target_year = request.data.get('year')
        target_month = request.data.get('month')
        target_quarter = request.data.get('quarter')
        target_period = request.data.get('period', source_budget.period)
        
        if not target_year:
            return Response({'error': 'Target year is required'}, status=400)
        
        new_budget = Budget.objects.create(
            business=request.user.business,
            created_by=request.user,
            name=target_name or f"{source_budget.name} (Copy)",
            period=target_period,
            year=target_year,
            month=target_month,
            quarter=target_quarter,
            status='draft',
            notes=f"Copied from {source_budget.name}"
        )
        
        for item in source_budget.items.all():
            BudgetItem.objects.create(
                budget=new_budget,
                category=item.category,
                category_name=item.category_name,
                type=item.type,
                planned_amount=item.planned_amount,
                notes=f"Copied from {source_budget.name}"
            )
        
        serializer = BudgetSerializer(new_budget, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BudgetSummaryView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewBudgets()]
    
    def get(self, request):
        self.check_permissions(request)
        
        year = request.query_params.get('year')
        period = request.query_params.get('period', 'monthly')
        
        if not year:
            year = timezone.now().year
        
        budgets = Budget.objects.filter(
            business=request.user.business,
            period=period,
            year=year,
            status='active'
        )
        
        summary_data = []
        for budget in budgets:
            serializer = BudgetSerializer(budget, context={'request': request})
            data = serializer.data
            summary_data.append({
                'period': budget.month or budget.quarter or year,
                'period_name': budget.name,
                'total_planned_income': data['total_planned_income'],
                'total_actual_income': data['total_actual_income'],
                'total_planned_expenses': data['total_planned_expenses'],
                'total_actual_expenses': data['total_actual_expenses'],
                'planned_profit': data['planned_profit'],
                'actual_profit': data['actual_profit'],
                'variance': data['actual_profit'] - data['planned_profit'],
                'variance_percentage': ((data['actual_profit'] - data['planned_profit']) / data['planned_profit'] * 100) if data['planned_profit'] > 0 else 0
            })
        
        return Response({
            'year': year,
            'period_type': period,
            'summary': summary_data,
            'total_planned_income': sum(s['total_planned_income'] for s in summary_data),
            'total_actual_income': sum(s['total_actual_income'] for s in summary_data),
            'total_planned_expenses': sum(s['total_planned_expenses'] for s in summary_data),
            'total_actual_expenses': sum(s['total_actual_expenses'] for s in summary_data),
            'total_planned_profit': sum(s['planned_profit'] for s in summary_data),
            'total_actual_profit': sum(s['actual_profit'] for s in summary_data)
        })