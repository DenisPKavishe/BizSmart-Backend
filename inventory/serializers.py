# inventory/serializers.py

from rest_framework import serializers
from decimal import Decimal
from .models import Category, Supplier, Product, StockMovement, PurchaseOrder, PurchaseOrderItem


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    total_purchase_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address', 'tax_id', 
                  'product_count', 'total_purchase_orders', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    
    def get_total_purchase_orders(self, obj):
        return obj.purchase_orders.count()


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    profit_per_unit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'description',
            'category', 'category_name', 'supplier', 'supplier_name',
            'buying_price', 'selling_price', 'profit_per_unit', 'profit_margin_percentage',
            'quantity_on_hand', 'reorder_level', 'reorder_quantity', 'stock_value',
            'unit', 'image', 'is_active', 'total_investment',
            'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_investment', 'stock_value', 'created_at', 'updated_at']
    
    def get_stock_value(self, obj):
        return float(obj.quantity_on_hand * obj.buying_price)


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'quantity', 'movement_type', 'movement_type_display',
            'unit_cost', 'total_cost', 'reference_id', 'reference_type', 'notes',
            'previous_quantity', 'new_quantity', 'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    remaining_quantity = serializers.SerializerMethodField()
    is_fully_received = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_cost', 
            'total_cost', 'quantity_received', 'remaining_quantity', 'is_fully_received'
        ]
    
    def get_remaining_quantity(self, obj):
        return obj.remaining_quantity
    
    def get_is_fully_received(self, obj):
        return obj.is_fully_received


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    total_received = serializers.SerializerMethodField()
    is_fully_received = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'order_date', 
            'expected_delivery', 'actual_delivery', 'subtotal', 'tax_amount',
            'total_amount', 'status', 'status_display', 'notes', 'items',
            'total_received', 'is_fully_received', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'po_number', 'created_at', 'updated_at']
    
    def get_total_received(self, obj):
        return sum(item.quantity_received for item in obj.items.all())
    
    def get_is_fully_received(self, obj):
        return all(item.is_fully_received for item in obj.items.all())


class CreatePurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, required=False)
    
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'expected_delivery', 'notes', 'items']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                **item_data
            )
        
        return purchase_order


class ReceiveItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)