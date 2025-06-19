# core/management/commands/create_test_data.py
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from core.models import Customer, Product, Batch, Order, StockRecord

User = get_user_model()


class Command(BaseCommand):
    help = '创建测试数据，用于开发和演示'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有数据后重新创建',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=3,
            help='创建用户数量 (默认: 3)',
        )
        parser.add_argument(
            '--customers',
            type=int,
            default=6,
            help='创建客户数量 (默认: 6)',
        )
        parser.add_argument(
            '--products',
            type=int,
            default=10,
            help='创建产品数量 (默认: 10)',
        )
        parser.add_argument(
            '--batches',
            type=int,
            default=5,
            help='创建批次数量 (默认: 5)',
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=20,
            help='创建订单数量 (默认: 20)',
        )

    def handle(self, *args, **options):
        """主执行方法"""
        self.stdout.write(
            self.style.SUCCESS('开始创建测试数据...')
        )

        # 如果指定清除数据
        if options['clear']:
            self.clear_data()

        try:
            with transaction.atomic():
                # 按顺序创建数据
                users = self.create_users(options['users'])
                customers = self.create_customers(options['customers'])
                products = self.create_products(options['products'])
                self.create_stock_records(products, users)
                batches = self.create_batches(options['batches'], users)
                self.create_orders(options['orders'], batches, customers, products, users)

            self.stdout.write(
                self.style.SUCCESS('✅ 测试数据创建完成！')
            )
            self.print_summary()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 创建测试数据失败: {str(e)}')
            )
            raise

    def clear_data(self):
        """清除现有数据"""
        self.stdout.write('🗑️  清除现有数据...')
        
        # 按依赖关系倒序删除
        Order.objects.all().delete()
        StockRecord.objects.all().delete()
        Batch.objects.all().delete()
        Product.objects.all().delete()
        Customer.objects.all().delete()
        # 保留超级用户，只删除测试创建的用户
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(
            self.style.WARNING('已清除现有测试数据')
        )

    def create_users(self, count):
        """创建用户"""
        self.stdout.write(f'👥 创建 {count} 个用户...')
        
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': 'admin123456',
                'first_name': '管理员',
                'last_name': '用户',
                'user_type': 'admin',
                'is_superuser': False,
                'is_staff': True,
            },
            {
                'username': 'user1',
                'email': 'user1@example.com', 
                'password': 'user123456',
                'first_name': '张',
                'last_name': '三',
                'user_type': 'normal',
            },
            {
                'username': 'user2',
                'email': 'user2@example.com',
                'password': 'user123456', 
                'first_name': '李',
                'last_name': '四',
                'user_type': 'normal',
            },
        ]

        created_users = []
        for i, user_data in enumerate(users_data[:count]):
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'  ✓ 创建用户: {user.username}')
            else:
                self.stdout.write(f'  → 用户已存在: {user.username}')
            
            created_users.append(user)

        return created_users

    def create_customers(self, count):
        """创建客户"""
        self.stdout.write(f'🏢 创建 {count} 个客户...')
        
        customers_data = [
            {
                'name': '北京科技有限公司',
                'contact': '13800138001',
                'address': '北京市朝阳区中关村大街1号'
            },
            {
                'name': '上海贸易集团',
                'contact': '13800138002', 
                'address': '上海市浦东新区陆家嘴环路888号'
            },
            {
                'name': '广州制造企业',
                'contact': '13800138003',
                'address': '广州市天河区珠江新城花城大道123号'
            },
            {
                'name': '深圳创新公司',
                'contact': '13800138004',
                'address': '深圳市南山区科技园南区深南大道9999号'
            },
            {
                'name': '成都发展有限公司',
                'contact': '13800138005',
                'address': '成都市高新区天府大道中段666号'
            },
            {
                'name': '杭州电商平台',
                'contact': '13800138006',
                'address': '杭州市滨江区网商路699号'
            },
        ]

        created_customers = []
        for i, customer_data in enumerate(customers_data[:count]):
            customer, created = Customer.objects.get_or_create(
                name=customer_data['name'],
                defaults=customer_data
            )
            if created:
                self.stdout.write(f'  ✓ 创建客户: {customer.name}')
            else:
                self.stdout.write(f'  → 客户已存在: {customer.name}')
            
            created_customers.append(customer)

        return created_customers

    def create_products(self, count):
        """创建产品"""
        self.stdout.write(f'📱 创建 {count} 个产品...')
        
        products_data = [
            {'name': '智能手机', 'specification': '128GB存储版', 'cost_price': '800.00', 'stock': 150},
            {'name': '智能手机', 'specification': '256GB存储版', 'cost_price': '1000.00', 'stock': 100},
            {'name': '平板电脑', 'specification': '标准版', 'cost_price': '600.00', 'stock': 80},
            {'name': '平板电脑', 'specification': '高端版', 'cost_price': '900.00', 'stock': 50},
            {'name': '无线耳机', 'specification': '标准版', 'cost_price': '150.00', 'stock': 200},
            {'name': '无线耳机', 'specification': '降噪版', 'cost_price': '250.00', 'stock': 120},
            {'name': '智能手表', 'specification': '运动版', 'cost_price': '400.00', 'stock': 75},
            {'name': '智能手表', 'specification': '商务版', 'cost_price': '600.00', 'stock': 60},
            {'name': '移动电源', 'specification': '10000mAh', 'cost_price': '80.00', 'stock': 300},
            {'name': '数据线', 'specification': 'USB-C版', 'cost_price': '20.00', 'stock': 500},
        ]

        created_products = []
        for i, product_data in enumerate(products_data[:count]):
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                specification=product_data['specification'],
                defaults={
                    'cost_price': Decimal(product_data['cost_price']),
                    'current_stock': product_data['stock']
                }
            )
            if created:
                self.stdout.write(f'  ✓ 创建产品: {product.name} - {product.specification}')
            else:
                self.stdout.write(f'  → 产品已存在: {product.name} - {product.specification}')
            
            created_products.append(product)

        return created_products

    def create_stock_records(self, products, users):
        """创建库存记录"""
        self.stdout.write(f'📦 创建库存记录...')
        
        admin_user = next((u for u in users if u.user_type == 'admin'), users[0])
        
        # 为每个产品创建初始入库记录
        for product in products:
            try:
                # 创建初始入库记录
                stock_record = StockRecord.objects.create(
                    product=product,
                    operation_type='in',
                    quantity=product.current_stock,
                    before_stock=0,
                    after_stock=product.current_stock,
                    remark=f'{product.name}初始库存',
                    operated_by=admin_user,
                    operated_at=timezone.now() - timedelta(days=30)
                )
                self.stdout.write(f'  ✓ 创建库存记录: {product.name} 入库 {product.current_stock}')
            except Exception as e:
                self.stdout.write(f'  ❌ 创建库存记录失败: {product.name} - {str(e)}')

        # 创建一些随机的库存操作记录
        for _ in range(len(products) // 2):
            try:
                product = random.choice(products)
                operation_type = random.choice(['in', 'out'])
                quantity = random.randint(10, 50)
                
                if operation_type == 'out' and product.current_stock < quantity:
                    continue  # 跳过库存不足的出库操作
                
                StockRecord.objects.create(
                    product=product,
                    operation_type=operation_type,
                    quantity=quantity,
                    remark=f'测试{operation_type}库操作',
                    operated_by=random.choice(users),
                    operated_at=timezone.now() - timedelta(days=random.randint(1, 20))
                )
            except Exception as e:
                self.stdout.write(f'  ❌ 创建随机库存记录失败: {str(e)}')

    def create_batches(self, count, users):
        """创建批次"""
        self.stdout.write(f'📋 创建 {count} 个批次...')
        
        created_batches = []
        base_date = timezone.now().date() - timedelta(days=30)
        
        for i in range(count):
            batch_date = base_date + timedelta(days=i*5)
            batch_number = f'B{batch_date.strftime("%Y%m%d")}-{i+1:03d}'
            
            batch, created = Batch.objects.get_or_create(
                batch_number=batch_number,
                defaults={
                    'date': batch_date,
                    'created_by': random.choice(users)
                }
            )
            if created:
                self.stdout.write(f'  ✓ 创建批次: {batch.batch_number}')
            else:
                self.stdout.write(f'  → 批次已存在: {batch.batch_number}')
            
            created_batches.append(batch)

        return created_batches

    def create_orders(self, count, batches, customers, products, users):
        """创建订单"""
        self.stdout.write(f'🛒 创建 {count} 个订单...')
        
        order_statuses = ['pending', 'confirmed', 'shipping', 'completed']
        status_weights = [0.1, 0.3, 0.2, 0.4]  # 权重：大部分订单是已完成状态
        
        created_orders = []
        for i in range(count):
            batch = random.choice(batches)
            customer = random.choice(customers)
            product = random.choice(products)
            
            # 随机数量和价格
            quantity = random.randint(1, 20)
            base_price = float(product.cost_price) * random.uniform(1.3, 2.0)  # 30%-100%利润
            unit_price = round(base_price, 2)
            
            # 随机其他成本
            other_costs = random.uniform(10, 100)
            
            # 随机状态
            status = random.choices(order_statuses, weights=status_weights)[0]
            
            # 随机订单日期（在批次日期前后）
            order_date = batch.date + timedelta(days=random.randint(-2, 5))
            
            # 检查库存是否足够（如果是已确认状态）
            if status in ['confirmed', 'shipping', 'completed'] and product.current_stock < quantity:
                quantity = min(quantity, product.current_stock)
                if quantity <= 0:
                    continue  # 跳过库存不足的订单
            
            try:
                order = Order.objects.create(
                    batch=batch,
                    customer=customer,
                    product=product,
                    quantity=quantity,
                    unit_price=Decimal(str(round(unit_price, 2))),
                    other_costs=Decimal(str(round(other_costs, 2))),
                    status=status,
                    remark=f'测试订单 - {product.name}批量采购',
                    order_date=order_date,
                    created_by=random.choice(users)
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ 创建订单失败: {str(e)}')
                )
                continue
            
            created_orders.append(order)
            self.stdout.write(
                f'  ✓ 创建订单: {order.id} - {customer.name} - {product.name} x{quantity}'
            )

        # 重新计算所有批次的利润
        self.stdout.write('\n🔄 重新计算批次利润...')
        for batch in batches:
            try:
                batch.calculate_total_profit()
                self.stdout.write(f'  ✓ 批次 {batch.batch_number}: ¥{float(batch.total_profit):,.2f}')
            except Exception as e:
                self.stdout.write(f'  ❌ 批次 {batch.batch_number} 利润计算失败: {str(e)}')

        return created_orders

    def print_summary(self):
        """打印数据汇总"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 数据汇总:'))
        self.stdout.write('='*50)
        
        # 统计数据
        stats = {
            '👥 用户数量': User.objects.count(),
            '🏢 客户数量': Customer.objects.count(),
            '📱 产品数量': Product.objects.count(),
            '📋 批次数量': Batch.objects.count(),
            '🛒 订单数量': Order.objects.count(),
            '📦 库存记录数量': StockRecord.objects.count(),
        }
        
        for label, count in stats.items():
            self.stdout.write(f'{label}: {count}')
        
        # 订单状态统计
        self.stdout.write('\n📈 订单状态分布:')
        try:
            order_stats = Order.objects.values('status').annotate(
                count=models.Count('id')
            ).order_by('status')
            
            status_display = {
                'pending': '待确认',
                'confirmed': '已确认', 
                'shipping': '发货中',
                'completed': '已完成',
                'cancelled': '已取消',
            }
            
            for stat in order_stats:
                status_name = status_display.get(stat['status'], stat['status'])
                self.stdout.write(f'  {status_name}: {stat["count"]}')
        except Exception as e:
            self.stdout.write(f'  统计错误: {str(e)}')
        
        # 利润统计
        try:
            total_profit_result = Order.objects.filter(
                status__in=['confirmed', 'shipping', 'completed']
            ).aggregate(
                total=models.Sum('gross_profit')
            )['total']
            
            total_profit = total_profit_result or Decimal('0')
            self.stdout.write(f'\n💰 总利润: ¥{float(total_profit):,.2f}')
        except Exception as e:
            self.stdout.write(f'\n💰 总利润: 计算错误 - {str(e)}')
        
        # 库存价值
        try:
            total_stock_value_result = Product.objects.aggregate(
                total=models.Sum(
                    models.F('current_stock') * models.F('cost_price')
                )
            )['total']
            
            total_stock_value = total_stock_value_result or Decimal('0')
            self.stdout.write(f'📦 库存总价值: ¥{float(total_stock_value):,.2f}')
        except Exception as e:
            self.stdout.write(f'📦 库存总价值: 计算错误 - {str(e)}')
        
        self.stdout.write('\n🎉 可以开始使用系统进行测试了！')
        self.stdout.write('\n💡 登录信息:')
        self.stdout.write('  管理员: admin / admin123456')
        self.stdout.write('  用户1: user1 / user123456') 
        self.stdout.write('  用户2: user2 / user123456')


# 添加必要的导入
from django.db import models