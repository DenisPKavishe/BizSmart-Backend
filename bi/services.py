from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from core.models import Business
from financials.models import Transaction
from inventory.models import Product
from sales.models import Sale, SaleItem, Customer
from hr.models import Employee


class BusinessIntelligenceService:
    """Core BI logic for BizSmart"""
    
    def __init__(self, business):
        self.business = business
        self.today = timezone.now().date()
    
    def _calculate_percentage_change(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous * 100), 1)
    
    def _calculate_gross_margin(self, start_date, end_date):
        income = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        cogs = Transaction.objects.filter(
            business=self.business,
            type='expense',
            cost_type='direct',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        if income > 0:
            return (income - cogs) / income * 100
        return 0
    
    def _calculate_inventory_turnover(self):
        cogs = Transaction.objects.filter(
            business=self.business,
            type='expense',
            cost_type='direct'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        avg_inventory = Product.objects.filter(
            business=self.business
        ).aggregate(Avg('total_investment'))['total_investment__avg'] or Decimal('1')
        
        if avg_inventory > 0:
            return float(cogs / avg_inventory)
        return 0
    
    def get_kpi_dashboard(self):
        """Main KPI dashboard with all key metrics"""
        current_month_start = self.today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)
        
        current_income = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=current_month_start,
            transaction_date__lte=self.today
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        current_expense = Transaction.objects.filter(
            business=self.business,
            type='expense',
            transaction_date__gte=current_month_start,
            transaction_date__lte=self.today
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        last_income = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=last_month_start,
            transaction_date__lte=last_month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        last_expense = Transaction.objects.filter(
            business=self.business,
            type='expense',
            transaction_date__gte=last_month_start,
            transaction_date__lte=last_month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        revenue_change = self._calculate_percentage_change(current_income, last_income)
        expense_change = self._calculate_percentage_change(current_expense, last_expense)
        
        current_profit = current_income - current_expense
        last_profit = last_income - last_expense
        profit_change = self._calculate_percentage_change(current_profit, last_profit)
        
        gross_margin = self._calculate_gross_margin(current_month_start, self.today)
        net_margin = (current_profit / current_income * 100) if current_income > 0 else 0
        
        inventory_value = Product.objects.filter(
            business=self.business
        ).aggregate(Sum('total_investment'))['total_investment__sum'] or Decimal('0')
        
        low_stock_count = Product.objects.filter(
            business=self.business,
            quantity_on_hand__lte=F('reorder_level'),
            is_active=True
        ).count()
        
        total_sales = Sale.objects.filter(
            business=self.business,
            status='completed',
            sale_date__date__gte=current_month_start
        ).count()
        
        avg_order_value = current_income / total_sales if total_sales > 0 else 0
        
        total_customers = Customer.objects.filter(business=self.business).count()
        new_customers = Customer.objects.filter(
            business=self.business,
            created_at__gte=current_month_start
        ).count()
        
        total_employees = Employee.objects.filter(business=self.business, is_active=True).count()
        revenue_per_employee = current_income / total_employees if total_employees > 0 else 0
        
        return {
            'period': {
                'current_month': current_month_start.strftime('%B %Y'),
                'previous_month': last_month_start.strftime('%B %Y'),
                'current_month_start': current_month_start.isoformat(),
                'current_month_end': self.today.isoformat()
            },
            'revenue': {
                'current': float(current_income),
                'previous': float(last_income),
                'change': revenue_change,
                'trend': 'up' if revenue_change > 0 else 'down' if revenue_change < 0 else 'stable'
            },
            'expenses': {
                'current': float(current_expense),
                'previous': float(last_expense),
                'change': expense_change,
                'trend': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'stable'
            },
            'profit': {
                'current': float(current_profit),
                'previous': float(last_profit),
                'change': profit_change,
                'trend': 'up' if profit_change > 0 else 'down' if profit_change < 0 else 'stable'
            },
            'margins': {
                'gross_margin': round(float(gross_margin), 1),
                'net_margin': round(float(net_margin), 1)
            },
            'inventory': {
                'total_value': float(inventory_value),
                'low_stock_items': low_stock_count
            },
            'sales': {
                'total_transactions': total_sales,
                'average_order_value': float(avg_order_value)
            },
            'customers': {
                'total': total_customers,
                'new_this_month': new_customers
            },
            'employees': {
                'total': total_employees,
                'revenue_per_employee': float(revenue_per_employee)
            }
        }
    
    def get_trends(self, days=30):
        """Get sales and profit trends for last N days"""
        start_date = self.today - timedelta(days=days)
        
        daily_data = []
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            day_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date=date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            day_expense = Transaction.objects.filter(
                business=self.business,
                type='expense',
                transaction_date=date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            daily_data.append({
                'date': date.isoformat(),
                'revenue': float(day_income),
                'expenses': float(day_expense),
                'profit': float(day_income - day_expense)
            })
        
        weekly_data = []
        for week in range(4):
            week_start = self.today - timedelta(days=7 * (week + 1))
            week_end = week_start + timedelta(days=6)
            week_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date__gte=week_start,
                transaction_date__lte=week_end
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            weekly_data.append({
                'week': f"Week {4 - week}",
                'revenue': float(week_income)
            })
        
        monthly_data = []
        for month in range(6):
            month_date = self.today.replace(day=1) - timedelta(days=30 * month)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1, day=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1, day=1)
            month_end = next_month - timedelta(days=1)
            
            month_income = Transaction.objects.filter(
                business=self.business,
                type='income',
                transaction_date__gte=month_start,
                transaction_date__lte=month_end
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'revenue': float(month_income),
                'short_month': month_start.strftime('%b')
            })
        
        daily_revenues = [d['revenue'] for d in daily_data]
        
        return {
            'daily': daily_data,
            'weekly': weekly_data,
            'monthly': monthly_data,
            'summary': {
                'total_revenue_last_30_days': sum(daily_revenues),
                'average_daily_revenue': sum(daily_revenues) / len(daily_revenues) if daily_revenues else 0,
                'best_day': max(daily_data, key=lambda x: x['revenue']) if daily_data else None,
                'worst_day': min(daily_data, key=lambda x: x['revenue']) if daily_data else None
            }
        }
    
    def get_top_products(self, limit=10):
        """Get best selling products"""
        start_date = self.today - timedelta(days=30)
        
        top_products = SaleItem.objects.filter(
            sale__business=self.business,
            sale__status='completed',
            sale__sale_date__date__gte=start_date
        ).values(
            'product__id',
            'product__name',
            'product__sku',
            'product__selling_price'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price'),
            total_profit=Sum(F('total_price') - F('cost_price') * F('quantity'))
        ).order_by('-total_revenue')[:limit]
        
        results = []
        for item in top_products:
            revenue = float(item['total_revenue'])
            profit = float(item['total_profit'] or 0)
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0
            
            results.append({
                'id': item['product__id'],
                'name': item['product__name'],
                'sku': item['product__sku'],
                'selling_price': float(item['product__selling_price']),
                'quantity_sold': item['total_quantity'],
                'revenue': revenue,
                'profit': profit,
                'profit_margin': round(profit_margin, 1)
            })
        
        return results
    
    def get_slow_moving_products(self, days=30):
        """Get products that haven't sold well"""
        start_date = self.today - timedelta(days=days)
        
        slow_products = Product.objects.filter(
            business=self.business,
            is_active=True
        ).annotate(
            sales_quantity=Sum('saleitem__quantity', filter=Q(
                saleitem__sale__status='completed',
                saleitem__sale__sale_date__date__gte=start_date
            ))
        ).filter(
            quantity_on_hand__gt=0
        ).order_by('sales_quantity')[:10]
        
        results = []
        for product in slow_products:
            sold_qty = product.sales_quantity or 0
            days_to_sell = (product.quantity_on_hand / (sold_qty or 1)) * days if sold_qty > 0 else 999
            
            recommendation = 'Consider discount promotion'
            if sold_qty == 0:
                recommendation = 'Product not selling - consider clearance sale'
            elif product.quantity_on_hand > product.reorder_level * 3:
                recommendation = 'Overstocked - reduce reorder quantity'
            
            results.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'quantity_on_hand': product.quantity_on_hand,
                'sold_last_30_days': sold_qty,
                'days_to_sell': round(days_to_sell, 1),
                'investment': float(product.total_investment),
                'recommendation': recommendation
            })
        
        return results
    
    def get_customer_insights(self):
        """Analyze customer behavior"""
        customers = Customer.objects.filter(business=self.business)
        
        if not customers.exists():
            return {
                'total_customers': 0,
                'segments': {},
                'retention_rate': 0,
                'repeat_customers': 0,
                'top_customers': []
            }
        
        segments = {
            'high_value': customers.filter(total_spent__gte=500000).count(),
            'medium_value': customers.filter(total_spent__gte=100000, total_spent__lt=500000).count(),
            'low_value': customers.filter(total_spent__lt=100000).count(),
        }
        
        top_customers_data = []
        for customer in customers.order_by('-total_spent')[:10]:
            top_customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'total_spent': float(customer.total_spent),
                'total_visits': customer.total_visits,
                'average_order': float(customer.total_spent / customer.total_visits) if customer.total_visits > 0 else 0
            })
        
        repeat_customers = customers.filter(total_visits__gt=1).count()
        retention_rate = (repeat_customers / customers.count() * 100) if customers.count() > 0 else 0
        
        return {
            'total_customers': customers.count(),
            'segments': segments,
            'retention_rate': round(retention_rate, 1),
            'repeat_customers': repeat_customers,
            'top_customers': top_customers_data
        }
    
    def get_sales_forecast(self, days=30):
        """Predict future sales based on historical data"""
        start_date = self.today - timedelta(days=90)
        
        daily_sales = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=start_date,
            transaction_date__lte=self.today
        ).values('transaction_date').annotate(
            daily_total=Sum('amount')
        ).order_by('transaction_date')
        
        if not daily_sales:
            return {
                'forecast': [],
                'total_forecast': 0,
                'average_daily_forecast': 0,
                'confidence': 0,
                'based_on_days': 0
            }
        
        sales_list = [float(s['daily_total']) for s in daily_sales]
        avg_daily = sum(sales_list) / len(sales_list)
        
        x = list(range(len(sales_list)))
        y = sales_list
        
        if len(x) > 1:
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            denominator = (n * sum_x2 - sum_x ** 2)
            if denominator != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                intercept = (sum_y - slope * sum_x) / n
            else:
                slope = 0
                intercept = avg_daily
        else:
            slope = 0
            intercept = y[0] if y else 0
        
        forecast = []
        total_forecast = 0
        for i in range(1, days + 1):
            predicted = max(0, intercept + slope * (len(sales_list) + i))
            forecast.append({
                'day': i,
                'date': (self.today + timedelta(days=i)).isoformat(),
                'predicted_sales': round(predicted, 2)
            })
            total_forecast += predicted
        
        variance = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(len(x))) / len(x) if len(x) > 0 else 0
        confidence = max(0, min(100, 100 - (variance / (avg_daily + 1) * 10)))
        
        return {
            'period': f'Next {days} days',
            'forecast': forecast,
            'total_forecast': round(total_forecast, 2),
            'average_daily_forecast': round(total_forecast / days, 2),
            'confidence': round(confidence, 1),
            'based_on_days': len(sales_list)
        }
    
    def generate_insights(self):
        """Generate actionable insights from data"""
        insights = []
        current_month_start = self.today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)
        
        current_sales = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=current_month_start
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        last_sales = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=last_month_start,
            transaction_date__lte=last_month_end
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        if current_sales > last_sales:
            increase = ((current_sales - last_sales) / last_sales * 100) if last_sales > 0 else 0
            insights.append({
                'type': 'positive',
                'category': 'sales',
                'title': 'Sales Growth',
                'description': f'Sales increased by {round(increase, 1)}% compared to last month',
                'recommendation': 'Continue current marketing strategy',
                'metric_value': float(current_sales)
            })
        elif current_sales < last_sales:
            decrease = ((last_sales - current_sales) / last_sales * 100) if last_sales > 0 else 0
            insights.append({
                'type': 'warning',
                'category': 'sales',
                'title': 'Sales Decline',
                'description': f'Sales decreased by {round(decrease, 1)}% compared to last month',
                'recommendation': 'Review marketing campaigns and customer feedback',
                'metric_value': float(current_sales)
            })
        
        low_stock_products = Product.objects.filter(
            business=self.business,
            quantity_on_hand__lte=F('reorder_level'),
            is_active=True
        )
        
        if low_stock_products.exists():
            insights.append({
                'type': 'critical',
                'category': 'inventory',
                'title': 'Low Stock Alert',
                'description': f'{low_stock_products.count()} products are below reorder level',
                'recommendation': 'Place purchase orders immediately to avoid stockouts',
                'metric_value': low_stock_products.count()
            })
        
        top_products = self.get_top_products(limit=1)
        if top_products:
            top = top_products[0]
            insights.append({
                'type': 'opportunity',
                'category': 'sales',
                'title': 'Top Performing Product',
                'description': f'{top["name"]} is your best seller with {top["quantity_sold"]} units sold',
                'recommendation': f'Consider promoting {top["name"]} more',
                'metric_value': top['revenue']
            })
        
        new_customers = Customer.objects.filter(
            business=self.business,
            created_at__gte=current_month_start
        ).count()
        
        if new_customers > 0:
            insights.append({
                'type': 'positive',
                'category': 'customer',
                'title': 'Customer Acquisition',
                'description': f'You gained {new_customers} new customers this month',
                'recommendation': 'Engage them with welcome offers',
                'metric_value': new_customers
            })
        
        gross_margin = self._calculate_gross_margin(current_month_start, self.today)
        if gross_margin < 30:
            insights.append({
                'type': 'warning',
                'category': 'financial',
                'title': 'Low Profit Margin',
                'description': f'Your gross profit margin is {round(gross_margin, 1)}% (target: 30%+)',
                'recommendation': 'Review supplier costs or consider price adjustments',
                'metric_value': round(gross_margin, 1)
            })
        
        return insights
    
    def get_profit_loss(self, start_date, end_date):
        """Generate Profit & Loss statement"""
        income = Transaction.objects.filter(
            business=self.business,
            type='income',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )
        
        expense = Transaction.objects.filter(
            business=self.business,
            type='expense',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        )
        
        income_by_category = income.values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        expense_by_category = expense.values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        total_income = income.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        total_expense = expense.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        net_profit = total_income - total_expense
        
        cogs = expense.filter(category__in=['raw_materials', 'packaging', 'direct_labor', 'manufacturing']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        gross_profit = total_income - cogs
        gross_margin = (gross_profit / total_income * 100) if total_income > 0 else 0
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'income': {
                'total': float(total_income),
                'breakdown': [
                    {'category': item['category'], 'amount': float(item['total'])}
                    for item in income_by_category
                ]
            },
            'expenses': {
                'total': float(total_expense),
                'breakdown': [
                    {'category': item['category'], 'amount': float(item['total'])}
                    for item in expense_by_category
                ]
            },
            'profit': {
                'gross_profit': float(gross_profit),
                'gross_margin': round(float(gross_margin), 1),
                'net_profit': float(net_profit),
                'net_margin': round(float(net_profit / total_income * 100) if total_income > 0 else 0, 1)
            }
        }