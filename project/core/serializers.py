# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db.models import Sum, Count, Q
from decimal import Decimal
from .models import User, Customer, Product, Batch, Order, StockRecord


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'user_type', 'is_active', 'date_joined', 'password', 'confirm_password']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate(self, attrs):
        # 如果提供了确认密码，验证两次密码是否一致
        if 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError("两次密码不一致")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('用户账号已被禁用')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('必须提供用户名和密码')


class CustomerListSerializer(serializers.ModelSerializer):
    """客户列表序列化器（包含统计信息）"""
    order_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact', 'address', 'order_count', 
                 'total_sales', 'created_at', 'updated_at']
    
    def get_order_count(self, obj):
        """获取订单数量"""
        return obj.order_set.count()
    
    def get_total_sales(self, obj):
        """获取总销售额"""
        total = obj.order_set.filter(
            status__in=['confirmed', 'shipping', 'completed']
        ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
        return str(total)


class CustomerDetailSerializer(serializers.ModelSerializer):
    """客户详情序列化器"""
    recent_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact', 'address', 'recent_orders',
                 'created_at', 'updated_at']
    
    def get_recent_orders(self, obj):
        """获取最近的订单"""
        recent_orders = obj.order_set.select_related('product', 'batch').order_by('-created_at')[:5]
        return [{
            'id': order.id,
            'batch_number': order.batch.batch_number,
            'product_name': order.product.name,
            'quantity': order.quantity,
            'sales_amount': str(order.sales_amount),
            'status': order.get_status_display(),
            'order_date': order.order_date
        } for order in recent_orders]


class CustomerSerializer(serializers.ModelSerializer):
    """客户基础序列化器"""
    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact', 'address', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """产品列表序列化器"""
    stock_status = serializers.SerializerMethodField()
    total_sold_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'specification', 'cost_price', 'current_stock', 
                 'sold_quantity', 'stock_status', 'total_sold_value', 'created_at']
    
    def get_stock_status(self, obj):
        """获取库存状态"""
        if obj.current_stock == 0:
            return 'out_of_stock'
        elif obj.current_stock < 10:
            return 'low_stock'
        else:
            return 'in_stock'
    
    def get_total_sold_value(self, obj):
        """获取总销售价值"""
        return str(obj.cost_price * obj.sold_quantity)


class ProductSerializer(serializers.ModelSerializer):
    """产品序列化器"""
    class Meta:
        model = Product
        fields = ['id', 'name', 'specification', 'cost_price', 'current_stock', 
                 'sold_quantity', 'created_at', 'updated_at']
        read_only_fields = ['sold_quantity']


class StockInSerializer(serializers.Serializer):
    """入库序列化器"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError('产品不存在')
        return value
    
    def create(self, validated_data):
        product = Product.objects.get(id=validated_data['product_id'])
        quantity = validated_data['quantity']
        remark = validated_data.get('remark', '')
        
        # 创建库存记录
        stock_record = StockRecord.objects.create(
            product=product,
            operation_type='in',
            quantity=quantity,
            remark=remark,
            operated_by=self.context['request'].user
        )
        return stock_record


class BatchListSerializer(serializers.ModelSerializer):
    """批次列表序列化器"""
    order_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    profit_margin = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Batch
        fields = ['id', 'batch_number', 'date', 'total_profit', 'order_count',
                 'total_sales', 'profit_margin', 'created_by_name', 'created_at']
    
    def get_order_count(self, obj):
        return obj.orders.count()
    
    def get_total_sales(self, obj):
        total = obj.orders.filter(
            status__in=['confirmed', 'shipping', 'completed']
        ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
        return str(total)
    
    def get_profit_margin(self, obj):
        total_sales = obj.orders.filter(
            status__in=['confirmed', 'shipping', 'completed']
        ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
        
        if total_sales > 0:
            return round(float(obj.total_profit / total_sales) * 100, 2)
        return 0


class BatchSerializer(serializers.ModelSerializer):
    """批次序列化器"""
    class Meta:
        model = Batch
        fields = ['id', 'batch_number', 'date', 'total_profit', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['total_profit', 'created_by']


class OrderListSerializer(serializers.ModelSerializer):
    """订单列表序列化器"""
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_specification = serializers.CharField(source='product.specification', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'batch_number', 'customer_name', 'product_name', 'product_specification',
                 'quantity', 'unit_price', 'sales_amount', 'total_cost', 'gross_profit',
                 'status', 'status_display', 'order_date', 'created_by_name', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    """订单详情序列化器"""
    batch_info = serializers.SerializerMethodField()
    customer_info = serializers.SerializerMethodField()
    product_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'batch_info', 'customer_info', 'product_info', 'quantity', 
                 'unit_price', 'sales_amount', 'other_costs', 'total_cost', 'gross_profit',
                 'status', 'remark', 'order_date', 'created_at', 'updated_at']
    
    def get_batch_info(self, obj):
        return {
            'id': obj.batch.id,
            'batch_number': obj.batch.batch_number,
            'date': obj.batch.date
        }
    
    def get_customer_info(self, obj):
        return {
            'id': obj.customer.id,
            'name': obj.customer.name,
            'contact': obj.customer.contact
        }
    
    def get_product_info(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'specification': obj.product.specification,
            'cost_price': str(obj.product.cost_price)
        }


class OrderCreateSerializer(serializers.ModelSerializer):
    """订单创建序列化器"""
    class Meta:
        model = Order
        fields = ['batch', 'customer', 'product', 'quantity', 'unit_price', 
                 'other_costs', 'status', 'remark', 'order_date']
    
    def validate(self, attrs):
        # 验证库存是否充足（只对确认状态及以后的订单验证）
        if attrs.get('status') in ['confirmed', 'shipping', 'completed']:
            product = attrs['product']
            quantity = attrs['quantity']
            if product.current_stock < quantity:
                raise serializers.ValidationError(f'库存不足，当前库存：{product.current_stock}')
        return attrs


class OrderUpdateSerializer(serializers.ModelSerializer):
    """订单更新序列化器"""
    class Meta:
        model = Order
        fields = ['quantity', 'unit_price', 'other_costs', 'status', 'remark', 'order_date']
    
    def validate(self, attrs):
        # 如果更新状态或数量，需要验证库存
        instance = self.instance
        new_status = attrs.get('status', instance.status)
        new_quantity = attrs.get('quantity', instance.quantity)
        
        # 如果从待确认变为已确认或者增加数量，需要检查库存
        if (instance.status == 'pending' and new_status in ['confirmed', 'shipping', 'completed']) or \
           (new_quantity > instance.quantity and new_status in ['confirmed', 'shipping', 'completed']):
            
            quantity_diff = new_quantity - (instance.quantity if instance.status != 'pending' else 0)
            if instance.product.current_stock < quantity_diff:
                raise serializers.ValidationError(f'库存不足，当前库存：{instance.product.current_stock}')
        
        return attrs


class BatchOrderCreateSerializer(serializers.Serializer):
    """批量创建订单序列化器"""
    batch_id = serializers.IntegerField()
    orders = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=100
    )
    
    def validate_batch_id(self, value):
        try:
            batch = Batch.objects.get(id=value)
        except Batch.DoesNotExist:
            raise serializers.ValidationError('批次不存在')
        return value
    
    def validate_orders(self, value):
        validated_orders = []
        for order_data in value:
            # 验证必需字段
            required_fields = ['customer_id', 'product_id', 'quantity', 'unit_price']
            for field in required_fields:
                if field not in order_data:
                    raise serializers.ValidationError(f'订单数据缺少必需字段: {field}')
            
            # 验证客户和产品是否存在
            try:
                customer = Customer.objects.get(id=order_data['customer_id'])
                product = Product.objects.get(id=order_data['product_id'])
            except (Customer.DoesNotExist, Product.DoesNotExist):
                raise serializers.ValidationError('客户或产品不存在')
            
            # 验证数量和价格
            if order_data['quantity'] <= 0:
                raise serializers.ValidationError('数量必须大于0')
            if order_data['unit_price'] < 0:
                raise serializers.ValidationError('单价不能为负数')
            
            validated_orders.append(order_data)
        
        return validated_orders


class StockRecordSerializer(serializers.ModelSerializer):
    """库存记录序列化器"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    operated_by_name = serializers.CharField(source='operated_by.username', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    
    class Meta:
        model = StockRecord
        fields = ['id', 'product_name', 'operation_type', 'operation_type_display',
                 'quantity', 'before_stock', 'after_stock', 'remark', 
                 'operated_by_name', 'operated_at', 'created_at']


class StockRecordCreateSerializer(serializers.ModelSerializer):
    """库存记录创建序列化器"""
    class Meta:
        model = StockRecord
        fields = ['product', 'operation_type', 'quantity', 'after_stock', 'remark']
        
    def validate(self, attrs):
        operation_type = attrs['operation_type']
        quantity = attrs['quantity']
        
        if operation_type == 'adjust':
            if 'after_stock' not in attrs:
                raise serializers.ValidationError('调整操作必须提供调整后库存数量')
            if attrs['after_stock'] < 0:
                raise serializers.ValidationError('调整后库存不能为负数')
        else:
            if operation_type == 'out' and quantity > attrs['product'].current_stock:
                raise serializers.ValidationError('出库数量不能超过当前库存')
            if quantity <= 0:
                raise serializers.ValidationError('数量必须大于0')
        
        return attrs


# 报表相关序列化器
class ProductSalesStatsSerializer(serializers.Serializer):
    """产品销售统计序列化器"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    product_specification = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CustomerSalesStatsSerializer(serializers.Serializer):
    """客户销售统计序列化器"""
    customer_id = serializers.IntegerField()
    customer_name = serializers.CharField()
    order_count = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)


class DailySalesStatsSerializer(serializers.Serializer):
    """每日销售统计序列化器"""
    date = serializers.DateField()
    order_count = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)