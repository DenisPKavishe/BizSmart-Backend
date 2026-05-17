from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models as django_models
from decimal import Decimal
from datetime import date
from .models import Category, Supplier, Product, StockMovement, PurchaseOrder, PurchaseOrderItem
from .serializers import (
    CategorySerializer, SupplierSerializer, ProductSerializer,
    StockMovementSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer
)
from .permissions import (
    CanViewInventory, CanManageInventory, CanDeleteInventory,
    CanAdjustStock, CanViewSuppliers, CanManageSuppliers,
    CanViewCategories, CanManageCategories, IsAuditorInventoryReadOnly
)


# ==================== CATEGORIES ====================
class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List all categories or create a new category.
    
    - View: Owner, Manager, Inventory Manager, Cashier, Auditor
    - Create/Edit: Owner, Manager, Inventory Manager
    """
    serializer_class = CategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewCategories(), IsAuditorInventoryReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageCategories(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return Category.objects.filter(business=self.request.user.business)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a category.
    
    - View: Owner, Manager, Inventory Manager, Cashier, Auditor
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only
    """
    serializer_class = CategorySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewCategories(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageCategories(), IsAuditorInventoryReadOnly()]
        else:  # DELETE
            return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Category.objects.filter(business=self.request.user.business)


# ==================== SUPPLIERS ====================
class SupplierListCreateView(generics.ListCreateAPIView):
    """
    List all suppliers or create a new supplier.
    
    - View: Owner, Manager, Inventory Manager, Auditor
    - Create/Edit: Owner, Manager, Inventory Manager
    """
    serializer_class = SupplierSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSuppliers(), IsAuditorInventoryReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageSuppliers(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Supplier.objects.none()
        return Supplier.objects.filter(business=self.request.user.business)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a supplier.
    
    - View: Owner, Manager, Inventory Manager, Auditor
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only
    """
    serializer_class = SupplierSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSuppliers(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageSuppliers(), IsAuditorInventoryReadOnly()]
        else:  # DELETE
            return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Supplier.objects.filter(business=self.request.user.business)


# ==================== PRODUCTS ====================
class ProductListCreateView(generics.ListCreateAPIView):
    """
    List all products or create a new product.
    
    - View: Owner, Manager, Inventory Manager, Cashier, Auditor
    - Create/Edit: Owner, Manager, Inventory Manager
    """
    serializer_class = ProductSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()
        return Product.objects.filter(business=self.request.user.business)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product.
    
    - View: Owner, Manager, Inventory Manager, Cashier, Auditor
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only
    """
    serializer_class = ProductSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
        else:  # DELETE
            return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Product.objects.filter(business=self.request.user.business)


class LowStockProductsView(APIView):
    """
    Get products with low stock levels.
    
    Access: Owner, Manager, Inventory Manager, Cashier (to know what to reorder)
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get(self, request):
        self.check_permissions(request)
        
        products = Product.objects.filter(
            business=request.user.business,
            quantity_on_hand__lte=django_models.F('reorder_level'),
            is_active=True
        )
        serializer = ProductSerializer(products, many=True)
        return Response({
            'count': products.count(),
            'products': serializer.data
        })


# ==================== STOCK MOVEMENTS ====================
class StockInView(APIView):
    """
    Add stock to inventory - for purchases.
    
    Access: Owner, Manager, Inventory Manager only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    def post(self, request):
        self.check_permissions(request)
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0))
        unit_cost = Decimal(request.data.get('unit_cost', 0))
        notes = request.data.get('notes', '')
        
        try:
            product = Product.objects.get(id=product_id, business=request.user.business)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        
        previous_qty = product.quantity_on_hand
        
        product.quantity_on_hand += quantity
        product.total_investment = product.buying_price * product.quantity_on_hand
        product.save()
        
        movement = StockMovement.objects.create(
            business=request.user.business,
            product=product,
            quantity=quantity,
            movement_type='IN',
            unit_cost=unit_cost,
            total_cost=unit_cost * quantity,
            notes=notes,
            previous_quantity=previous_qty,
            new_quantity=product.quantity_on_hand,
            created_by=request.user
        )
        
        return Response({
            'message': f'Added {quantity} {product.unit}(s) to {product.name}',
            'product': ProductSerializer(product).data,
            'movement': StockMovementSerializer(movement).data
        }, status=status.HTTP_201_CREATED)


class StockOutView(APIView):
    """
    Remove stock from inventory - for sales or adjustments.
    
    Access: Owner, Manager, Inventory Manager only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    def post(self, request):
        self.check_permissions(request)
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', 'adjustment')
        reference_id = request.data.get('reference_id', '')
        notes = request.data.get('notes', '')
        
        try:
            product = Product.objects.get(id=product_id, business=request.user.business)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        
        if product.quantity_on_hand < quantity:
            return Response({
                'error': f'Insufficient stock. Available: {product.quantity_on_hand}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        previous_qty = product.quantity_on_hand
        
        product.quantity_on_hand -= quantity
        product.total_investment = product.buying_price * product.quantity_on_hand
        product.save()
        
        movement_type = 'OUT'
        if reason == 'damaged':
            movement_type = 'DAMAGED'
        elif reason == 'return_to_supplier':
            movement_type = 'RETURN_OUT'
        
        movement = StockMovement.objects.create(
            business=request.user.business,
            product=product,
            quantity=quantity,
            movement_type=movement_type,
            unit_cost=product.buying_price,
            total_cost=product.buying_price * quantity,
            reference_id=reference_id,
            reference_type=reason,
            notes=notes,
            previous_quantity=previous_qty,
            new_quantity=product.quantity_on_hand,
            created_by=request.user
        )
        
        return Response({
            'message': f'Removed {quantity} {product.unit}(s) from {product.name}',
            'product': ProductSerializer(product).data,
            'movement': StockMovementSerializer(movement).data
        }, status=status.HTTP_201_CREATED)


class StockMovementListView(generics.ListAPIView):
    """
    View all stock movements.
    
    Access: Owner, Manager, Inventory Manager only
    """
    serializer_class = StockMovementSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return StockMovement.objects.none()
        return StockMovement.objects.filter(business=self.request.user.business)


# ==================== PURCHASE ORDERS ====================
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    """
    List all purchase orders or create a new one.
    
    - View: Owner, Manager, Inventory Manager
    - Create: Owner, Manager, Inventory Manager
    """
    serializer_class = PurchaseOrderSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        else:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PurchaseOrder.objects.none()
        return PurchaseOrder.objects.filter(business=self.request.user.business)
    
    def perform_create(self, serializer):
        po_count = PurchaseOrder.objects.filter(business=self.request.user.business).count() + 1
        po_number = f"PO-{date.today().year}-{po_count:04d}"
        serializer.save(
            business=self.request.user.business,
            po_number=po_number,
            created_by=self.request.user
        )


class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a purchase order.
    
    - View: Owner, Manager, Inventory Manager
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only
    """
    serializer_class = PurchaseOrderSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
        else:  # DELETE
            return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(business=self.request.user.business)


class ReceivePurchaseOrderView(APIView):
    """
    Receive items from purchase order and add to inventory.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            po = PurchaseOrder.objects.get(pk=pk, business=request.user.business)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Purchase order not found'}, status=404)
        
        items_received = []
        for item in po.items.all():
            if item.remaining_quantity > 0:
                product = item.product
                previous_qty = product.quantity_on_hand
                
                product.quantity_on_hand += item.remaining_quantity
                product.total_investment = product.buying_price * product.quantity_on_hand
                product.save()
                
                StockMovement.objects.create(
                    business=request.user.business,
                    product=product,
                    quantity=item.remaining_quantity,
                    movement_type='IN',
                    unit_cost=item.unit_cost,
                    total_cost=item.unit_cost * item.remaining_quantity,
                    reference_id=po.po_number,
                    reference_type='purchase_order',
                    notes=f'Received from PO {po.po_number}',
                    previous_quantity=previous_qty,
                    new_quantity=product.quantity_on_hand,
                    created_by=request.user
                )
                
                item.quantity_received = item.quantity
                item.save()
                items_received.append(product.name)
        
        po.status = 'completed'
        po.actual_delivery = date.today()
        po.save()
        
        return Response({
            'message': f'Received items: {", ".join(items_received)}',
            'purchase_order': PurchaseOrderSerializer(po).data
        })