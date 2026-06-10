# bi/services.py - UPDATED WITH BUDGET TARGETS

from django.db.models import Sum, Count, Avg, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
from decimal import Decimal
from core.models import Business
from financials.models import Transaction
from inventory.models import Product
from sales.models import Sale, SaleItem, Customer
from hr.models import Employee
from financials.models import Budget


class BusinessIntelligenceService:
    """Core BI logic for BizSmart"""
    
    def __init__(self, business):
        self.business = business
        self.today = timezone.now().date()
    
    def _get_active_budget(self):
        """Get active budget for current period"""
        try:
            # Get active budget
            active_budget = Budget.objects.filter(
                business=self.business,
                status='active'
            ).first()
            
            if not active_budget:
                return None
            
            return active_budget
        except Exception as e:
            print(f"Error getting active budget: {e}")
            return None
    
    def _calculate_budget_targets(self, budget, current_income, days_in_period, days_passed):
        """Calculate revenue target based on active budget"""
        try:
            # Get total planned income from budget
            total_planned_income = budget.items.filter(
                type='income'
            ).aggregate(total=Coalesce(Sum('planned_amount'), Decimal('0')))['total']
            
            # Calculate daily target
            daily_target = float(total_planned_income) / days_in_period if days_in_period > 0 else 0
            
            # Calculate target to date
            target_to_date = daily_target * days_passed
            
            # Calculate progress
            progress = (current_income / target_to_date * 100) if target_to_date > 0 else 0
            progress = min(100, progress)  # Cap at 100
            
            # Calculate planned profit margin
            total_planned_expenses = budget.items.filter(
                type='expense'
            ).aggregate(total=Coalesce(Sum('planned_amount'), Decimal('0')))['total']
            
            planned_profit = total_planned_income - total_planned_expenses
            planned_margin = (planned_profit / total_planned_income * 100) if total_planned_income > 0 else 0
            
            # Get period display
            period_display = self._get_period_display(budget)
            
            return {
                'has_budget': True,
                'total_planned_income': float(total_planned_income),
                'target_to_date': target_to_date,
                'daily_target': daily_target,
                'progress': round(progress, 1),
                'planned_margin': round(float(planned_margin), 1),
                'period_display': period_display,
                'budget_name': budget.name,
                'budget_period': budget.period,
                'budget_year': budget.year
            }
        except Exception as e:
            print(f"Error calculating budget targets: {e}")
            return {'has_budget': False}
    
    def _get_period_display(self, budget):
        """Get formatted period display for budget"""
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        if budget.period == 'monthly' and budget.month:
            return f"{month_names[budget.month - 1]} {budget.year}"
        elif budget.period == 'quarterly' and budget.quarter:
            quarters = {1: 'Jan-Mar', 2: 'Apr-Jun', 3: 'Jul-Sep', 4: 'Oct-Dec'}
            return f"{quarters[budget.quarter]} {budget.year}"
        else:
            return f"Full Year {budget.year}"
    
    def _get_period_days(self, budget):
        """Get number of days in budget period"""
        from datetime import date
        
        if budget.period == 'monthly' and budget.month:
            if budget.month == 2:
                # Check for leap year
                is_leap = (budget.year % 4 == 0 and budget.year % 100 != 0) or (budget.year % 400 == 0)
                return 29 if is_leap else 28
            elif budget.month in [4, 6, 9, 11]:
                return 30
            else:
                return 31
        elif budget.period == 'quarterly' and budget.quarter:
            quarter_months = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
            months = quarter_months[budget.quarter]
            days = 0
            for m in months:
                if m == 2:
                    is_leap = (budget.year % 4 == 0 and budget.year % 100 != 0) or (budget.year % 400 == 0)
                    days += 29 if is_leap else 28
                elif m in [4, 6, 9, 11]:
                    days += 30
                else:
                    days += 31
            return days
        else:
            # Yearly
            is_leap = (budget.year % 4 == 0 and budget.year % 100 != 0) or (budget.year % 400 == 0)
            return 366 if is_leap else 365
    
    def _get_days_passed_in_period(self, budget):
        """Get number of days passed in budget period"""
        from datetime import date
        
        if budget.period == 'monthly' and budget.month:
            period_start = date(budget.year, budget.month, 1)
        elif budget.period == 'quarterly' and budget.quarter:
            quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
            period_start = date(budget.year, quarter_starts[budget.quarter], 1)
        else:
            period_start = date(budget.year, 1, 1)
        
        days_passed = (self.today - period_start).days + 1
        days_passed = max(0, min(days_passed, self._get_period_days(budget)))
        
        return days_passed
    
    def get_kpi_dashboard(self):
        """Get current month KPI dashboard"""
        return self.get_kpi_dashboard_for_month(self.today.year, self.today.month)
    
    def get_kpi_dashboard_for_month(self, year, month):
        """Get KPI dashboard for specific month with budget targets"""
        try:
            # Calculate date range
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # If end date is in future, use today
            if end_date > self.today:
                end_date = self.today
            
            # Calculate previous month for comparison
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1
            
            prev_start = datetime(prev_year, prev_month, 1).date()
            if prev_month == 12:
                prev_end = datetime(prev_year + 1, 1, 1).date() - timedelta(days=1)
            else:
                prev_end = datetime(prev_year, prev_month + 1, 1).date() - timedelta(days=1)
            
            # ========== INCOME & EXPENSES ==========
            current_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            current_expense = Transaction.objects.filter(
                business=self.business,
                type='expense',
                transaction_date__gte=start_date,
                transaction_date__lte=end_date
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            prev_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date__gte=prev_start,
                transaction_date__lte=prev_end
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            # Calculate profit
            current_profit = current_income - current_expense
            prev_profit = prev_income - current_expense
            
            # Calculate changes
            revenue_change = 0
            if prev_income > 0:
                revenue_change = round(float((current_income - prev_income) / prev_income * 100), 1)
            elif current_income > 0:
                revenue_change = 100
            
            profit_change = 0
            if prev_profit > 0:
                profit_change = round(float((current_profit - prev_profit) / prev_profit * 100), 1)
            elif current_profit > 0:
                profit_change = 100
            
            # Calculate margins
            net_margin = float((current_profit / current_income * 100)) if current_income > 0 else 0
            
            # ========== SALES TRANSACTIONS ==========
            total_transactions = Sale.objects.filter(
                business=self.business,
                status='completed',
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date
            ).count()
            
            if total_transactions == 0:
                total_transactions = Transaction.objects.filter(
                    business=self.business,
                    type='income',
                    transaction_date__gte=start_date,
                    transaction_date__lte=end_date
                ).count()
            
            avg_order_value = float(current_income / total_transactions) if total_transactions > 0 else 0
            
            # ========== INVENTORY ==========
            inventory_agg = Product.objects.filter(
                business=self.business,
                is_active=True
            ).aggregate(
                total_value=Coalesce(Sum('total_investment'), Decimal('0')),
                total_quantity=Coalesce(Sum('quantity_on_hand'), 0),
                low_stock=Count('id', filter=Q(quantity_on_hand__lte=F('reorder_level'), is_active=True))
            )
            
            inventory_value = float(inventory_agg['total_value'])
            low_stock_count = inventory_agg['low_stock'] or 0
            total_quantity = inventory_agg['total_quantity'] or 0
            
            # ========== CUSTOMERS ==========
            total_customers = Customer.objects.filter(business=self.business).count()
            new_customers = Customer.objects.filter(
                business=self.business,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            customers_with_multiple_orders = Customer.objects.filter(
                business=self.business,
                total_visits__gt=1
            ).count()
            repeat_rate = (customers_with_multiple_orders / total_customers * 100) if total_customers > 0 else 0
            
            total_revenue = Transaction.objects.filter(
                business=self.business,
                type='income'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            avg_ltv = float(total_revenue / total_customers) if total_customers > 0 else 0
            
            # ========== EMPLOYEES ==========
            total_employees = Employee.objects.filter(business=self.business, is_active=True).count()
            revenue_per_employee = float(current_income / total_employees) if total_employees > 0 else 0
            
            # ========== BUSINESS INFO ==========
            business_start_date = None
            if hasattr(self.business, 'created_at') and self.business.created_at:
                business_start_date = self.business.created_at.date()
            
            # ========== BUDGET TARGETS ==========
            active_budget = self._get_active_budget()
            budget_targets = None
            
            if active_budget:
                # Calculate days in period and days passed
                days_in_period = self._get_period_days(active_budget)
                days_passed = self._get_days_passed_in_period(active_budget)
                
                budget_targets = self._calculate_budget_targets(
                    active_budget, 
                    float(current_income),
                    days_in_period,
                    days_passed
                )
                
                # If budget period is longer than current month, adjust target display
                if active_budget.period != 'monthly':
                    monthly_avg = budget_targets['total_planned_income'] / (days_in_period / 30)
                    budget_targets['monthly_average'] = round(monthly_avg, 2)
            
            result = {
                'period': {
                    'current_month': start_date.strftime('%B %Y'),
                    'previous_month': prev_start.strftime('%B %Y'),
                    'current_month_start': start_date.isoformat(),
                    'current_month_end': end_date.isoformat()
                },
                'revenue': {
                    'current': float(current_income),
                    'previous': float(prev_income),
                    'change': revenue_change,
                    'trend': 'up' if revenue_change > 0 else 'down' if revenue_change < 0 else 'stable'
                },
                'profit': {
                    'current': float(current_profit),
                    'previous': float(prev_profit),
                    'change': profit_change,
                    'trend': 'up' if profit_change > 0 else 'down' if profit_change < 0 else 'stable',
                    'is_negative': current_profit < 0
                },
                'margins': {
                    'net_margin': round(net_margin, 1)
                },
                'sales': {
                    'total_transactions': total_transactions,
                    'average_order_value': round(avg_order_value, 2),
                    'transactions_change': 0
                },
                'customers': {
                    'total': total_customers,
                    'new_this_month': new_customers,
                    'repeat_rate': round(repeat_rate, 1),
                    'avg_ltv': round(avg_ltv, 2)
                },
                'inventory': {
                    'total_value': inventory_value,
                    'low_stock_items': low_stock_count,
                    'total_quantity': total_quantity
                },
                'employees': {
                    'total': total_employees,
                    'revenue_per_employee': round(revenue_per_employee, 2)
                },
                'business_start_date': business_start_date.isoformat() if business_start_date else None,
                'budget_targets': budget_targets
            }
            
            return result
            
        except Exception as e:
            print(f"Error in get_kpi_dashboard_for_month: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_dashboard()
    
    def _get_default_dashboard(self):
        """Return default dashboard structure"""
        return {
            'period': {
                'current_month': 'No Data',
                'previous_month': 'No Data',
                'current_month_start': None,
                'current_month_end': None
            },
            'revenue': {
                'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable'
            },
            'profit': {
                'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable', 'is_negative': False
            },
            'margins': {
                'net_margin': 0
            },
            'sales': {
                'total_transactions': 0, 'average_order_value': 0, 'transactions_change': 0
            },
            'customers': {
                'total': 0, 'new_this_month': 0, 'repeat_rate': 0, 'avg_ltv': 0
            },
            'inventory': {
                'total_value': 0, 'low_stock_items': 0, 'total_quantity': 0
            },
            'employees': {
                'total': 0, 'revenue_per_employee': 0
            },
            'business_start_date': None,
            'budget_targets': None
        }
    
    def get_business_info(self):
        """Get business information"""
        try:
            business_start_date = None
            if hasattr(self.business, 'created_at') and self.business.created_at:
                business_start_date = self.business.created_at.date()
            
            return {
                'business_name': self.business.name,
                'business_city': getattr(self.business, 'city', ''),
                'start_date': business_start_date.isoformat() if business_start_date else None,
                'email': getattr(self.business, 'email', ''),
                'phone': getattr(self.business, 'phone', ''),
            }
        except Exception as e:
            return {
                'business_name': self.business.name if hasattr(self.business, 'name') else 'Business',
                'business_city': '',
                'start_date': None,
                'email': '',
                'phone': '',
            }
    
    def get_trends(self, days=30):
        """Get daily revenue trends"""
        start_date = self.today - timedelta(days=days)
        
        daily_data = []
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            daily_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date=date
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            daily_data.append({
                'date': date.isoformat(),
                'revenue': float(daily_income)
            })
        
        return {'daily': daily_data}
    
    def get_top_products(self, limit=10):
        """Get top selling products"""
        start_date = self.today - timedelta(days=30)
        
        top_products = SaleItem.objects.filter(
            sale__business=self.business,
            sale__status='completed',
            sale__sale_date__date__gte=start_date
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Coalesce(Sum('quantity'), 0),
            total_revenue=Coalesce(Sum('total_price'), Decimal('0'))
        ).order_by('-total_revenue')[:limit]
        
        results = []
        for item in top_products:
            results.append({
                'id': item['product__id'],
                'name': item['product__name'],
                'sku': item['product__sku'],
                'quantity_sold': item['total_quantity'],
                'revenue': float(item['total_revenue'])
            })
        
        return results
    
    def get_slow_moving_products(self, days=30):
        """Get slow moving products"""
        start_date = self.today - timedelta(days=days)
        
        slow_products = Product.objects.filter(
            business=self.business,
            is_active=True
        ).annotate(
            sales_quantity=Coalesce(Sum('saleitem__quantity', filter=Q(
                saleitem__sale__status='completed',
                saleitem__sale__sale_date__date__gte=start_date
            )), 0)
        ).filter(
            quantity_on_hand__gt=0,
            sales_quantity=0
        )[:10]
        
        results = []
        for product in slow_products:
            results.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'quantity_on_hand': product.quantity_on_hand,
                'investment': float(product.total_investment)
            })
        
        return results
    
    def get_customer_insights(self):
        """Get customer insights"""
        customers = Customer.objects.filter(business=self.business)
        total_customers = customers.count()
        
        segments = {
            'high_value': customers.filter(total_spent__gte=500000).count(),
            'medium_value': customers.filter(total_spent__gte=100000, total_spent__lt=500000).count(),
            'low_value': customers.filter(total_spent__lt=100000).count(),
        }
        
        repeat_customers = customers.filter(total_visits__gt=1).count()
        retention_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
        
        return {
            'total_customers': total_customers,
            'segments': segments,
            'retention_rate': round(retention_rate, 1),
            'repeat_customers': repeat_customers,
            'top_customers': []
        }
    
    def get_sales_forecast(self, days=30):
        """Get sales forecast"""
        return {'forecast': [], 'total_forecast': 0, 'confidence': 0}
    
    def generate_insights(self):
        """Generate insights"""
        return []
    
    def get_profit_loss(self, start_date, end_date):
        """Get profit & loss"""
        income = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        expense = Transaction.objects.filter(
            business=self.business,
            type='expense',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        return {
            'income': {'total': float(income)},
            'expenses': {'total': float(expense)},
            'profit': {'net_profit': float(income - expense)}
        }