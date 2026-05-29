# sales/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Sum, Count, F, Q, Prefetch
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from inventory.models import Product
from financials.models import Transaction
from .models import Customer, Sale, SaleItem, Return
from .serializers import (
    CustomerSerializer, SaleSerializer, SaleItemSerializer,
    ProcessSaleSerializer, ReturnSerializer
)
from .permissions import (
    CanProcessSale, CanViewSales, CanManageCustomers,
    CanViewSalesReports, CanProcessReturn, CanViewReceipt,
    IsAuditorSalesReadOnly
)


# ==================== HELPER FUNCTIONS ====================
def generate_invoice_number(business_id):
    """Generate unique invoice number with lock to prevent race condition"""
    from .models import Sale
    from django.db import transaction as db_transaction
    
    with db_transaction.atomic():
        today = timezone.now()
        prefix = f"INV-{today.strftime('%Y%m%d')}"
        
        last_sale = Sale.objects.select_for_update().filter(
            business_id=business_id,
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_sale and last_sale.invoice_number:
            try:
                last_num = int(last_sale.invoice_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"


def validate_discount(user, discount_percentage, discount_amount, subtotal):
    """Validate discount based on user role"""
    role = user.role.name.lower() if user.role else ''
    
    max_percentage = 100
    max_amount = subtotal
    
    if role == 'cashier':
        max_percentage = 10
        max_amount = subtotal * Decimal('0.1')
    elif role == 'general_manager':
        max_percentage = 30
        max_amount = subtotal * Decimal('0.3')
    # Owner has no limits
    
    if discount_percentage > max_percentage:
        raise ValueError(f'Discount cannot exceed {max_percentage}% for your role')
    
    if discount_amount > max_amount:
        raise ValueError(f'Discount cannot exceed TZS {max_amount:,.2f} for your role')
    
    return True


# ==================== CUSTOMERS ====================
class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
        return [permissions.IsAuthenticated(), CanManageCustomers(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Customer.objects.none()
        return Customer.objects.filter(business=self.request.user.business, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), CanManageCustomers(), IsAuditorSalesReadOnly()]
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        return Customer.objects.filter(business=self.request.user.business)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - just deactivate instead of deleting"""
        customer = self.get_object()
        
        if customer.sales.exists():
            # Deactivate instead of delete
            customer.is_active = False
            customer.save()
            return Response({'message': 'Customer deactivated successfully'})
        
        customer.delete()
        return Response({'message': 'Customer deleted successfully'})


# ==================== SALE ITEMS ====================
class SaleItemListCreateView(generics.ListCreateAPIView):
    serializer_class = SaleItemSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SaleItem.objects.none()
        return SaleItem.objects.filter(sale__business=self.request.user.business)
    
    def create(self, request, *args, **kwargs):
        return Response({
            'error': 'Use POST /api/v1/sales/sales/process/ to create sale items'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class SaleItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SaleItemSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        return SaleItem.objects.filter(sale__business=self.request.user.business)
    
    @transaction.atomic
    def perform_update(self, serializer):
        old_item = self.get_object()
        new_quantity = serializer.validated_data.get('quantity', old_item.quantity)
        old_quantity = old_item.quantity
        
        quantity_diff = old_quantity - new_quantity
        
        if quantity_diff != 0:
            product = old_item.product
            if quantity_diff > 0:
                product.quantity_on_hand += quantity_diff
            else:
                if product.quantity_on_hand < abs(quantity_diff):
                    raise serializers.ValidationError(
                        f"Insufficient stock. Available: {product.quantity_on_hand}"
                    )
                product.quantity_on_hand -= abs(quantity_diff)
            product.save()
        
        sale = old_item.sale
        old_total = old_item.total_price
        new_total = new_quantity * old_item.unit_price
        sale.subtotal = sale.subtotal - old_total + new_total
        sale.total_amount = sale.subtotal - sale.discount_amount
        sale.save()
        
        serializer.save()
    
    @transaction.atomic
    def perform_destroy(self, instance):
        product = instance.product
        product.quantity_on_hand += instance.quantity
        product.save()
        
        sale = instance.sale
        sale.subtotal -= instance.total_price
        sale.total_amount = sale.subtotal - sale.discount_amount
        sale.save()
        
        instance.delete()


# ==================== SALES ====================
class SaleListCreateView(generics.ListAPIView):
    serializer_class = SaleSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Sale.objects.none()
        
        # Optimized with select_related and prefetch_related to prevent N+1 queries
        queryset = Sale.objects.filter(
            business=self.request.user.business
        ).select_related(
            'customer', 'created_by'
        ).prefetch_related(
            Prefetch('items', queryset=SaleItem.objects.select_related('product'))
        )
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        status_filter = self.request.query_params.get('status')
        
        if start_date:
            queryset = queryset.filter(sale_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__date__lte=end_date)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        return Response({
            'error': 'Use POST /api/v1/sales/sales/process/ to create a sale'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class SaleDetailView(generics.RetrieveAPIView):
    serializer_class = SaleSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSales(), IsAuditorSalesReadOnly()]
    
    def get_queryset(self):
        return Sale.objects.filter(business=self.request.user.business)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        items = SaleItem.objects.filter(sale=instance).select_related('product')
        data['items'] = SaleItemSerializer(items, many=True).data
        
        return Response(data)


class SalePartialUpdateView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]
    
    @transaction.atomic
    def patch(self, request, pk):
        self.check_permissions(request)
        
        try:
            sale = Sale.objects.get(pk=pk, business=request.user.business)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found'}, status=404)
        
        if 'amount_paid' in request.data:
            new_amount = Decimal(str(request.data['amount_paid']))
            sale.amount_paid = new_amount
            if new_amount >= sale.total_amount:
                sale.status = 'completed'
            sale.save()
        
        if 'status' in request.data:
            old_status = sale.status
            new_status = request.data['status']
            
            if new_status == 'refunded' and old_status != 'refunded':
                for item in sale.items.all():
                    product = item.product
                    product.quantity_on_hand += item.quantity
                    product.save()
            
            sale.status = new_status
            sale.save()
        
        if 'notes' in request.data:
            sale.notes = request.data['notes']
            sale.save()
        
        items = SaleItem.objects.filter(sale=sale).select_related('product')
        data = SaleSerializer(sale).data
        data['items'] = SaleItemSerializer(items, many=True).data
        
        return Response({
            'message': 'Sale updated successfully',
            'sale': data
        })


class ProcessSaleView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanProcessSale(), IsAuditorSalesReadOnly()]
    
    @transaction.atomic
    def post(self, request):
        self.check_permissions(request)
        
        data = request.data
        business = request.user.business
        
        if not business:
            return Response({'error': 'No business associated with user'}, status=400)
        
        # Get or create customer
        customer = None
        if data.get('customer_id'):
            try:
                customer = Customer.objects.get(id=data['customer_id'], business=business, is_active=True)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=404)
        elif data.get('customer_name'):
            customer = Customer.objects.create(
                business=business,
                name=data['customer_name'],
                phone=data.get('customer_phone', ''),
                is_active=True
            )
        
        # Validate items
        items_data = data.get('items', [])
        if not items_data:
            return Response({'error': 'At least one item is required'}, status=400)
        
        # Generate invoice number (fixed race condition)
        invoice_number = generate_invoice_number(business.id)
        
        # Calculate totals and validate stock
        subtotal = Decimal('0')
        sale_items_data = []
        
        for item in items_data:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 0))
            
            if not product_id or quantity <= 0:
                return Response({'error': 'Invalid product or quantity'}, status=400)
            
            try:
                product = Product.objects.get(id=product_id, business=business, is_active=True)
            except Product.DoesNotExist:
                return Response({'error': f'Product {product_id} not found'}, status=404)
            
            if product.quantity_on_hand < quantity:
                return Response({
                    'error': f'Insufficient stock for {product.name}. Available: {product.quantity_on_hand}'
                }, status=400)
            
            item_total = product.selling_price * quantity
            subtotal += item_total
            
            sale_items_data.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.selling_price,
                'cost_price': product.buying_price,
                'total_price': item_total
            })
        
        # Calculate discounts with role validation
        discount_percentage = Decimal(str(data.get('discount_percentage', 0)))
        discount_amount = Decimal(str(data.get('discount_amount', 0)))
        
        # Validate discount based on user role
        try:
            validate_discount(request.user, discount_percentage, discount_amount, subtotal)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        
        if discount_percentage > 0 and discount_amount == 0:
            discount_amount = subtotal * (discount_percentage / 100)
        
        total_amount = subtotal - discount_amount
        amount_paid = Decimal(str(data.get('amount_paid', 0)))
        
        if amount_paid < total_amount:
            payment_method = data.get('payment_method', 'cash')
            if payment_method != 'credit':
                return Response({
                    'error': f'Amount paid ({amount_paid}) is less than total ({total_amount})'
                }, status=400)
        
        # Create sale
        sale = Sale.objects.create(
            business=business,
            customer=customer,
            created_by=request.user,
            invoice_number=invoice_number,
            subtotal=subtotal,
            discount_amount=discount_amount,
            discount_percentage=discount_percentage,
            total_amount=total_amount,
            payment_method=data.get('payment_method', 'cash'),
            amount_paid=amount_paid,
            status='completed' if amount_paid >= total_amount else 'pending',
            notes=data.get('notes', '')
        )
        
        # Create sale items and update inventory
        from inventory.models import StockMovement
        
        created_items = []
        for item_data in sale_items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            sale_item = SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=item_data['unit_price'],
                cost_price=item_data['cost_price'],
                total_price=item_data['total_price']
            )
            created_items.append(sale_item)
            
            # Update inventory
            product.quantity_on_hand -= quantity
            product.total_investment = product.buying_price * product.quantity_on_hand
            product.save()
            
            # Record stock movement
            StockMovement.objects.create(
                business=business,
                product=product,
                quantity=quantity,
                movement_type='OUT',
                unit_cost=product.buying_price,
                total_cost=product.buying_price * quantity,
                reference_id=sale.invoice_number,
                reference_type='sale',
                notes=f"Sale {sale.invoice_number}",
                previous_quantity=product.quantity_on_hand + quantity,
                new_quantity=product.quantity_on_hand,
                created_by=request.user
            )
        
        # Create financial transaction
        Transaction.objects.create(
            business=business,
            created_by=request.user,
            type='income',
            cost_type='non_cost',
            category='sales',
            amount=total_amount,
            description=f"Sale {invoice_number}",
            transaction_date=timezone.now().date()
        )
        
        # Update customer stats
        if customer:
            customer.total_spent = F('total_spent') + total_amount
            customer.total_visits = F('total_visits') + 1
            customer.save()
            customer.refresh_from_db()
        
        change_amount = float(amount_paid - total_amount) if amount_paid > total_amount else 0
        
        return Response({
            'message': 'Sale processed successfully',
            'sale': SaleSerializer(sale).data,
            'items': SaleItemSerializer(created_items, many=True).data,
            'change_amount': change_amount
        }, status=status.HTTP_201_CREATED)


class SaleReceiptView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewReceipt(), IsAuditorSalesReadOnly()]
    
    def get(self, request, pk):
        self.check_permissions(request)
        
        try:
            sale = Sale.objects.get(pk=pk, business=request.user.business)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found'}, status=404)
        
        items = sale.items.select_related('product').all()
        
        receipt_data = {
            'business': {
                'name': sale.business.name,
                'address': sale.business.address,
                'phone': sale.business.phone,
                'email': sale.business.email,
            },
            'sale': {
                'invoice_number': sale.invoice_number,
                'date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'cashier': sale.created_by.username if sale.created_by else 'N/A',
            },
            'customer': {
                'name': sale.customer.name if sale.customer else 'Walk-in Customer',
                'phone': sale.customer.phone if sale.customer else '',
            },
            'items': [
                {
                    'id': item.id,
                    'name': item.product.name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price)
                }
                for item in items
            ],
            'totals': {
                'subtotal': float(sale.subtotal),
                'discount': float(sale.discount_amount),
                'total': float(sale.total_amount),
                'amount_paid': float(sale.amount_paid),
                'change': float(sale.change_amount),
            },
            'payment_method': sale.get_payment_method_display(),
            'notes': sale.notes
        }
        
        return Response(receipt_data)


# ==================== RETURNS ====================
class ReturnListCreateView(generics.ListCreateAPIView):
    serializer_class = ReturnSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalesReports(), IsAuditorSalesReadOnly()]
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Return.objects.none()
        return Return.objects.filter(business=self.request.user.business)

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business,
            created_by=self.request.user
        )


class ReturnDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReturnSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated(), CanViewSalesReports(), IsAuditorSalesReadOnly()]
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]

    def get_queryset(self):
        return Return.objects.filter(business=self.request.user.business)


class ProcessReturnView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanProcessReturn(), IsAuditorSalesReadOnly()]

    @transaction.atomic
    def post(self, request):
        self.check_permissions(request)

        sale_id = request.data.get('sale_id')
        sale_item_id = request.data.get('sale_item_id')
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', 'customer_request')
        notes = request.data.get('notes', '')

        try:
            sale = Sale.objects.get(id=sale_id, business=request.user.business)
        except Sale.DoesNotExist:
            return Response({'error': 'Sale not found'}, status=404)

        if sale.status == 'refunded':
            return Response({'error': 'Sale already refunded'}, status=400)

        if sale_item_id:
            try:
                sale_item = SaleItem.objects.get(id=sale_item_id, sale=sale)
            except SaleItem.DoesNotExist:
                return Response({'error': 'Sale item not found'}, status=404)
        else:
            sale_item = sale.items.first()
            quantity = sale_item.quantity if sale_item else 0

        if not sale_item:
            return Response({'error': 'No items found for this sale'}, status=404)

        # Check for existing return to prevent duplicates
        existing_return = Return.objects.filter(
            sale_item=sale_item,
            sale=sale
        ).exists()
        
        if existing_return:
            return Response({
                'error': 'This item has already been returned'
            }, status=400)

        # Check remaining quantity that can be returned
        total_returned = Return.objects.filter(
            sale_item=sale_item
        ).aggregate(total=Sum('quantity_returned'))['total'] or 0
        
        available_for_return = sale_item.quantity - total_returned
        
        if quantity > available_for_return:
            return Response({
                'error': f'Only {available_for_return} units available for return'
            }, status=400)

        if quantity > sale_item.quantity:
            return Response({
                'error': 'Return quantity exceeds sold quantity'
            }, status=400)

        refund_amount = (sale_item.unit_price * quantity) - sale_item.discount_amount

        return_obj = Return.objects.create(
            business=request.user.business,
            sale=sale,
            sale_item=sale_item,
            reason=reason,
            quantity_returned=quantity,
            refund_amount=refund_amount,
            notes=notes,
            created_by=request.user
        )

        # Return stock to inventory
        from inventory.models import StockMovement

        product = sale_item.product
        product.quantity_on_hand += quantity
        product.total_investment = product.buying_price * product.quantity_on_hand
        product.save()

        StockMovement.objects.create(
            business=request.user.business,
            product=product,
            quantity=quantity,
            movement_type='RETURN_IN',
            unit_cost=product.buying_price,
            total_cost=product.buying_price * quantity,
            reference_id=sale.invoice_number,
            reference_type='return',
            notes=f"Return from sale {sale.invoice_number}",
            created_by=request.user
        )

        # Create financial transaction (refund/expense)
        Transaction.objects.create(
            business=request.user.business,
            created_by=request.user,
            type='expense',
            cost_type='non_cost',
            category='other',
            amount=refund_amount,
            description=f"Refund for {sale.invoice_number}",
            transaction_date=timezone.now().date()
        )

        # Update sale status if fully returned
        if sale_item.quantity == quantity and sale.items.count() == 1:
            sale.status = 'refunded'
            sale.save()

        return Response({
            'message': 'Return processed successfully',
            'return': ReturnSerializer(return_obj).data,
            'refund_amount': float(refund_amount)
        }, status=status.HTTP_201_CREATED)


# ==================== SALES REPORTS ====================
class DailySalesReportView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalesReports(), IsAuditorSalesReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        days = int(request.query_params.get('days', 7))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        sales = Sale.objects.filter(
            business=request.user.business,
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date,
            status='completed'
        ).prefetch_related('items')
        
        daily_data = []
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            day_sales = sales.filter(sale_date__date=date)
            
            total = day_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            count = day_sales.count()
            items = day_sales.aggregate(Sum('items__quantity'))['items__quantity__sum'] or 0
            customers = day_sales.values('customer').distinct().count()
            
            daily_data.append({
                'date': date.isoformat(),
                'total_sales': float(total),
                'transaction_count': count,
                'items_sold': items,
                'unique_customers': customers,
                'average_order': float(total / count) if count > 0 else 0
            })
        
        total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_transactions = sales.count()
        total_items = sales.aggregate(Sum('items__quantity'))['items__quantity__sum'] or 0
        total_customers = sales.values('customer').distinct().count()
        
        payment_breakdown = {}
        for method in Sale.PAYMENT_METHODS:
            method_sales = sales.filter(payment_method=method[0])
            amount = method_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            if amount > 0:
                payment_breakdown[method[1]] = float(amount)
        
        top_products = SaleItem.objects.filter(
            sale__business=request.user.business,
            sale__sale_date__date__gte=start_date
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity')[:10]
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days + 1
            },
            'summary': {
                'total_sales': float(total_sales),
                'total_transactions': total_transactions,
                'total_items_sold': total_items,
                'unique_customers': total_customers,
                'average_transaction': float(total_sales / total_transactions) if total_transactions > 0 else 0
            },
            'daily_breakdown': daily_data,
            'payment_breakdown': payment_breakdown,
            'top_products': list(top_products)
        })


class TodaySalesView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated(), CanViewSalesReports(), IsAuditorSalesReadOnly()]
    
    def get(self, request):
        self.check_permissions(request)
        
        today = timezone.now().date()
        
        sales = Sale.objects.filter(
            business=request.user.business,
            sale_date__date=today,
            status='completed'
        ).prefetch_related('items')
        
        total_sales = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_transactions = sales.count()
        total_items = sales.aggregate(Sum('items__quantity'))['items__quantity__sum'] or 0
        
        hourly = []
        for hour in range(24):
            hour_sales = sales.filter(sale_date__hour=hour)
            amount = hour_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            if amount > 0:
                hourly.append({
                    'hour': hour,
                    'amount': float(amount),
                    'transactions': hour_sales.count()
                })
        
        return Response({
            'date': today.isoformat(),
            'total_sales': float(total_sales),
            'total_transactions': total_transactions,
            'total_items': total_items,
            'average_order': float(total_sales / total_transactions) if total_transactions > 0 else 0,
            'hourly_breakdown': hourly
        })