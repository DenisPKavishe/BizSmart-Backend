from rest_framework import serializers
from .models import Budget, BudgetItem, Transaction, Invoice, InvoiceItem, Loan, PettyCash, CashFlowForecast

class TransactionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    cost_type_display = serializers.CharField(source='get_cost_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'unit_price', 'created_at']

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'total']

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'balance_due', 'is_overdue']

class LoanSerializer(serializers.ModelSerializer):
    loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    balance_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'balance_remaining']

class PettyCashSerializer(serializers.ModelSerializer):
    class Meta:
        model = PettyCash
        fields = '__all__'
        read_only_fields = ['id', 'date']

class CashFlowForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlowForecast
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'closing_balance']



# financials/serializers.py - Add these after your existing serializers

class BudgetItemSerializer(serializers.ModelSerializer):
    """Serializer for budget items with calculated actual amounts"""
    
    actual_amount = serializers.SerializerMethodField()
    variance = serializers.SerializerMethodField()
    variance_percentage = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = BudgetItem
        fields = ['id', 'budget', 'category', 'category_name', 'type', 'type_display',
                  'planned_amount', 'actual_amount', 'variance', 'variance_percentage',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'actual_amount', 'variance', 'variance_percentage']
    
    def get_actual_amount(self, obj):
        """Calculate actual amount from transactions for this budget period"""
        request = self.context.get('request')
        if not request:
            return 0
        
        budget = obj.budget
        # Get date range based on budget period
        from django.utils import timezone
        from datetime import datetime
        
        if budget.period == 'monthly' and budget.month:
            start_date = datetime(budget.year, budget.month, 1).date()
            if budget.month == 12:
                end_date = datetime(budget.year + 1, 1, 1).date()
            else:
                end_date = datetime(budget.year, budget.month + 1, 1).date()
        elif budget.period == 'quarterly' and budget.quarter:
            quarter_months = {1: (1, 4), 2: (4, 7), 3: (7, 10), 4: (10, 13)}
            start_month, end_month = quarter_months[budget.quarter]
            start_date = datetime(budget.year, start_month, 1).date()
            end_date = datetime(budget.year, end_month, 1).date()
        else:  # yearly
            start_date = datetime(budget.year, 1, 1).date()
            end_date = datetime(budget.year + 1, 1, 1).date()
        
        # Sum transactions matching category within date range
        from .models import Transaction
        
        actual = Transaction.objects.filter(
            business=request.user.business,
            category=obj.category,
            transaction_date__gte=start_date,
            transaction_date__lt=end_date
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        return float(actual)
    
    def get_variance(self, obj):
        """Calculate variance (actual - planned)"""
        actual = self.get_actual_amount(obj)
        return float(actual - obj.planned_amount)
    
    def get_variance_percentage(self, obj):
        """Calculate variance percentage"""
        if obj.planned_amount > 0:
            actual = self.get_actual_amount(obj)
            return float(((actual - obj.planned_amount) / obj.planned_amount) * 100)
        return 0


class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for budgets with summary calculations"""
    
    items = BudgetItemSerializer(many=True, read_only=True)
    total_planned_income = serializers.SerializerMethodField()
    total_actual_income = serializers.SerializerMethodField()
    total_planned_expenses = serializers.SerializerMethodField()
    total_actual_expenses = serializers.SerializerMethodField()
    planned_profit = serializers.SerializerMethodField()
    actual_profit = serializers.SerializerMethodField()
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Budget
        fields = ['id', 'name', 'period', 'period_display', 'year', 'month', 'quarter',
                  'status', 'status_display', 'notes', 'items',
                  'total_planned_income', 'total_actual_income',
                  'total_planned_expenses', 'total_actual_expenses',
                  'planned_profit', 'actual_profit',
                  'created_at', 'updated_at', 'created_by', 'business']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'business']
    
    def get_total_planned_income(self, obj):
        """Sum planned amounts for income items"""
        total = obj.items.filter(type='income').aggregate(
            total=models.Sum('planned_amount')
        )['total'] or 0
        return float(total)
    
    def get_total_actual_income(self, obj):
        """Sum actual amounts for income items"""
        total = 0
        for item in obj.items.filter(type='income'):
            total += BudgetItemSerializer(context=self.context).get_actual_amount(item)
        return float(total)
    
    def get_total_planned_expenses(self, obj):
        """Sum planned amounts for expense items"""
        total = obj.items.filter(type='expense').aggregate(
            total=models.Sum('planned_amount')
        )['total'] or 0
        return float(total)
    
    def get_total_actual_expenses(self, obj):
        """Sum actual amounts for expense items"""
        total = 0
        for item in obj.items.filter(type='expense'):
            total += BudgetItemSerializer(context=self.context).get_actual_amount(item)
        return float(total)
    
    def get_planned_profit(self, obj):
        """Calculate planned profit"""
        return self.get_total_planned_income(obj) - self.get_total_planned_expenses(obj)
    
    def get_actual_profit(self, obj):
        """Calculate actual profit"""
        return self.get_total_actual_income(obj) - self.get_total_actual_expenses(obj)
    
    def create(self, validated_data):
        validated_data['business'] = self.context['request'].user.business
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class BudgetItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating budget items"""
    
    class Meta:
        model = BudgetItem
        fields = ['id', 'category', 'category_name', 'type', 'planned_amount', 'notes']


class BudgetSummarySerializer(serializers.Serializer):
    """Serializer for budget summary across periods"""
    
    period = serializers.CharField()
    total_planned_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_actual_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_planned_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_actual_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    planned_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    actual_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2)
    variance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)        