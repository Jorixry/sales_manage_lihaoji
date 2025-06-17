# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'customers', views.CustomerViewSet, basename='customer')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'batches', views.BatchViewSet, basename='batch')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'stock-records', views.StockRecordViewSet, basename='stockrecord')

app_name = 'api'

urlpatterns = [
    # 认证相关URL
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/profile/', views.profile, name='profile'),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),  # DRF默认token认证
    
    # 报表统计URL
    path('reports/product-sales/', views.product_sales_stats, name='product_sales_stats'),
    path('reports/customer-sales/', views.customer_sales_stats, name='customer_sales_stats'),
    path('reports/daily-sales/', views.daily_sales_stats, name='daily_sales_stats'),
    path('reports/dashboard/', views.dashboard_stats, name='dashboard_stats'),
    
    # 包含所有ViewSet的URL
    path('', include(router.urls)),
]

# 完整的URL列表说明：
"""
API接口列表：

认证接口：
- POST /api/auth/login/                    # 用户登录
- POST /api/auth/logout/                   # 用户登出
- GET  /api/auth/profile/                  # 获取当前用户信息
- POST /api/auth/token/                    # 获取认证token（DRF默认）

用户管理：
- GET    /api/users/                       # 用户列表
- POST   /api/users/                       # 创建用户
- GET    /api/users/{id}/                  # 用户详情
- PUT    /api/users/{id}/                  # 更新用户
- PATCH  /api/users/{id}/                  # 部分更新用户
- DELETE /api/users/{id}/                  # 删除用户
- POST   /api/users/{id}/set_password/     # 重置用户密码
- POST   /api/users/{id}/toggle_active/    # 切换用户激活状态

客户管理：
- GET    /api/customers/                   # 客户列表
- POST   /api/customers/                   # 创建客户
- GET    /api/customers/{id}/              # 客户详情
- PUT    /api/customers/{id}/              # 更新客户
- PATCH  /api/customers/{id}/              # 部分更新客户
- DELETE /api/customers/{id}/              # 删除客户
- GET    /api/customers/{id}/orders/       # 客户订单列表
- GET    /api/customers/{id}/stats/        # 客户销售统计

产品管理：
- GET    /api/products/                    # 产品列表
- POST   /api/products/                    # 创建产品
- GET    /api/products/{id}/               # 产品详情
- PUT    /api/products/{id}/               # 更新产品
- PATCH  /api/products/{id}/               # 部分更新产品
- DELETE /api/products/{id}/               # 删除产品
- GET    /api/products/low_stock/          # 库存偏低的产品
- POST   /api/products/{id}/stock_in/      # 产品入库
- GET    /api/products/{id}/stock_records/ # 产品库存记录
- GET    /api/products/{id}/sales_stats/   # 产品销售统计

批次管理：
- GET    /api/batches/                     # 批次列表
- POST   /api/batches/                     # 创建批次
- GET    /api/batches/{id}/                # 批次详情
- PUT    /api/batches/{id}/                # 更新批次
- PATCH  /api/batches/{id}/                # 部分更新批次
- DELETE /api/batches/{id}/                # 删除批次
- GET    /api/batches/{id}/orders/         # 批次订单列表
- POST   /api/batches/{id}/add_orders/     # 批量添加订单到批次
- POST   /api/batches/{id}/recalculate_profit/ # 重新计算批次利润
- GET    /api/batches/{id}/summary/        # 批次汇总信息

订单管理：
- GET    /api/orders/                      # 订单列表
- POST   /api/orders/                      # 创建订单
- GET    /api/orders/{id}/                 # 订单详情
- PUT    /api/orders/{id}/                 # 更新订单
- PATCH  /api/orders/{id}/                 # 部分更新订单
- DELETE /api/orders/{id}/                 # 删除订单
- POST   /api/orders/{id}/update_status/   # 更新订单状态
- POST   /api/orders/batch_update_status/  # 批量更新订单状态

库存记录：
- GET    /api/stock-records/               # 库存记录列表
- POST   /api/stock-records/               # 创建库存记录
- GET    /api/stock-records/{id}/          # 库存记录详情
- GET    /api/stock-records/summary/       # 库存操作汇总

报表统计：
- GET    /api/reports/product-sales/       # 产品销售统计
- GET    /api/reports/customer-sales/      # 客户销售统计
- GET    /api/reports/daily-sales/         # 每日销售统计
- GET    /api/reports/dashboard/           # 仪表盘统计数据

查询参数说明：
- page: 页码（默认1）
- page_size: 每页数量（默认20，最大100）
- search: 搜索关键词
- ordering: 排序字段（可以用'-'表示倒序）
- start_date: 开始日期（YYYY-MM-DD格式）
- end_date: 结束日期（YYYY-MM-DD格式）

各个列表接口还支持特定的过滤参数，详见各ViewSet的filterset_fields配置。
"""