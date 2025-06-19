# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from decimal import Decimal
from .models import User, Customer, Product, Batch, Order, StockRecord


class CustomUserAdmin(UserAdmin):
    """自定义用户管理"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # 添加用户类型到添加和编辑表单
    fieldsets = UserAdmin.fieldsets + (
        ('用户类型', {'fields': ('user_type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('用户类型', {'fields': ('user_type',)}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # 普通用户只能看到自己的信息
        if not request.user.is_superuser and request.user.user_type != 'admin':
            return qs.filter(id=request.user.id)
        return qs
    
    def has_add_permission(self, request):
        # 只有管理员可以添加用户
        return request.user.is_superuser or request.user.user_type == 'admin'
    
    def has_delete_permission(self, request, obj=None):
        # 只有管理员可以删除用户
        return request.user.is_superuser or request.user.user_type == 'admin'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """客户管理"""
    list_display = ['name', 'contact', 'address', 'order_count', 'total_sales', 'created_at']
    search_fields = ['name', 'contact', 'address']
    list_filter = ['created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def order_count(self, obj):
        """订单数量"""
        return obj.order_set.count()
    order_count.short_description = '订单数量'
    
    def total_sales(self, obj):
        """总销售额"""
        try:
            total = obj.order_set.filter(
                status__in=['confirmed', 'shipping', 'completed']
            ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
            return f'¥{float(total):,.2f}'
        except (ValueError, TypeError):
            return '¥0.00'
    total_sales.short_description = '总销售额'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """产品管理"""
    list_display = ['name', 'specification', 'cost_price_display', 'current_stock_display', 
                    'sold_quantity', 'stock_status', 'created_at']
    search_fields = ['name', 'specification']
    list_filter = ['created_at', 'specification']
    ordering = ['name', 'specification']
    readonly_fields = ['sold_quantity', 'created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'specification', 'cost_price')
        }),
        ('库存信息', {
            'fields': ('current_stock', 'sold_quantity'),
            'description': '已售数量为只读字段，会根据订单自动更新'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def cost_price_display(self, obj):
        try:
            return f'¥{float(obj.cost_price):,.2f}'
        except (ValueError, TypeError):
            return '¥0.00'
    cost_price_display.short_description = '成本价'
    
    def current_stock_display(self, obj):
        try:
            stock = int(obj.current_stock or 0)
            return format_html(
                '<span style="color: {};">{}</span>',
                'red' if stock < 10 else 'green',
                stock
            )
        except (ValueError, TypeError):
            return '0'
    current_stock_display.short_description = '当前库存'
    
    def stock_status(self, obj):
        try:
            stock = int(obj.current_stock or 0)
            if stock == 0:
                return format_html('<span style="color: red;">缺货</span>')
            elif stock < 10:
                return format_html('<span style="color: orange;">库存偏低</span>')
            else:
                return format_html('<span style="color: green;">库存充足</span>')
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">未知</span>')
    stock_status.short_description = '库存状态'


class OrderInline(admin.TabularInline):
    """订单内联编辑"""
    model = Order
    extra = 1
    fields = ['customer', 'product', 'quantity', 'unit_price', 'other_costs', 
              'status', 'remark']
    readonly_fields = ['sales_amount', 'total_cost', 'gross_profit']
    autocomplete_fields = ['customer', 'product']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'product')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    """批次管理"""
    list_display = ['batch_number', 'date', 'order_count', 'total_sales_display', 
                    'total_profit_display', 'profit_margin', 'created_by', 'created_at']
    search_fields = ['batch_number']
    list_filter = ['date', 'created_by', 'created_at']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    readonly_fields = ['total_profit', 'created_by', 'created_at', 'updated_at']
    inlines = [OrderInline]
    
    fieldsets = (
        ('批次信息', {
            'fields': ('batch_number', 'date')
        }),
        ('财务信息', {
            'fields': ('total_profit',),
            'description': '批次总利润会根据订单自动计算'
        }),
        ('系统信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建批次时
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def order_count(self, obj):
        """订单数量"""
        return obj.orders.count()
    order_count.short_description = '订单数'
    
    def total_sales_display(self, obj):
        """总销售额"""
        try:
            total = obj.orders.filter(
                status__in=['confirmed', 'shipping', 'completed']
            ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
            return f'¥{float(total):,.2f}'
        except (ValueError, TypeError):
            return '¥0.00'
    total_sales_display.short_description = '总销售额'
    
    def total_profit_display(self, obj):
        """总利润显示"""
        try:
            profit = obj.total_profit or Decimal('0')
            profit_float = float(profit)
            color = 'green' if profit_float > 0 else 'red' if profit_float < 0 else 'black'
            return format_html(
                '<span style="color: {};">¥{}</span>',
                color,
                f'{profit_float:,.2f}'
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: red;">数据错误</span>')
    total_profit_display.short_description = '总利润'
    
    def profit_margin(self, obj):
        """利润率"""
        try:
            total_sales = obj.orders.filter(
                status__in=['confirmed', 'shipping', 'completed']
            ).aggregate(total=Sum('sales_amount'))['total'] or Decimal('0')
            
            profit = obj.total_profit or Decimal('0')
            
            if total_sales > 0 and profit is not None:
                margin = float((profit / total_sales) * 100)
                color = 'green' if margin > 20 else 'orange' if margin > 10 else 'red'
                return format_html(
                    '<span style="color: {};">{}</span>',
                    color,
                    f'{margin:.1f}%'
                )
            return '-'
        except (ValueError, TypeError, ZeroDivisionError):
            return format_html('<span style="color: red;">计算错误</span>')
    profit_margin.short_description = '利润率'
    
    def recalculate_profit(self, request, queryset):
        """重新计算批次利润"""
        for batch in queryset:
            batch.calculate_total_profit()
        self.message_user(request, f'成功重新计算 {queryset.count()} 个批次的利润')
    recalculate_profit.short_description = '重新计算选中批次的利润'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """订单管理"""
    list_display = [
        'order_number', 
        'batch_link',
        'customer_link', 
        'product_link', 
        'quantity',
        'unit_price_display', 
        'sales_amount_display',
        'gross_profit_display',
        'status_display', 
        'order_date',
        'created_by'
    ]
    search_fields = ['batch__batch_number', 'customer__name', 'product__name', 'remark']
    list_filter = ['status', 'batch', 'customer', 'order_date', 'created_by', 'product']
    date_hierarchy = 'order_date'
    ordering = ['-order_date', '-created_at']
    readonly_fields = ['sales_amount', 'total_cost', 'gross_profit', 'created_by', 
                       'created_at', 'updated_at']
    autocomplete_fields = ['customer', 'product', 'batch']
    
    fieldsets = (
        ('订单信息', {
            'fields': ('batch', 'customer', 'order_date', 'status')
        }),
        ('产品信息', {
            'fields': ('product', 'quantity', 'unit_price')
        }),
        ('成本信息', {
            'fields': ('other_costs', 'remark'),
            'description': '其他成本如运输费用等'
        }),
        ('财务汇总', {
            'fields': ('sales_amount', 'total_cost', 'gross_profit'),
            'description': '以下金额会自动计算',
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建订单时
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def order_number(self, obj):
        """订单编号"""
        return f'#{obj.id:06d}'
    order_number.short_description = '订单号'
    
    def batch_link(self, obj):
        """批次链接"""
        if obj.batch:
            try:
                url = reverse('admin:core_batch_change', args=[obj.batch.pk])
                return format_html('<a href="{}">{}</a>', url, obj.batch.batch_number)
            except Exception:
                return str(obj.batch.batch_number)
        return '-'
    batch_link.short_description = '批次'
    
    def customer_link(self, obj):
        """客户链接"""
        if obj.customer:
            try:
                url = reverse('admin:core_customer_change', args=[obj.customer.pk])
                return format_html('<a href="{}">{}</a>', url, obj.customer.name)
            except Exception:
                return str(obj.customer.name)
        return '-'
    customer_link.short_description = '客户'
    
    def product_link(self, obj):
        """产品链接"""
        if obj.product:
            try:
                url = reverse('admin:core_product_change', args=[obj.product.pk])
                return format_html('<a href="{}">{}</a>', url, f"{obj.product.name} - {obj.product.specification}")
            except Exception:
                return f"{obj.product.name} - {obj.product.specification}"
        return '-'
    product_link.short_description = '产品'
    
    def unit_price_display(self, obj):
        try:
            return f'¥{float(obj.unit_price):,.2f}'
        except (ValueError, TypeError):
            return '¥0.00'
    unit_price_display.short_description = '单价'
    
    def sales_amount_display(self, obj):
        try:
            return f'¥{float(obj.sales_amount):,.2f}'
        except (ValueError, TypeError):
            return '¥0.00'
    sales_amount_display.short_description = '销售额'
    
    def gross_profit_display(self, obj):
        """毛利润显示"""
        try:
            profit = obj.gross_profit or Decimal('0')
            profit_float = float(profit)
            color = 'green' if profit_float > 0 else 'red' if profit_float < 0 else 'black'
            return format_html(
                '<span style="color: {};">¥{}</span>',
                color,
                f'{profit_float:,.2f}'
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: red;">数据错误</span>')
    gross_profit_display.short_description = '毛利润'
    
    def status_display(self, obj):
        """状态显示"""
        status_colors = {
            'pending': 'gray',
            'confirmed': 'blue',
            'shipping': 'orange',
            'completed': 'green',
            'cancelled': 'red',
            'refund_requested': 'purple',
            'refunding': 'purple',
            'refunded': 'darkred',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = '状态'
    
    actions = ['confirm_orders', 'cancel_orders', 'mark_as_completed']
    
    def confirm_orders(self, request, queryset):
        """确认订单"""
        updated = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'成功确认 {updated} 个订单')
    confirm_orders.short_description = '确认选中的待确认订单'
    
    def cancel_orders(self, request, queryset):
        """取消订单"""
        updated = queryset.filter(status__in=['pending', 'confirmed']).update(status='cancelled')
        self.message_user(request, f'成功取消 {updated} 个订单')
    cancel_orders.short_description = '取消选中的订单'
    
    def mark_as_completed(self, request, queryset):
        """标记为已完成"""
        updated = queryset.filter(status='shipping').update(status='completed')
        self.message_user(request, f'成功完成 {updated} 个订单')
    mark_as_completed.short_description = '标记为已完成'


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    """库存记录管理"""
    list_display = ['product', 'operation_type_display', 'quantity_display', 
                    'stock_change', 'operated_by', 'operated_at', 'remark']
    search_fields = ['product__name', 'remark', 'operated_by__username']
    list_filter = ['operation_type', 'operated_at', 'operated_by']
    date_hierarchy = 'operated_at'
    ordering = ['-operated_at']
    readonly_fields = ['before_stock', 'after_stock', 'operated_by', 'created_at']
    autocomplete_fields = ['product']
    
    fieldsets = (
        ('操作信息', {
            'fields': ('product', 'operation_type', 'quantity', 'remark')
        }),
        ('库存变化', {
            'fields': ('before_stock', 'after_stock'),
            'description': '系统自动记录'
        }),
        ('系统信息', {
            'fields': ('operated_by', 'operated_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建记录时
            obj.operated_by = request.user
        super().save_model(request, obj, form, change)
    
    def operation_type_display(self, obj):
        """操作类型显示"""
        type_colors = {
            'in': 'green',
            'out': 'red',
            'adjust': 'blue',
        }
        color = type_colors.get(obj.operation_type, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_operation_type_display()
        )
    operation_type_display.short_description = '操作类型'
    
    def quantity_display(self, obj):
        """数量显示"""
        try:
            quantity = int(obj.quantity or 0)
            if obj.operation_type == 'in':
                return format_html('<span style="color: green;">+{}</span>', quantity)
            elif obj.operation_type == 'out':
                return format_html('<span style="color: red;">-{}</span>', quantity)
            else:
                return quantity
        except (ValueError, TypeError):
            return '0'
    quantity_display.short_description = '数量'
    
    def stock_change(self, obj):
        """库存变化"""
        try:
            before = int(obj.before_stock or 0)
            after = int(obj.after_stock or 0)
            return format_html(
                '{} → <strong>{}</strong>',
                before,
                after
            )
        except (ValueError, TypeError):
            return '0 → 0'
    stock_change.short_description = '库存变化'
    
    def has_delete_permission(self, request, obj=None):
        # 库存记录不允许删除
        return False


# 注册模型到admin
# 因为我们使用了自定义User模型，不需要先注销
admin.site.register(User, CustomUserAdmin)

# 自定义admin站点标题
admin.site.site_header = '销售管理系统'
admin.site.site_title = '销售管理系统'
admin.site.index_title = '欢迎使用销售管理系统'