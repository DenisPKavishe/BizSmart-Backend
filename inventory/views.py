# inventory/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import F, Sum, Q
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import Category, Supplier, Product, StockMovement, PurchaseOrder, PurchaseOrderItem
from .serializers import (
    CategorySerializer, SupplierSerializer, ProductSerializer,
    StockMovementSerializer, PurchaseOrderSerializer, CreatePurchaseOrderSerializer,
    ReceiveItemSerializer
)
from .permissions import (
    CanViewInventory, CanManageInventory, CanDeleteInventory,
    CanAdjustStock, CanViewSuppliers, CanManageSuppliers,
    CanViewCategories, CanManageCategories, IsAuditorInventoryReadOnly
)
from .barcode_generator import generate_barcode_for_product


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
        return [permissions.IsAuthenticated(), CanManageCategories(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return Category.objects.filter(business=self.request.user.business, is_active=True)
    
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
        return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Category.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        
        # Check if category has active products
        if category.products.filter(is_active=True).exists():
            return Response({
                'error': f'Cannot delete category "{category.name}" because it has {category.products.filter(is_active=True).count()} active products.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        category.is_active = False
        category.save()
        return Response({'message': 'Category deactivated successfully'})


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
        return [permissions.IsAuthenticated(), CanManageSuppliers(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Supplier.objects.none()
        return Supplier.objects.filter(business=self.request.user.business, is_active=True)
    
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
        return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Supplier.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        
        # Check if supplier has active products
        if supplier.products.filter(is_active=True).exists():
            return Response({
                'error': f'Cannot delete supplier "{supplier.name}" because it has {supplier.products.filter(is_active=True).count()} active products.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if supplier.purchase_orders.exists():
            return Response({
                'error': f'Cannot delete supplier "{supplier.name}" because it has {supplier.purchase_orders.count()} purchase orders.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        supplier.is_active = False
        supplier.save()
        return Response({'message': 'Supplier deactivated successfully'})


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
        return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()
        return Product.objects.filter(business=self.request.user.business, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product (soft delete).
    
    - View: Owner, Manager, Inventory Manager, Cashier, Auditor
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only (soft delete)
    """
    serializer_class = ProductSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
        return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return Product.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        
        # Check if product has sales records
        if product.sale_items.exists():
            return Response({
                'error': f'Cannot delete product "{product.name}" because it has sales records.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Soft delete - just deactivate
        product.is_active = False
        product.save()
        
        return Response({
            'message': f'Product "{product.name}" has been deactivated successfully.'
        }, status=status.HTTP_200_OK)


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
            quantity_on_hand__lte=F('reorder_level'),
            is_active=True
        )
        serializer = ProductSerializer(products, many=True)
        return Response({
            'count': products.count(),
            'products': serializer.data
        })


class ProductByBarcodeView(APIView):
    """
    Get product by barcode (for POS scanning and manual input)
    
    Access: Owner, Manager, Inventory Manager, Cashier
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get(self, request, barcode):
        self.check_permissions(request)
        
        try:
            product = Product.objects.get(
                barcode=barcode,
                business=request.user.business,
                is_active=True
            )
            return Response(ProductSerializer(product).data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found with this barcode'}, status=404)


class StockValuationReportView(APIView):
    """Stock valuation report"""
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get(self, request):
        self.check_permissions(request)
        
        products = Product.objects.filter(
            business=request.user.business,
            is_active=True
        )
        
        total_value = Decimal('0')
        by_category = {}
        low_stock_count = 0
        out_of_stock_count = 0
        
        for product in products:
            value = product.quantity_on_hand * product.buying_price
            total_value += value
            
            if product.quantity_on_hand == 0:
                out_of_stock_count += 1
            elif product.is_low_stock:
                low_stock_count += 1
            
            category_name = product.category.name if product.category else 'Uncategorized'
            if category_name not in by_category:
                by_category[category_name] = {
                    'category': category_name,
                    'total_quantity': 0,
                    'total_value': Decimal('0')
                }
            
            by_category[category_name]['total_quantity'] += product.quantity_on_hand
            by_category[category_name]['total_value'] += value
        
        return Response({
            'total_stock_value': float(total_value),
            'total_items': products.count(),
            'by_category': list(by_category.values()),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count
        })


class GenerateProductBarcodeView(APIView):
    """
    Generate barcode for a specific product.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageInventory()]
    
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            product = Product.objects.get(pk=pk, business=request.user.business)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        
        method = request.data.get('method', 'auto')
        barcode = generate_barcode_for_product(product, method)
        
        product.barcode = barcode
        product.save()
        
        return Response({
            'message': f'Barcode generated for {product.name}',
            'product_id': product.id,
            'product_name': product.name,
            'barcode': barcode,
            'method': method
        })


class BulkGenerateBarcodesView(APIView):
    """
    Generate barcodes for all products without barcodes.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageInventory()]
    
    def post(self, request):
        self.check_permissions(request)
        
        products_without_barcode = Product.objects.filter(
            business=request.user.business,
            is_active=True,
            barcode=''
        )
        
        generated = []
        for product in products_without_barcode:
            barcode = generate_barcode_for_product(product)
            product.barcode = barcode
            product.save()
            generated.append({
                'id': product.id,
                'name': product.name,
                'barcode': barcode
            })
        
        return Response({
            'message': f'Generated {len(generated)} barcodes',
            'generated': generated
        })


class PrintBarcodeLabelView(APIView):
    """
    Generate barcode label for printing.
    
    Access: Owner, Manager, Inventory Manager, Cashier
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get(self, request, pk):
        self.check_permissions(request)
        
        try:
            product = Product.objects.get(pk=pk, business=request.user.business)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        
        # Generate HTML for printing
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Barcode Label - {product.name}</title>
            <style>
                @page {{
                    size: 50mm 30mm;
                    margin: 5mm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    text-align: center;
                }}
                .label {{
                    border: 1px solid #ccc;
                    padding: 10px;
                    border-radius: 5px;
                }}
                .product-name {{
                    font-size: 12px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .price {{
                    font-size: 14px;
                    color: green;
                    margin-top: 5px;
                }}
                .barcode {{
                    font-family: 'Courier New', monospace;
                    font-size: 18px;
                    letter-spacing: 2px;
                    margin: 10px 0;
                }}
                .sku {{
                    font-size: 10px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="label">
                <div class="product-name">{product.name}</div>
                <div class="barcode">*{product.barcode}*</div>
                <div class="price">TZS {product.selling_price:,.0f}</div>
                <div class="sku">SKU: {product.sku}</div>
            </div>
        </body>
        </html>
        """
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html')


class BulkPrintBarcodeLabelsView(APIView):
    """
    Generate multiple barcode labels for printing.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanManageInventory()]
    
    def post(self, request):
        self.check_permissions(request)
        
        product_ids = request.data.get('product_ids', [])
        
        if not product_ids:
            return Response({'error': 'No products selected'}, status=400)
        
        products = Product.objects.filter(
            id__in=product_ids,
            business=request.user.business,
            is_active=True
        )
        
        # Generate HTML for multiple labels (2 per row)
        labels_html = ""
        for product in products:
            labels_html += f"""
            <div class="label">
                <div class="product-name">{product.name}</div>
                <div class="barcode">*{product.barcode}*</div>
                <div class="price">TZS {product.selling_price:,.0f}</div>
                <div class="sku">SKU: {product.sku}</div>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Barcode Labels</title>
            <style>
                @page {{
                    size: A4;
                    margin: 10mm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                }}
                .labels-container {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                }}
                .label {{
                    border: 1px solid #ccc;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    page-break-inside: avoid;
                }}
                .product-name {{
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 8px;
                }}
                .barcode {{
                    font-family: 'Courier New', monospace;
                    font-size: 20px;
                    letter-spacing: 2px;
                    margin: 15px 0;
                }}
                .price {{
                    font-size: 16px;
                    color: green;
                    font-weight: bold;
                }}
                .sku {{
                    font-size: 10px;
                    color: #666;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="labels-container">
                {labels_html}
            </div>
        </body>
        </html>
        """
        
        from django.http import HttpResponse
        return HttpResponse(html_content, content_type='text/html')


# ==================== STOCK MOVEMENTS ====================
class StockInView(APIView):
    """
    Add stock to inventory - for purchases.
    
    Access: Owner, Manager, Inventory Manager only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    @transaction.atomic
    def post(self, request):
        self.check_permissions(request)
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0))
        unit_cost = Decimal(str(request.data.get('unit_cost', 0)))
        notes = request.data.get('notes', '')
        
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero'}, status=400)
        
        if unit_cost <= 0:
            return Response({'error': 'Unit cost must be greater than zero'}, status=400)
        
        try:
            product = Product.objects.select_for_update().get(
                id=product_id, 
                business=request.user.business
            )
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)
        
        previous_qty = product.quantity_on_hand
        previous_cost = product.buying_price
        
        # Update average cost using FIFO/Average Cost method
        product.update_average_cost(quantity, unit_cost)
        
        # Create stock movement record
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
            'movement': StockMovementSerializer(movement).data,
            'cost_update': {
                'old_cost': float(previous_cost),
                'new_cost': float(product.buying_price)
            }
        }, status=status.HTTP_201_CREATED)


class StockOutView(APIView):
    """
    Remove stock from inventory - for sales or adjustments.
    
    Access: Owner, Manager, Inventory Manager only
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    @transaction.atomic
    def post(self, request):
        self.check_permissions(request)
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', 'adjustment')
        reference_id = request.data.get('reference_id', '')
        notes = request.data.get('notes', '')
        
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero'}, status=400)
        
        try:
            product = Product.objects.select_for_update().get(
                id=product_id, 
                business=request.user.business
            )
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
        
        # Determine movement type
        movement_type = 'OUT'
        if reason == 'damaged':
            movement_type = 'DAMAGED'
        elif reason == 'return_to_supplier':
            movement_type = 'RETURN_OUT'
        elif reason == 'stock_take':
            movement_type = 'STOCK_TAKE'
        
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


class StockMovementReportView(APIView):
    """
    Stock movement report with filters.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewInventory()]
    
    def get(self, request):
        self.check_permissions(request)
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        product_id = request.query_params.get('product_id')
        movement_type = request.query_params.get('movement_type')
        
        movements = StockMovement.objects.filter(business=request.user.business)
        
        if start_date:
            movements = movements.filter(created_at__date__gte=start_date)
        if end_date:
            movements = movements.filter(created_at__date__lte=end_date)
        if product_id:
            movements = movements.filter(product_id=product_id)
        if movement_type:
            movements = movements.filter(movement_type=movement_type)
        
        # Summary
        total_in = movements.filter(movement_type='IN').aggregate(total=Sum('quantity'))['total'] or 0
        total_out = movements.filter(movement_type='OUT').aggregate(total=Sum('quantity'))['total'] or 0
        
        return Response({
            'total_movements': movements.count(),
            'total_in': total_in,
            'total_out': total_out,
            'movements': StockMovementSerializer(movements[:100], many=True).data
        })


# ==================== PURCHASE ORDERS ====================
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    """
    List all purchase orders or create a new one.
    
    - View: Owner, Manager, Inventory Manager
    - Create: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PurchaseOrder.objects.none()
        return PurchaseOrder.objects.filter(business=self.request.user.business)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePurchaseOrderSerializer
        return PurchaseOrderSerializer
    
    @transaction.atomic
    def perform_create(self, serializer):
        # Generate unique PO number with lock to prevent race condition
        with transaction.atomic():
            last_po = PurchaseOrder.objects.filter(
                business=self.request.user.business
            ).select_for_update().order_by('-id').first()
            
            year = date.today().year
            if last_po and last_po.po_number:
                try:
                    last_num = int(last_po.po_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            po_number = f"PO-{year}-{new_num:04d}"
        
        serializer.save(
            business=self.request.user.business,
            po_number=po_number,
            created_by=self.request.user,
            status='draft'
        )


class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a purchase order.
    
    - View: Owner, Manager, Inventory Manager
    - Update: Owner, Manager, Inventory Manager
    - Delete: Owner only
    """
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewInventory(), IsAuditorInventoryReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageInventory(), IsAuditorInventoryReadOnly()]
        return [permissions.IsAuthenticated(), CanDeleteInventory(), IsAuditorInventoryReadOnly()]
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(business=self.request.user.business)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CreatePurchaseOrderSerializer
        return PurchaseOrderSerializer


class ReceivePurchaseOrderView(APIView):
    """
    Receive items from purchase order and add to inventory.
    Supports partial receiving.
    
    Access: Owner, Manager, Inventory Manager
    """
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanAdjustStock(), IsAuditorInventoryReadOnly()]
    
    @transaction.atomic
    def post(self, request, pk):
        self.check_permissions(request)
        
        try:
            po = PurchaseOrder.objects.select_for_update().get(
                pk=pk, 
                business=request.user.business
            )
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Purchase order not found'}, status=404)
        
        if po.status == 'completed':
            return Response({'error': 'Purchase order already fully received'}, status=400)
        
        if po.status == 'cancelled':
            return Response({'error': 'Cannot receive cancelled purchase order'}, status=400)
        
        # Get items to receive (support both single item and multiple items)
        items_to_receive = request.data.get('items', [])
        
        if not items_to_receive:
            # Legacy support: receive all remaining items
            items_to_receive = [
                {'item_id': item.id, 'quantity': item.remaining_quantity}
                for item in po.items.all() if item.remaining_quantity > 0
            ]
        
        received_items = []
        errors = []
        
        for receive_item in items_to_receive:
            item_id = receive_item.get('item_id')
            quantity = int(receive_item.get('quantity', 0))
            
            try:
                po_item = PurchaseOrderItem.objects.select_for_update().get(
                    id=item_id, 
                    purchase_order=po
                )
            except PurchaseOrderItem.DoesNotExist:
                errors.append(f'Item {item_id} not found')
                continue
            
            if quantity <= 0:
                errors.append(f'Invalid quantity for {po_item.product.name}')
                continue
            
            if quantity > po_item.remaining_quantity:
                errors.append(f'Cannot receive {quantity} units of {po_item.product.name}. Only {po_item.remaining_quantity} remaining.')
                continue
            
            # Update PO item
            po_item.quantity_received += quantity
            po_item.save()
            
            # Update product stock with average cost
            product = po_item.product
            product.update_average_cost(quantity, po_item.unit_cost)
            
            # Create stock movement record
            StockMovement.objects.create(
                business=request.user.business,
                product=product,
                quantity=quantity,
                movement_type='IN',
                unit_cost=po_item.unit_cost,
                total_cost=po_item.unit_cost * quantity,
                reference_id=po.po_number,
                reference_type='purchase_order',
                notes=f'Received from PO {po.po_number} - {quantity} units',
                created_by=request.user
            )
            
            received_items.append(f'{quantity} x {product.name}')
        
        if errors:
            return Response({
                'partial_success': True,
                'message': f'Received: {", ".join(received_items)}',
                'errors': errors,
                'purchase_order': PurchaseOrderSerializer(po).data
            }, status=status.HTTP_207_MULTI_STATUS)
        
        # Update PO status based on receiving progress
        all_received = all(item.is_fully_received for item in po.items.all())
        if all_received:
            po.status = 'completed'
            po.actual_delivery = date.today()
        elif any(item.quantity_received > 0 for item in po.items.all()):
            po.status = 'partial'
        
        po.save()
        
        return Response({
            'message': f'Received: {", ".join(received_items)}',
            'purchase_order': PurchaseOrderSerializer(po).data
        }, status=status.HTTP_200_OK)