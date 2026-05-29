# sales/serializers.py

from rest_framework import serializers
from .models import Customer, Sale, SaleItem, Return

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['id', 'total_spent', 'total_visits', 'created_at', 'updated_at']


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = ['id', 'sale', 'product', 'product_name', 'product_sku', 
                  'quantity', 'unit_price', 'cost_price', 'total_price', 'discount_amount']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = [
            'id', 'invoice_number', 'sale_date', 'change_amount', 
            'created_at', 'updated_at'
        ]


class ProcessSaleSerializer(serializers.Serializer):
    """Serializer for processing a sale with items"""
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_method = serializers.ChoiceField(choices=Sale.PAYMENT_METHODS, default='cash')
    amount_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError("Each item must have product_id")
            if 'quantity' not in item:
                raise serializers.ValidationError("Each item must have quantity")
        return value


class ReturnSerializer(serializers.ModelSerializer):
    sale_invoice = serializers.CharField(source='sale.invoice_number', read_only=True)
    product_name = serializers.CharField(source='sale_item.product.name', read_only=True)
    
    class Meta:
        model = Return
        fields = '__all__'
        read_only_fields = ['id', 'created_at']