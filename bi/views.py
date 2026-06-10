# bi/views.py - COMPLETE FIXED VERSION

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from decimal import Decimal

from .services import BusinessIntelligenceService
from .permissions import (
    CanViewBIDashboard, CanViewFinancialBI, CanViewInventoryBI,
    CanViewSalesBI, CanViewHRBI, CanViewCustomerBI, IsOwnerOnly
)
from .models import BusinessInsight, BusinessGoal, DashboardWidget
from .serializers import (
    InsightSerializer, GoalSerializer, DashboardWidgetSerializer
)


# ==================== MAIN DASHBOARD ====================

class MainDashboardView(APIView):
    """Main dashboard with all key metrics for the current month."""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            month_param = request.query_params.get('month')
            service = BusinessIntelligenceService(request.user.business)
            
            if month_param:
                try:
                    year, month = map(int, month_param.split('-'))
                    dashboard_data = service.get_kpi_dashboard_for_month(year, month)
                except (ValueError, Exception) as e:
                    print(f"Error getting dashboard for month {month_param}: {e}")
                    dashboard_data = service._get_default_kpi_dashboard()
            else:
                try:
                    dashboard_data = service.get_kpi_dashboard()
                except Exception as e:
                    print(f"Error getting current dashboard: {e}")
                    dashboard_data = service._get_default_kpi_dashboard()
            
            try:
                business_info = service.get_business_info()
            except Exception as e:
                print(f"Error getting business info: {e}")
                business_info = {
                    'business_name': request.user.business.name if request.user.business else 'Business',
                    'start_date': None
                }
            
            current_month = f"{timezone.now().year}-{timezone.now().month:02d}"
            
            return Response({
                'dashboard': dashboard_data,
                'business_info': business_info,
                'selected_month': month_param or current_month
            })
        except Exception as e:
            print(f"Unexpected error in MainDashboardView: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'dashboard': {
                    'revenue': {'current': 0, 'change': 0, 'target': 5000000},
                    'profit': {'current': 0, 'change': 0},
                    'margins': {'net_margin': 0},
                    'sales': {'total_transactions': 0, 'average_order_value': 0},
                    'customers': {'total': 0, 'new_this_month': 0},
                    'inventory': {'total_value': 0, 'low_stock_items': 0}
                },
                'business_info': {'business_name': request.user.business.name if request.user.business else 'Business'},
                'selected_month': timezone.now().strftime('%Y-%m')
            })


class DashboardTrendsView(APIView):
    """Get trends data for charts on main dashboard"""
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            days = min(days, 90)
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_trends(days)
            return Response(data)
        except Exception as e:
            print(f"Error in DashboardTrendsView: {e}")
            return Response({'daily': [], 'weekly': [], 'monthly': [], 'summary': {}})


class DashboardAlertsView(APIView):
    """Get active alerts for the dashboard"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            insights = service.generate_insights()
            active_insights = [i for i in insights if i.get('type') in ['warning', 'critical', 'opportunity']]
            return Response({
                'alerts': active_insights[:5],
                'count': len(active_insights)
            })
        except Exception as e:
            print(f"Error in DashboardAlertsView: {e}")
            return Response({'alerts': [], 'count': 0})


class DashboardMilestonesView(APIView):
    """Get milestones and targets for the dashboard"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            kpi = service.get_kpi_dashboard()
            
            # Safely get values with defaults
            revenue_current = float(kpi.get('revenue', {}).get('current', 0))
            revenue_target = float(kpi.get('revenue', {}).get('target', revenue_current * 1.1 if revenue_current > 0 else 5000000))
            
            # Calculate percentage safely - AVOID division by zero
            revenue_percentage = 0
            if revenue_target > 0:
                revenue_percentage = min(100, (revenue_current / revenue_target) * 100)
            
            customers_current = float(kpi.get('customers', {}).get('new_this_month', 0))
            customers_target = float(kpi.get('customers', {}).get('target', 50))
            
            customers_percentage = 0
            if customers_target > 0:
                customers_percentage = min(100, (customers_current / customers_target) * 100)
            
            margin_current = float(kpi.get('margins', {}).get('net_margin', 0))
            margin_target = float(kpi.get('margins', {}).get('target', 25))
            
            margin_percentage = 0
            if margin_target > 0:
                margin_percentage = min(100, (margin_current / margin_target) * 100)
            
            milestones = {
                'revenue': {
                    'current': revenue_current,
                    'target': revenue_target,
                    'percentage': round(revenue_percentage, 1)
                },
                'customers': {
                    'current': customers_current,
                    'target': customers_target,
                    'percentage': round(customers_percentage, 1)
                },
                'profit_margin': {
                    'current': round(margin_current, 1),
                    'target': margin_target,
                    'percentage': round(margin_percentage, 1)
                }
            }
            
            return Response(milestones)
        except Exception as e:
            print(f"Error in DashboardMilestonesView: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'revenue': {'current': 0, 'target': 0, 'percentage': 0},
                'customers': {'current': 0, 'target': 0, 'percentage': 0},
                'profit_margin': {'current': 0, 'target': 0, 'percentage': 0}
            })


class AvailableMonthsView(APIView):
    """Get list of months with data available for the business"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            from financials.models import Transaction
            
            first_transaction = Transaction.objects.filter(
                business=request.user.business
            ).order_by('transaction_date').first()
            
            if first_transaction:
                start_date = first_transaction.transaction_date
            else:
                start_date = request.user.business.created_at.date() if hasattr(request.user.business, 'created_at') else timezone.now().date()
            
            current_date = timezone.now().date()
            months = []
            
            year = start_date.year
            month = start_date.month
            
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            while year < current_date.year or (year == current_date.year and month <= current_date.month):
                months.append({
                    'value': f"{year}-{month:02d}",
                    'label': f"{month_names[month-1]} {year}",
                    'year': year,
                    'month': month
                })
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            
            return Response({
                'months': months,
                'total_months': len(months),
                'current_month': f"{current_date.year}-{current_date.month:02d}"
            })
        except Exception as e:
            print(f"Error in AvailableMonthsView: {e}")
            return Response({'months': [], 'total_months': 0, 'current_month': ''})


# ==================== KPI DASHBOARD ====================

class KPIDashboardView(APIView):
    """Get main KPI dashboard with key metrics"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_kpi_dashboard()
            return Response(data)
        except Exception as e:
            print(f"Error in KPIDashboardView: {e}")
            return Response({
                'revenue': {'current': 0, 'change': 0},
                'profit': {'current': 0, 'change': 0},
                'margins': {'net_margin': 0}
            })


class TrendAnalysisView(APIView):
    """Get sales and profit trends over time"""
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            days = min(days, 365)
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_trends(days)
            return Response(data)
        except Exception as e:
            print(f"Error in TrendAnalysisView: {e}")
            return Response({'daily': [], 'weekly': [], 'monthly': [], 'summary': {}})


# ==================== SALES ANALYTICS ====================

class TopProductsView(APIView):
    """Get top selling products"""
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(limit, 50)
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_top_products(limit)
            return Response({
                'top_products': data,
                'count': len(data)
            })
        except Exception as e:
            print(f"Error in TopProductsView: {e}")
            return Response({'top_products': [], 'count': 0})


class SalesPerformanceView(APIView):
    """Get sales performance analytics"""
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        try:
            period = request.query_params.get('period', 'month')
            service = BusinessIntelligenceService(request.user.business)
            
            if period == 'week':
                days = 7
            elif period == 'month':
                days = 30
            elif period == 'year':
                days = 365
            else:
                days = 30
            
            trends = service.get_trends(days)
            top_products = service.get_top_products(10)
            customers = service.get_customer_insights()
            
            from sales.models import Sale
            from django.db.models import Sum
            
            start_date = timezone.now().date() - timedelta(days=90)
            
            # SQLite compatible weekday extraction
            sales_by_weekday = Sale.objects.filter(
                business=request.user.business,
                status='completed',
                sale_date__date__gte=start_date
            )
            
            weekday_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            weekday_data = []
            
            for i in range(7):
                # SQLite weekday: 0=Sunday, 1=Monday, ..., 6=Saturday
                weekday_sales = sales_by_weekday.filter(sale_date__week_day=i+1)
                total = weekday_sales.aggregate(total=Sum('total_amount'))['total'] or 0
                if total > 0:
                    weekday_data.append({
                        'day': weekday_names[i],
                        'total_sales': float(total)
                    })
            
            return Response({
                'period': period,
                'trends': trends,
                'top_products': top_products,
                'customer_insights': customers,
                'sales_by_weekday': weekday_data
            })
        except Exception as e:
            print(f"Error in SalesPerformanceView: {e}")
            return Response({
                'period': period,
                'trends': {'daily': []},
                'top_products': [],
                'customer_insights': {},
                'sales_by_weekday': []
            })


class SalesForecastView(APIView):
    """Get sales forecast predictions (Owner only)"""
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            days = min(days, 90)
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_sales_forecast(days)
            return Response(data)
        except Exception as e:
            print(f"Error in SalesForecastView: {e}")
            return Response({
                'period': f'Next {days} days',
                'forecast': [],
                'total_forecast': 0,
                'average_daily_forecast': 0,
                'confidence': 0,
                'based_on_days': 0
            })


# ==================== INVENTORY ANALYTICS ====================

class InventoryAnalyticsView(APIView):
    """Get inventory-specific analytics"""
    permission_classes = [IsAuthenticated, CanViewInventoryBI]
    
    def get(self, request):
        try:
            from inventory.models import Product
            from django.db.models import Sum, Count, Q, F
            
            service = BusinessIntelligenceService(request.user.business)
            top_products = service.get_top_products(10)
            slow_products = service.get_slow_moving_products(30)
            
            inventory_agg = Product.objects.filter(
                business=request.user.business,
                is_active=True
            ).aggregate(
                total_value=Sum('total_investment'),
                total_quantity=Sum('quantity_on_hand'),
                total_products=Count('id')
            )
            
            low_stock = Product.objects.filter(
                business=request.user.business,
                quantity_on_hand__lte=F('reorder_level'),
                is_active=True
            ).count()
            
            out_of_stock = Product.objects.filter(
                business=request.user.business,
                quantity_on_hand=0,
                is_active=True
            ).count()
            
            return Response({
                'inventory_summary': {
                    'total_value': float(inventory_agg['total_value'] or 0),
                    'total_quantity': inventory_agg['total_quantity'] or 0,
                    'total_products': inventory_agg['total_products'] or 0,
                    'low_stock_items': low_stock,
                    'out_of_stock_items': out_of_stock
                },
                'top_products': top_products[:5],
                'slow_moving_products': slow_products[:5]
            })
        except Exception as e:
            print(f"Error in InventoryAnalyticsView: {e}")
            return Response({
                'inventory_summary': {
                    'total_value': 0,
                    'total_quantity': 0,
                    'total_products': 0,
                    'low_stock_items': 0,
                    'out_of_stock_items': 0
                },
                'top_products': [],
                'slow_moving_products': []
            })


class SlowMovingProductsView(APIView):
    """Get products that are not selling well"""
    permission_classes = [IsAuthenticated, CanViewInventoryBI]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            days = min(days, 180)
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_slow_moving_products(days)
            return Response({
                'slow_moving_products': data,
                'count': len(data)
            })
        except Exception as e:
            print(f"Error in SlowMovingProductsView: {e}")
            return Response({'slow_moving_products': [], 'count': 0})


# ==================== CUSTOMER ANALYTICS ====================

class CustomerInsightsView(APIView):
    """Get customer behavior insights and segmentation"""
    permission_classes = [IsAuthenticated, CanViewCustomerBI]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_customer_insights()
            return Response(data)
        except Exception as e:
            print(f"Error in CustomerInsightsView: {e}")
            return Response({
                'total_customers': 0,
                'segments': {},
                'retention_rate': 0,
                'repeat_customers': 0,
                'top_customers': []
            })


# ==================== FINANCIAL ANALYTICS ====================

class FinancialSummaryView(APIView):
    """Get financial summary for dashboard"""
    permission_classes = [IsAuthenticated, CanViewFinancialBI]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            profit_loss = service.get_profit_loss(start_of_month, today)
            kpi = service.get_kpi_dashboard()
            
            return Response({
                'current_month_profit_loss': profit_loss,
                'key_metrics': {
                    'revenue': kpi.get('revenue', {}),
                    'expenses': kpi.get('expenses', {}),
                    'profit': kpi.get('profit', {}),
                    'margins': kpi.get('margins', {})
                }
            })
        except Exception as e:
            print(f"Error in FinancialSummaryView: {e}")
            return Response({
                'current_month_profit_loss': {},
                'key_metrics': {}
            })


class ProfitLossView(APIView):
    """Get Profit & Loss statement"""
    permission_classes = [IsAuthenticated, CanViewFinancialBI]
    
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            days = min(days, 365)
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            service = BusinessIntelligenceService(request.user.business)
            data = service.get_profit_loss(start_date, end_date)
            return Response(data)
        except Exception as e:
            print(f"Error in ProfitLossView: {e}")
            return Response({
                'period': {'start_date': None, 'end_date': None},
                'income': {'total': 0, 'breakdown': []},
                'expenses': {'total': 0, 'breakdown': []},
                'profit': {'gross_profit': 0, 'gross_margin': 0, 'net_profit': 0, 'net_margin': 0}
            })


# ==================== HR ANALYTICS ====================

class HRAnalyticsView(APIView):
    """Get HR and employee analytics"""
    permission_classes = [IsAuthenticated, CanViewHRBI]
    
    def get(self, request):
        try:
            from hr.models import Employee, Attendance, LeaveRequest
            from django.db.models import Sum, Count
            
            business = request.user.business
            
            # Employee summary
            employees = Employee.objects.filter(business=business, is_active=True)
            total_employees = employees.count()
            
            # Department distribution
            department_distribution = list(employees.values('department__name').annotate(
                count=Count('id')
            ).order_by('-count'))
            
            # Gender ratio
            male_count = employees.filter(gender='M').count()
            female_count = employees.filter(gender='F').count()
            
            # Salary summary
            total_monthly_salary = employees.aggregate(total=Sum('salary'))['total'] or 0
            
            # Attendance rate (last 30 days)
            start_date = timezone.now().date() - timedelta(days=30)
            attendance_records = Attendance.objects.filter(
                employee__business=business,
                date__gte=start_date
            )
            total_expected_days = total_employees * 30
            total_attended = attendance_records.filter(status='present').count()
            attendance_rate = (total_attended / total_expected_days * 100) if total_expected_days > 0 else 0
            
            # Upcoming leave
            upcoming_leave = LeaveRequest.objects.filter(
                employee__business=business,
                status='approved',
                start_date__gte=timezone.now().date()
            ).select_related('employee')[:10]
            
            upcoming_leave_data = []
            for leave in upcoming_leave:
                upcoming_leave_data.append({
                    'employee_name': f"{leave.employee.first_name} {leave.employee.last_name}",
                    'start_date': leave.start_date.isoformat(),
                    'end_date': leave.end_date.isoformat(),
                    'days': (leave.end_date - leave.start_date).days + 1,
                    'type': leave.leave_type
                })
            
            return Response({
                'employee_summary': {
                    'total_employees': total_employees,
                    'male_count': male_count,
                    'female_count': female_count,
                    'total_monthly_salary': float(total_monthly_salary)
                },
                'department_distribution': [
                    {'name': d['department__name'] or 'Unassigned', 'count': d['count']}
                    for d in department_distribution
                ],
                'attendance_rate': round(attendance_rate, 1),
                'upcoming_leave': upcoming_leave_data
            })
        except Exception as e:
            print(f"Error in HRAnalyticsView: {e}")
            return Response({
                'employee_summary': {
                    'total_employees': 0,
                    'male_count': 0,
                    'female_count': 0,
                    'total_monthly_salary': 0
                },
                'department_distribution': [],
                'attendance_rate': 0,
                'upcoming_leave': []
            })


# ==================== INSIGHTS ====================

class InsightsView(APIView):
    """Get generated business insights and recommendations"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            data = service.generate_insights()
            return Response({
                'insights': data,
                'count': len(data)
            })
        except Exception as e:
            print(f"Error in InsightsView: {e}")
            return Response({'insights': [], 'count': 0})


class MarkInsightReadView(APIView):
    """Mark an insight as read"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def post(self, request, pk):
        try:
            insight = BusinessInsight.objects.get(pk=pk, business=request.user.business)
            insight.is_read = True
            insight.save()
            return Response({'message': 'Insight marked as read'})
        except BusinessInsight.DoesNotExist:
            return Response({'error': 'Insight not found'}, status=404)
        except Exception as e:
            print(f"Error in MarkInsightReadView: {e}")
            return Response({'error': 'Failed to mark insight as read'}, status=500)


# ==================== GOALS MANAGEMENT ====================

class GoalsListView(APIView):
    """List and create business goals"""
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get(self, request):
        try:
            goals = BusinessGoal.objects.filter(business=request.user.business)
            serializer = GoalSerializer(goals, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in GoalsListView: {e}")
            return Response([])
    
    def post(self, request):
        try:
            serializer = GoalSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(business=request.user.business)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error in GoalsListView POST: {e}")
            return Response({'error': 'Failed to create goal'}, status=500)


class GoalDetailView(APIView):
    """Update or delete a specific goal"""
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get(self, request, pk):
        try:
            goal = BusinessGoal.objects.get(pk=pk, business=request.user.business)
            serializer = GoalSerializer(goal)
            return Response(serializer.data)
        except BusinessGoal.DoesNotExist:
            return Response({'error': 'Goal not found'}, status=404)
        except Exception as e:
            print(f"Error in GoalDetailView GET: {e}")
            return Response({'error': 'Failed to retrieve goal'}, status=500)
    
    def patch(self, request, pk):
        try:
            goal = BusinessGoal.objects.get(pk=pk, business=request.user.business)
            serializer = GoalSerializer(goal, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusinessGoal.DoesNotExist:
            return Response({'error': 'Goal not found'}, status=404)
        except Exception as e:
            print(f"Error in GoalDetailView PATCH: {e}")
            return Response({'error': 'Failed to update goal'}, status=500)
    
    def delete(self, request, pk):
        try:
            goal = BusinessGoal.objects.get(pk=pk, business=request.user.business)
            goal.delete()
            return Response({'message': 'Goal deleted'})
        except BusinessGoal.DoesNotExist:
            return Response({'error': 'Goal not found'}, status=404)
        except Exception as e:
            print(f"Error in GoalDetailView DELETE: {e}")
            return Response({'error': 'Failed to delete goal'}, status=500)


# ==================== DASHBOARD WIDGETS ====================

class DashboardWidgetsView(APIView):
    """Get and configure dashboard widgets"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            if user_id and str(request.user.id) != user_id and not request.user.is_superuser:
                return Response({'error': 'Unauthorized'}, status=403)
            
            if user_id:
                widgets = DashboardWidget.objects.filter(
                    business=request.user.business,
                    user_id=user_id
                )
            else:
                widgets = DashboardWidget.objects.filter(
                    business=request.user.business,
                    user__isnull=True
                )
            
            serializer = DashboardWidgetSerializer(widgets, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in DashboardWidgetsView: {e}")
            return Response([])
    
    def post(self, request):
        try:
            serializer = DashboardWidgetSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(business=request.user.business, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error in DashboardWidgetsView POST: {e}")
            return Response({'error': 'Failed to create widget'}, status=500)


class DashboardWidgetReorderView(APIView):
    """Reorder dashboard widgets"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def post(self, request):
        try:
            widget_ids = request.data.get('widget_ids', [])
            for position, widget_id in enumerate(widget_ids):
                DashboardWidget.objects.filter(
                    id=widget_id,
                    business=request.user.business
                ).update(position=position)
            return Response({'message': 'Widgets reordered'})
        except Exception as e:
            print(f"Error in DashboardWidgetReorderView: {e}")
            return Response({'error': 'Failed to reorder widgets'}, status=500)


# ==================== EXECUTIVE DASHBOARD ====================

class ExecutiveDashboardView(APIView):
    """Complete executive dashboard combining all BI data"""
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        try:
            service = BusinessIntelligenceService(request.user.business)
            
            kpi = service.get_kpi_dashboard()
            trends = service.get_trends(30)
            top_products = service.get_top_products(5)
            customers = service.get_customer_insights()
            forecast = service.get_sales_forecast(30)
            insights = service.generate_insights()
            
            return Response({
                'business_name': request.user.business.name,
                'generated_at': timezone.now().isoformat(),
                'kpi': kpi,
                'trends': trends,
                'top_products': top_products,
                'customer_insights': customers,
                'forecast': forecast,
                'insights': insights[:5]
            })
        except Exception as e:
            print(f"Error in ExecutiveDashboardView: {e}")
            return Response({
                'business_name': request.user.business.name if request.user.business else 'Business',
                'generated_at': timezone.now().isoformat(),
                'kpi': {},
                'trends': {},
                'top_products': [],
                'customer_insights': {},
                'forecast': {},
                'insights': []
            })


# ==================== CACHE MANAGEMENT ====================

class ClearCacheView(APIView):
    """Clear BI cache for the business"""
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def post(self, request):
        try:
            from django.core.cache import cache
            
            # Clear all cache keys for this business
            business_id = request.user.business.id
            cache_keys = [
                f"bi_kpi_{business_id}_*",
                f"bi_trends_{business_id}_*",
                f"bi_top_products_{business_id}_*",
                f"bi_slow_products_{business_id}_*",
                f"bi_customer_insights_{business_id}_*",
                f"bi_forecast_{business_id}_*",
                f"bi_insights_{business_id}_*",
                f"bi_profit_loss_{business_id}_*",
                f"bi_gross_margin_{business_id}_*",
                f"bi_inventory_turnover_{business_id}_*",
            ]
            
            for pattern in cache_keys:
                cache.delete_pattern(pattern)
            
            return Response({'message': 'BI cache cleared successfully'})
        except Exception as e:
            print(f"Error in ClearCacheView: {e}")
            return Response({'error': 'Failed to clear cache'}, status=500)