# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q


class User(AbstractUser):
    """用户模型，扩展Django默认用户"""
    USER_TYPE_CHOICES = (
        ('admin', '管理员'),
        ('normal', '普通用户'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='normal', verbose_name='用户类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        db_table = 'user'


class Customer(models.Model):
    """客户模型"""
    name = models.CharField(max_length=100, verbose_name='客户名称')
    contact = models.CharField(max_length=50, verbose_name='联系方式')
    address = models.TextField(verbose_name='地址')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '客户'
        verbose_name_plural = '客户'
        db_table = 'customer'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """产品模型"""
    name = models.CharField(max_length=100, verbose_name='产品名称')
    specification = models.CharField(max_length=200, verbose_name='产品规格')
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='成本价'
    )
    current_stock = models.IntegerField(default=0, verbose_name='当前库存')
    sold_quantity = models.IntegerField(default=0, verbose_name='已售数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '产品'
        verbose_name_plural = '产品'
        db_table = 'product'
        unique_together = ['name', 'specification']  # 产品名称和规格的组合应该是唯一的
    
    def __str__(self):
        return f"{self.name} - {self.specification}"


class Batch(models.Model):
    """批次模型"""
    batch_number = models.CharField(max_length=50, unique=True, verbose_name='批次号')
    date = models.DateField(default=timezone.now, verbose_name='批次日期')
    total_profit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='批次总利润'
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '批次'
        verbose_name_plural = '批次'
        db_table = 'batch'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return self.batch_number
    
    def calculate_total_profit(self):
        """计算批次总利润 - 改进版本"""
        try:
            from django.db.models import Sum
            
            # 获取有效订单的利润总和
            total = self.orders.filter(
                status__in=['confirmed', 'shipping', 'completed']
            ).aggregate(total_profit=Sum('gross_profit'))['total_profit']
            
            # 处理None值并确保是Decimal类型
            if total is None:
                total = Decimal('0.00')
            else:
                total = Decimal(str(total))
            
            # 只有值发生变化时才保存
            if self.total_profit != total:
                self.total_profit = total
                self.save(update_fields=['total_profit'])
            
            return self.total_profit
            
        except Exception as e:
            print(f"批次{self.batch_number}利润计算失败: {e}")
            # 出错时设置为0但不抛出异常
            if self.total_profit != Decimal('0.00'):
                self.total_profit = Decimal('0.00')
                self.save(update_fields=['total_profit'])
            return self.total_profit


class Order(models.Model):
    """订单模型"""
    ORDER_STATUS_CHOICES = (
        ('pending', '待确认'),
        ('confirmed', '已确认'),
        ('shipping', '发货中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('refund_requested', '申请退款'),
        ('refunding', '正在退款'),
        ('refunded', '已退款'),
    )
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='orders', verbose_name='所属批次')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name='客户')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='产品')
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='数量')
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='单价'
    )
    sales_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name='销售额',
        help_text='数量 × 单价'
    )
    other_costs = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='其他成本',
        help_text='如运输费用等'
    )
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name='总成本',
        help_text='成本价 × 数量 + 其他成本'
    )
    gross_profit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name='毛利润',
        help_text='销售额 - 总成本'
    )
    status = models.CharField(
        max_length=20, 
        choices=ORDER_STATUS_CHOICES, 
        default='pending',
        verbose_name='订单状态'
    )
    remark = models.TextField(blank=True, verbose_name='备注', help_text='如为什么这个客户是这个价钱')
    order_date = models.DateField(default=timezone.now, verbose_name='订单日期')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        db_table = 'order'
        ordering = ['-order_date', '-created_at']
    
    def __str__(self):
        return f"{self.batch.batch_number} - {self.customer.name} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        """保存前自动计算销售额、总成本和毛利润"""
        try:
            # 确保所有字段都是正确的类型
            self.quantity = int(self.quantity or 0)
            self.unit_price = Decimal(str(self.unit_price or '0.00'))
            self.other_costs = Decimal(str(self.other_costs or '0.00'))
            
            # 获取产品成本价
            cost_price = Decimal(str(self.product.cost_price or '0.00'))
            
            # 计算销售额
            self.sales_amount = Decimal(str(self.quantity)) * self.unit_price
            
            # 计算总成本
            self.total_cost = (cost_price * Decimal(str(self.quantity))) + self.other_costs
            
            # 计算毛利润
            self.gross_profit = self.sales_amount - self.total_cost
            
            is_new = self.pk is None
            old_status = None
            old_quantity = 0
            
            if not is_new:
                # 获取保存前的状态
                try:
                    old_order = Order.objects.get(pk=self.pk)
                    old_status = old_order.status
                    old_quantity = old_order.quantity
                except Order.DoesNotExist:
                    is_new = True
            
            # 先保存订单
            super().save(*args, **kwargs)
            
            if is_new:
                # 新订单且状态为已确认，扣减库存
                if self.status in ['confirmed', 'shipping', 'completed']:
                    if self.product.current_stock >= self.quantity:
                        self.product.current_stock -= self.quantity
                        self.product.sold_quantity += self.quantity
                        self.product.save(update_fields=['current_stock', 'sold_quantity'])
                    else:
                        # 库存不足，改为待确认状态
                        self.status = 'pending'
                        super().save(update_fields=['status'])
            else:
                # 现有订单状态变更
                if old_status != self.status:
                    self._handle_status_change(old_status, old_quantity)
            
            # 确保批次利润重新计算
            if self.batch_id:
                try:
                    self.batch.calculate_total_profit()
                except Exception as e:
                    # 记录错误但不影响订单保存
                    print(f"批次利润计算失败: {e}")
                    
        except Exception as e:
            
            print(f"订单保存计算出错: {e}")
            # 设置默认值避免保存失败
            self.sales_amount = Decimal('0.00')
            self.total_cost = Decimal('0.00') 
            self.gross_profit = Decimal('0.00')
            super().save(*args, **kwargs)
                
        except Exception as e:
            # 如果出错，设置默认值
            self.sales_amount = Decimal('0.00')
            self.total_cost = Decimal('0.00') 
            self.gross_profit = Decimal('0.00')
            super().save(*args, **kwargs)

    def _handle_status_change(self, old_status, old_quantity):
        """处理订单状态变更的库存逻辑"""
        current_status = self.status
        
        # 从待确认到已确认：扣减库存
        if old_status == 'pending' and current_status in ['confirmed', 'shipping', 'completed']:
            if self.product.current_stock >= self.quantity:
                self.product.current_stock -= self.quantity
                self.product.sold_quantity += self.quantity
                self.product.save(update_fields=['current_stock', 'sold_quantity'])
            else:
                # 库存不足，保持待确认状态
                self.status = 'pending'
                super().save(update_fields=['status'])
        
        # 从已确认到取消/退款：恢复库存
        elif old_status in ['confirmed', 'shipping', 'completed'] and current_status in ['cancelled', 'refunded']:
            self.product.current_stock += old_quantity
            self.product.sold_quantity -= old_quantity
            self.product.save(update_fields=['current_stock', 'sold_quantity'])
        
        # 数量变更：调整库存差额
        elif (old_status in ['confirmed', 'shipping', 'completed'] and 
              current_status in ['confirmed', 'shipping', 'completed'] and 
              old_quantity != self.quantity):
            quantity_diff = self.quantity - old_quantity
            if self.product.current_stock >= quantity_diff:
                self.product.current_stock -= quantity_diff
                self.product.sold_quantity += quantity_diff
                self.product.save(update_fields=['current_stock', 'sold_quantity'])
            else:
                # 恢复旧数量
                self.quantity = old_quantity
                super().save(update_fields=['quantity'])


class StockRecord(models.Model):
    """库存记录（入库记录）"""
    OPERATION_CHOICES = (
        ('in', '入库'),
        ('out', '出库'),
        ('adjust', '调整'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_records', verbose_name='产品')
    operation_type = models.CharField(max_length=10, choices=OPERATION_CHOICES, verbose_name='操作类型')
    quantity = models.IntegerField(verbose_name='数量', help_text='正数表示增加，负数表示减少')
    before_stock = models.IntegerField(verbose_name='操作前库存')
    after_stock = models.IntegerField(verbose_name='操作后库存')
    remark = models.TextField(blank=True, verbose_name='备注')
    operated_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    operated_at = models.DateTimeField(default=timezone.now, verbose_name='操作时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '库存记录'
        verbose_name_plural = '库存记录'
        db_table = 'stock_record'
        ordering = ['-operated_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.get_operation_type_display()} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        """保存前记录库存变化 - 改进版本"""
        if not self.pk:  # 新记录
            # 记录操作前库存
            self.before_stock = self.product.current_stock
            
            # 计算操作后库存
            if self.operation_type == 'in':
                new_stock = self.product.current_stock + self.quantity
            elif self.operation_type == 'out':
                new_stock = max(0, self.product.current_stock - self.quantity)  # 不能为负
            elif self.operation_type == 'adjust':
                new_stock = self.quantity  # 调整操作，quantity就是新库存
            else:
                new_stock = self.product.current_stock
            
            self.after_stock = new_stock
            
            # 更新产品库存
            self.product.current_stock = new_stock
            self.product.save(update_fields=['current_stock'])
        
        super().save(*args, **kwargs)

# 添加信号处理器确保一致性
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def update_batch_profit_on_order_save(sender, instance, **kwargs):
    """订单保存后更新批次利润"""
    if instance.batch_id:
        # 异步或延迟执行避免递归
        try:
            instance.batch.calculate_total_profit()
        except Exception as e:
            print(f"信号处理器中批次利润计算失败: {e}")

@receiver(post_delete, sender=Order) 
def update_batch_profit_on_order_delete(sender, instance, **kwargs):
    """订单删除后更新批次利润"""
    if instance.batch_id:
        try:
            instance.batch.calculate_total_profit()
        except Exception as e:
            print(f"删除订单后批次利润计算失败: {e}")
