# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.db.models import Sum, Count, Q, Avg, F
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import User, Customer, Product, Batch, Order, StockRecord
from .serializers import (
    UserSerializer, LoginSerializer, CustomerSerializer, CustomerListSerializer, 
    CustomerDetailSerializer, ProductSerializer, ProductListSerializer, StockInSerializer,
    BatchSerializer, BatchListSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    OrderListSerializer, OrderDetailSerializer, BatchOrderCreateSerializer,
    StockRecordSerializer, StockRecordCreateSerializer,
    ProductSalesStatsSerializer, CustomerSalesStatsSerializer, DailySalesStatsSerializer
)
from .permissions import (
    IsAdminOrReadOnly, IsAdminOrOwner, IsAdminUserOnly, 
    IsOwnerOrAdmin, CanManageStock
)


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页配置"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# 认证相关视图
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """用户登录"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout(request):
    """用户登出"""
    try:
        request.user.auth_token.delete()
        return Response({'message': '登出成功'})
    except:
        return Response({'message': '登出失败'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def profile(request):
    """获取当前用户信息"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# 用户管理视图集
class UserViewSet(viewsets.ModelViewSet):
    """用户管理视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUserOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user_type', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        # 普通用户只能看到自己的信息
        if self.request.user.user_type != 'admin' and not self.request.user.is_superuser:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.all()
    
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        """重置用户密码"""
        user = self.get_object()
        password = request.data.get('password')
        if not password or len(password) < 8:
            return Response({'error': '密码长度至少8位'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        return Response({'message': '密码重置成功'})
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换用户激活状态"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({
            'message': f'用户已{"激活" if user.is_active else "禁用"}',
            'is_active': user.is_active
        })


# 客户管理视图集
class CustomerViewSet(viewsets.ModelViewSet):
    """客户管理视图集"""
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """获取客户的所有订单"""
        customer = self.get_object()
        orders = customer.order_set.select_related('batch', 'product').order_by('-created_at')
        
        # 分页
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """获取客户销售统计"""
        customer = self.get_object()
        
        # 有效订单（已确认及以后状态）
        valid_orders = customer.order_set.filter(
            status__in=['confirmed', 'shipping', 'completed']
        )
        
        stats = valid_orders.aggregate(
            total_orders=Count('id'),
            total_sales=Sum('sales_amount'),
            total_profit=Sum('gross_profit'),
            avg_order_value=Avg('sales_amount')
        )
        
        # 处理None值
        for key, value in stats.items():
            if value is None:
                stats[key] = 0
        
        # 最近订单时间
        last_order = valid_orders.order_by('-order_date').first()
        stats['last_order_date'] = last_order.order_date if last_order else None
        
        return Response(stats)


# 产品管理视图集
class ProductViewSet(viewsets.ModelViewSet):
    """产品管理视图集"""
    queryset = Product.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['specification']
    search_fields = ['name', 'specification']
    ordering_fields = ['name', 'current_stock', 'sold_quantity', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """获取库存偏低的产品"""
        threshold = int(request.query_params.get('threshold', 10))
        products = Product.objects.filter(current_stock__lte=threshold).order_by('current_stock')
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def stock_in(self, request, pk=None):
        """产品入库"""
        product = self.get_object()
        serializer = StockInSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # 添加产品ID到数据中
            validated_data = serializer.validated_data
            validated_data['product_id'] = product.id
            
            stock_record = serializer.save()
            return Response({
                'message': '入库成功',
                'stock_record_id': stock_record.id,
                'current_stock': product.current_stock
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def stock_records(self, request, pk=None):
        """获取产品库存记录"""
        product = self.get_object()
        records = product.stock_records.order_by('-operated_at')
        
        page = self.paginate_queryset(records)
        if page is not None:
            serializer = StockRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StockRecordSerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def sales_stats(self, request, pk=None):
        """获取产品销售统计"""
        product = self.get_object()
        
        # 有效订单
        valid_orders = product.order_set.filter(
            status__in=['confirmed', 'shipping', 'completed']
        )
        
        stats = valid_orders.aggregate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('sales_amount'),
            total_profit=Sum('gross_profit'),
            avg_unit_price=Avg('unit_price'),
            order_count=Count('id')
        )
        
        # 处理None值
        for key, value in stats.items():
            if value is None:
                stats[key] = 0
        
        # 计算利润率
        if stats['total_sales'] > 0:
            stats['profit_margin'] = round(float(stats['total_profit'] / stats['total_sales']) * 100, 2)
        else:
            stats['profit_margin'] = 0
        
        return Response(stats)


# 批次管理视图集
class BatchViewSet(viewsets.ModelViewSet):
    """批次管理视图集"""
    queryset = Batch.objects.all()
    permission_classes = [IsAdminOrOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['batch_number']
    ordering_fields = ['date', 'total_profit', 'created_at']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        queryset = Batch.objects.select_related('created_by')
        
        # 普通用户只能看到自己创建的批次
        if self.request.user.user_type != 'admin' and not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BatchListSerializer
        return BatchSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """获取批次的所有订单"""
        batch = self.get_object()
        orders = batch.orders.select_related('customer', 'product').order_by('-created_at')
        
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_orders(self, request, pk=None):
        """批量添加订单到批次"""
        batch = self.get_object()
        
        # 将批次ID添加到请求数据中
        data = request.data.copy()
        data['batch_id'] = batch.id
        
        serializer = BatchOrderCreateSerializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                created_orders = []
                
                for order_data in serializer.validated_data['orders']:
                    order = Order.objects.create(
                        batch=batch,
                        customer_id=order_data['customer_id'],
                        product_id=order_data['product_id'],
                        quantity=order_data['quantity'],
                        unit_price=Decimal(str(order_data['unit_price'])),
                        other_costs=Decimal(str(order_data.get('other_costs', 0))),
                        status=order_data.get('status', 'pending'),
                        remark=order_data.get('remark', ''),
                        order_date=order_data.get('order_date', timezone.now().date()),
                        created_by=request.user
                    )
                    created_orders.append(order)
                
                return Response({
                    'message': f'成功创建{len(created_orders)}个订单',
                    'order_ids': [order.id for order in created_orders]
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def recalculate_profit(self, request, pk=None):
        """重新计算批次利润"""
        batch = self.get_object()
        total_profit = batch.calculate_total_profit()
        
        return Response({
            'message': '利润重新计算完成',
            'total_profit': str(total_profit)
        })
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """获取批次汇总信息"""
        batch = self.get_object()
        
        # 订单统计
        orders_stats = batch.orders.aggregate(
            total_orders=Count('id'),
            confirmed_orders=Count('id', filter=Q(status__in=['confirmed', 'shipping', 'completed'])),
            pending_orders=Count('id', filter=Q(status='pending')),
            cancelled_orders=Count('id', filter=Q(status='cancelled')),
            total_sales=Sum('sales_amount', filter=Q(status__in=['confirmed', 'shipping', 'completed'])),
            total_cost=Sum('total_cost', filter=Q(status__in=['confirmed', 'shipping', 'completed']))
        )
        
        # 处理None值
        for key, value in orders_stats.items():
            if value is None:
                orders_stats[key] = 0
        
        # 计算利润率
        profit_margin = 0
        if orders_stats['total_sales'] > 0:
            profit_margin = round(float(batch.total_profit / orders_stats['total_sales']) * 100, 2)
        
        return Response({
            'batch_info': BatchSerializer(batch).data,
            'orders_stats': orders_stats,
            'profit_margin': profit_margin
        })


# 订单管理视图集
class OrderViewSet(viewsets.ModelViewSet):
    """订单管理视图集"""
    queryset = Order.objects.select_related('batch', 'customer', 'product', 'created_by')
    permission_classes = [IsAdminOrOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'batch', 'customer', 'product']
    search_fields = ['batch__batch_number', 'customer__name', 'product__name', 'remark']
    ordering_fields = ['order_date', 'sales_amount', 'gross_profit', 'created_at']
    ordering = ['-order_date', '-created_at']
    
    def get_queryset(self):
        queryset = Order.objects.select_related('batch', 'customer', 'product', 'created_by')
        
        # 普通用户只能看到自己创建的订单
        if self.request.user.user_type != 'admin' and not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        else:
            return OrderUpdateSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新订单状态"""
        order = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': '必须提供新状态'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in [choice[0] for choice in Order.ORDER_STATUS_CHOICES]:
            return Response({'error': '无效的状态'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = order.status
        
        # 状态变更的业务逻辑
        with transaction.atomic():
            # 如果从待确认变为已确认，需要检查并扣减库存
            if old_status == 'pending' and new_status in ['confirmed', 'shipping', 'completed']:
                if order.product.current_stock < order.quantity:
                    return Response({
                        'error': f'库存不足，当前库存：{order.product.current_stock}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                order.product.current_stock -= order.quantity
                order.product.sold_quantity += order.quantity
                order.product.save(update_fields=['current_stock', 'sold_quantity'])
            
            # 如果从已确认变为取消或退款，需要恢复库存
            elif old_status in ['confirmed', 'shipping', 'completed'] and new_status in ['cancelled', 'refunded']:
                order.product.current_stock += order.quantity
                order.product.sold_quantity -= order.quantity
                order.product.save(update_fields=['current_stock', 'sold_quantity'])
            
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
            
            # 重新计算批次利润
            order.batch.calculate_total_profit()
        
        return Response({
            'message': f'订单状态已从"{order.get_status_display()}"更新为"{order.get_status_display()}"',
            'status': new_status
        })
    
    @action(detail=False, methods=['post'])
    def batch_update_status(self, request):
        """批量更新订单状态"""
        order_ids = request.data.get('order_ids', [])
        new_status = request.data.get('status')
        
        if not order_ids or not new_status:
            return Response({'error': '必须提供订单ID列表和新状态'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in [choice[0] for choice in Order.ORDER_STATUS_CHOICES]:
            return Response({'error': '无效的状态'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取用户可操作的订单
        queryset = self.get_queryset().filter(id__in=order_ids)
        
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for order in queryset:
                try:
                    old_status = order.status
                    
                    # 状态变更的业务逻辑（简化版，实际可能需要更复杂的逻辑）
                    if old_status == 'pending' and new_status in ['confirmed', 'shipping', 'completed']:
                        if order.product.current_stock < order.quantity:
                            errors.append(f'订单{order.id}库存不足')
                            continue
                        
                        order.product.current_stock -= order.quantity
                        order.product.sold_quantity += order.quantity
                        order.product.save(update_fields=['current_stock', 'sold_quantity'])
                    
                    order.status = new_status
                    order.save(update_fields=['status', 'updated_at'])
                    order.batch.calculate_total_profit()
                    updated_count += 1
                    
                except Exception as e:
                    errors.append(f'订单{order.id}更新失败: {str(e)}')
        
        response_data = {
            'message': f'成功更新{updated_count}个订单',
            'updated_count': updated_count
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data)


# 库存记录视图集
class StockRecordViewSet(viewsets.ModelViewSet):
    """库存记录视图集"""
    queryset = StockRecord.objects.select_related('product', 'operated_by')
    permission_classes = [CanManageStock]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['operation_type', 'product']
    search_fields = ['product__name', 'remark']
    ordering_fields = ['operated_at', 'created_at']
    ordering = ['-operated_at']
    http_method_names = ['get', 'post']  # 只允许查看和创建，不允许修改删除
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StockRecordCreateSerializer
        return StockRecordSerializer
    
    def perform_create(self, serializer):
        serializer.save(operated_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取库存操作汇总"""
        # 今日操作统计
        today = timezone.now().date()
        today_records = StockRecord.objects.filter(operated_at__date=today)
        
        today_stats = today_records.aggregate(
            total_operations=Count('id'),
            in_operations=Count('id', filter=Q(operation_type='in')),
            out_operations=Count('id', filter=Q(operation_type='out')),
            adjust_operations=Count('id', filter=Q(operation_type='adjust'))
        )
        
        # 近7天统计
        week_ago = today - timedelta(days=7)
        week_records = StockRecord.objects.filter(operated_at__date__gte=week_ago)
        
        week_stats = week_records.aggregate(
            total_operations=Count('id'),
            in_operations=Count('id', filter=Q(operation_type='in')),
            out_operations=Count('id', filter=Q(operation_type='out')),
            adjust_operations=Count('id', filter=Q(operation_type='adjust'))
        )
        
        return Response({
            'today': today_stats,
            'this_week': week_stats
        })


# 报表API
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def product_sales_stats(request):
    """产品销售统计报表"""
    # 查询参数
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # 构建查询
    orders = Order.objects.filter(status__in=['confirmed', 'shipping', 'completed'])
    
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)
    
    # 按产品分组统计
    stats = orders.values(
        'product__id', 'product__name', 'product__specification'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('sales_amount'),
        total_profit=Sum('gross_profit'),
        avg_unit_price=Avg('unit_price')
    ).order_by('-total_sales')
    
    serializer = ProductSalesStatsSerializer(stats, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def customer_sales_stats(request):
    """客户销售统计报表"""
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    orders = Order.objects.filter(status__in=['confirmed', 'shipping', 'completed'])
    
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)
    
    stats = orders.values(
        'customer__id', 'customer__name'
    ).annotate(
        order_count=Count('id'),
        total_sales=Sum('sales_amount'),
        total_profit=Sum('gross_profit')
    ).order_by('-total_sales')
    
    serializer = CustomerSalesStatsSerializer(stats, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def daily_sales_stats(request):
    """每日销售统计报表"""
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    orders = Order.objects.filter(status__in=['confirmed', 'shipping', 'completed'])
    
    if start_date:
        orders = orders.filter(order_date__gte=start_date)
    if end_date:
        orders = orders.filter(order_date__lte=end_date)
    else:
        # 默认查询最近30天
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        orders = orders.filter(order_date__gte=start_date, order_date__lte=end_date)
    
    stats = orders.values('order_date').annotate(
        order_count=Count('id'),
        total_sales=Sum('sales_amount'),
        total_profit=Sum('gross_profit')
    ).order_by('order_date')
    
    serializer = DailySalesStatsSerializer(stats, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """仪表盘统计数据"""
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    
    # 今日统计
    today_orders = Order.objects.filter(
        order_date=today,
        status__in=['confirmed', 'shipping', 'completed']
    )
    
    today_stats = today_orders.aggregate(
        order_count=Count('id'),
        total_sales=Sum('sales_amount'),
        total_profit=Sum('gross_profit')
    )
    
    # 本月统计
    month_orders = Order.objects.filter(
        order_date__gte=this_month_start,
        status__in=['confirmed', 'shipping', 'completed']
    )
    
    month_stats = month_orders.aggregate(
        order_count=Count('id'),
        total_sales=Sum('sales_amount'),
        total_profit=Sum('gross_profit')
    )
    
    # 库存统计
    stock_stats = {
        'total_products': Product.objects.count(),
        'low_stock_products': Product.objects.filter(current_stock__lte=10).count(),
        'out_of_stock_products': Product.objects.filter(current_stock=0).count(),
        'total_stock_value': Product.objects.aggregate(
            value=Sum(F('current_stock') * F('cost_price'))
        )['value'] or 0
    }
    
    # 客户统计
    customer_stats = {
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(
            order__order_date__gte=this_month_start,
            order__status__in=['confirmed', 'shipping', 'completed']
        ).distinct().count()
    }
    
    # 处理None值
    for stat_dict in [today_stats, month_stats]:
        for key, value in stat_dict.items():
            if value is None:
                stat_dict[key] = 0
    
    return Response({
        'today': today_stats,
        'this_month': month_stats,
        'stock': stock_stats,
        'customer': customer_stats
    })