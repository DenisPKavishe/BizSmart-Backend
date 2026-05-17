from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .services import BusinessIntelligenceService
from .permissions import (
    CanViewBIDashboard, CanViewFinancialBI, CanViewInventoryBI,
    CanViewSalesBI, IsOwnerOnly
)


class KPIDashboardView(APIView):
    """
    Get main KPI dashboard with key metrics.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_kpi_dashboard()
        return Response(data)


class TrendAnalysisView(APIView):
    """
    Get sales and profit trends over time.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_trends(days)
        return Response(data)


class TopProductsView(APIView):
    """
    Get top selling products.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_top_products(limit)
        return Response({
            'top_products': data,
            'count': len(data)
        })


class SlowMovingProductsView(APIView):
    """
    Get products that are not selling well.
    
    Access: Owner, Manager, Inventory Manager
    """
    permission_classes = [IsAuthenticated, CanViewInventoryBI]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_slow_moving_products(days)
        return Response({
            'slow_moving_products': data,
            'count': len(data)
        })


class CustomerInsightsView(APIView):
    """
    Get customer behavior insights and segmentation.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_customer_insights()
        return Response(data)


class SalesForecastView(APIView):
    """
    Get sales forecast predictions.
    
    Access: Owner only (sensitive business projection)
    """
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_sales_forecast(days)
        return Response(data)


class InsightsView(APIView):
    """
    Get generated business insights and recommendations.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        data = service.generate_insights()
        return Response({
            'insights': data,
            'count': len(data)
        })


class ProfitLossView(APIView):
    """
    Get Profit & Loss statement.
    
    Access: Owner, Accountant only (financial sensitivity)
    """
    permission_classes = [IsAuthenticated, CanViewFinancialBI]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        service = BusinessIntelligenceService(request.user.business)
        data = service.get_profit_loss(start_date, end_date)
        return Response(data)


class ExecutiveDashboardView(APIView):
    """
    Complete executive dashboard combining all BI data.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewBIDashboard]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        
        # Get all BI data
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
            'insights': insights[:5]  # Top 5 insights only
        })


class InventoryAnalyticsView(APIView):
    """
    Get inventory-specific analytics.
    
    Access: Owner, Manager, Inventory Manager
    """
    permission_classes = [IsAuthenticated, CanViewInventoryBI]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        
        # Get inventory specific data
        top_products = service.get_top_products(10)
        slow_products = service.get_slow_moving_products(30)
        
        # Calculate inventory turnover
        from inventory.models import Product
        from django.db.models import Sum, F
        
        total_inventory_value = Product.objects.filter(
            business=request.user.business
        ).aggregate(Sum('total_investment'))['total_investment__sum'] or 0
        
        low_stock_count = Product.objects.filter(
            business=request.user.business,
            quantity_on_hand__lte=F('reorder_level'),
            is_active=True
        ).count()
        
        out_of_stock_count = Product.objects.filter(
            business=request.user.business,
            quantity_on_hand=0,
            is_active=True
        ).count()
        
        return Response({
            'inventory_summary': {
                'total_value': float(total_inventory_value),
                'low_stock_items': low_stock_count,
                'out_of_stock_items': out_of_stock_count,
                'total_products': Product.objects.filter(business=request.user.business, is_active=True).count()
            },
            'top_products': top_products[:5],
            'slow_moving_products': slow_products[:5]
        })


class FinancialSummaryView(APIView):
    """
    Get financial summary for dashboard.
    
    Access: Owner, Accountant only
    """
    permission_classes = [IsAuthenticated, CanViewFinancialBI]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        
        # Get current month data
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        profit_loss = service.get_profit_loss(start_of_month, today)
        kpi = service.get_kpi_dashboard()
        
        return Response({
            'current_month_profit_loss': profit_loss,
            'key_metrics': {
                'revenue': kpi['revenue'],
                'expenses': kpi['expenses'],
                'profit': kpi['profit'],
                'margins': kpi['margins']
            }
        })


class SalesPerformanceView(APIView):
    """
    Get sales performance analytics.
    
    Access: Owner, Manager, Accountant, Auditor
    """
    permission_classes = [IsAuthenticated, CanViewSalesBI]
    
    def get(self, request):
        service = BusinessIntelligenceService(request.user.business)
        
        period = request.query_params.get('period', 'month')  # week, month, year
        
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
        
        # Calculate sales by day of week
        from sales.models import Sale
        from django.db.models import Sum
        from django.utils import timezone
        
        start_date = timezone.now().date() - timedelta(days=90)
        sales_by_weekday = Sale.objects.filter(
            business=request.user.business,
            status='completed',
            sale_date__date__gte=start_date
        ).extra({
            'weekday': "strftime('%%w', sale_date)"
        }).values('weekday').annotate(
            total=Sum('total_amount')
        ).order_by('weekday')
        
        weekday_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        weekday_data = []
        for item in sales_by_weekday:
            weekday_data.append({
                'day': weekday_names[int(item['weekday'])],
                'total_sales': float(item['total'])
            })
        
        return Response({
            'period': period,
            'trends': trends,
            'top_products': top_products,
            'customer_insights': customers,
            'sales_by_weekday': weekday_data
        })