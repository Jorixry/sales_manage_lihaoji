# 销售管理系统 API 文档

## 1. 概述

本文档描述了销售管理系统的RESTful API接口，包括用户认证、客户管理、产品管理、批次管理、订单管理、库存管理和报表统计等功能。

### 基础信息
- **Base URL**: `http://your-domain.com/api/`
- **认证方式**: Token Authentication
- **数据格式**: JSON
- **编码**: UTF-8

## 2. 认证

### 2.1 登录
```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

**响应示例：**
```json
{
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "user_type": "admin",
        "first_name": "管理员",
        "last_name": "用户"
    }
}
```

### 2.2 请求头认证
获取token后，在后续请求中添加认证头：
```http
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### 2.3 登出
```http
POST /api/auth/logout/
Authorization: Token your_token

响应：
{
    "message": "登出成功"
}
```

### 2.4 获取当前用户信息
```http
GET /api/auth/profile/
Authorization: Token your_token
```

## 3. 用户管理 (仅管理员可访问)

### 3.1 用户列表
```http
GET /api/users/?page=1&page_size=20&search=关键词
```

**查询参数：**
- `page`: 页码
- `page_size`: 每页数量
- `search`: 搜索用户名、邮箱、姓名
- `user_type`: 过滤用户类型 (admin/normal)
- `is_active`: 过滤激活状态 (true/false)
- `ordering`: 排序字段 (username, date_joined, -date_joined)

### 3.2 创建用户
```http
POST /api/users/
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "confirm_password": "password123",
    "first_name": "新",
    "last_name": "用户",
    "user_type": "normal"
}
```

### 3.3 重置用户密码
```http
POST /api/users/{user_id}/set_password/
Content-Type: application/json

{
    "password": "new_password123"
}
```

### 3.4 切换用户激活状态
```http
POST /api/users/{user_id}/toggle_active/

响应：
{
    "message": "用户已激活",
    "is_active": true
}
```

## 4. 客户管理

### 4.1 客户列表
```http
GET /api/customers/?search=客户名称&ordering=-created_at
```

**响应示例：**
```json
{
    "count": 50,
    "next": "http://api/customers/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "ABC公司",
            "contact": "13800138000",
            "address": "北京市朝阳区...",
            "order_count": 15,
            "total_sales": "125000.00",
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-01-20T14:20:00Z"
        }
    ]
}
```

### 4.2 创建客户
```http
POST /api/customers/
Content-Type: application/json

{
    "name": "新客户公司",
    "contact": "13900139000",
    "address": "上海市浦东新区..."
}
```

### 4.3 客户详情
```http
GET /api/customers/{customer_id}/

响应包含客户基本信息和最近5个订单：
{
    "id": 1,
    "name": "ABC公司",
    "contact": "13800138000",
    "address": "北京市朝阳区...",
    "recent_orders": [
        {
            "id": 101,
            "batch_number": "B20250115-001",
            "product_name": "产品A",
            "quantity": 10,
            "sales_amount": "5000.00",
            "status": "已完成",
            "order_date": "2025-01-15"
        }
    ],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

### 4.4 客户订单列表
```http
GET /api/customers/{customer_id}/orders/?page=1
```

### 4.5 客户销售统计
```http
GET /api/customers/{customer_id}/stats/

响应：
{
    "total_orders": 15,
    "total_sales": "125000.00",
    "total_profit": "25000.00",
    "avg_order_value": "8333.33",
    "last_order_date": "2025-01-15"
}
```

## 5. 产品管理

### 5.1 产品列表
```http
GET /api/products/?search=产品名称&specification=规格&ordering=name
```

**响应示例：**
```json
{
    "count": 30,
    "results": [
        {
            "id": 1,
            "name": "产品A",
            "specification": "标准型",
            "cost_price": "50.00",
            "current_stock": 100,
            "sold_quantity": 500,
            "stock_status": "in_stock",
            "total_sold_value": "25000.00",
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]
}
```

**库存状态说明：**
- `in_stock`: 库存充足 (>10)
- `low_stock`: 库存偏低 (1-10)
- `out_of_stock`: 缺货 (0)

### 5.2 创建产品
```http
POST /api/products/
Content-Type: application/json

{
    "name": "新产品",
    "specification": "高级型",
    "cost_price": "80.00",
    "current_stock": 50
}
```

### 5.3 库存偏低产品
```http
GET /api/products/low_stock/?threshold=10

返回库存数量小于等于threshold的产品列表
```

### 5.4 产品入库
```http
POST /api/products/{product_id}/stock_in/
Content-Type: application/json

{
    "quantity": 100,
    "remark": "新采购入库"
}

响应：
{
    "message": "入库成功",
    "stock_record_id": 15,
    "current_stock": 200
}
```

### 5.5 产品库存记录
```http
GET /api/products/{product_id}/stock_records/
```

### 5.6 产品销售统计
```http
GET /api/products/{product_id}/sales_stats/

响应：
{
    "total_quantity": 500,
    "total_sales": "75000.00",
    "total_profit": "12500.00",
    "avg_unit_price": "150.00",
    "order_count": 25,
    "profit_margin": 16.67
}
```

## 6. 批次管理

### 6.1 批次列表
```http
GET /api/batches/?search=批次号&ordering=-date
```

**响应示例：**
```json
{
    "results": [
        {
            "id": 1,
            "batch_number": "B20250115-001",
            "date": "2025-01-15",
            "total_profit": "5000.00",
            "order_count": 8,
            "total_sales": "25000.00",
            "profit_margin": 20.0,
            "created_by_name": "admin",
            "created_at": "2025-01-15T09:00:00Z"
        }
    ]
}
```

### 6.2 创建批次
```http
POST /api/batches/
Content-Type: application/json

{
    "batch_number": "B20250120-001",
    "date": "2025-01-20"
}
```

### 6.3 批次订单列表
```http
GET /api/batches/{batch_id}/orders/
```

### 6.4 批量添加订单到批次
```http
POST /api/batches/{batch_id}/add_orders/
Content-Type: application/json

{
    "orders": [
        {
            "customer_id": 1,
            "product_id": 1,
            "quantity": 10,
            "unit_price": "100.00",
            "other_costs": "50.00",
            "status": "pending",
            "remark": "特殊客户价格",
            "order_date": "2025-01-15"
        },
        {
            "customer_id": 2,
            "product_id": 2,
            "quantity": 5,
            "unit_price": "200.00"
        }
    ]
}

响应：
{
    "message": "成功创建2个订单",
    "order_ids": [101, 102]
}
```

### 6.5 重新计算批次利润
```http
POST /api/batches/{batch_id}/recalculate_profit/

响应：
{
    "message": "利润重新计算完成",
    "total_profit": "5250.00"
}
```

### 6.6 批次汇总信息
```http
GET /api/batches/{batch_id}/summary/

响应：
{
    "batch_info": { 批次基本信息 },
    "orders_stats": {
        "total_orders": 8,
        "confirmed_orders": 6,
        "pending_orders": 2,
        "cancelled_orders": 0,
        "total_sales": "25000.00",
        "total_cost": "20000.00"
    },
    "profit_margin": 20.0
}
```

## 7. 订单管理

### 7.1 订单列表
```http
GET /api/orders/?status=confirmed&search=客户名称&ordering=-order_date
```

**过滤参数：**
- `status`: 订单状态过滤
- `batch`: 批次ID过滤
- `customer`: 客户ID过滤
- `product`: 产品ID过滤

**订单状态：**
- `pending`: 待确认
- `confirmed`: 已确认
- `shipping`: 发货中
- `completed`: 已完成
- `cancelled`: 已取消
- `refund_requested`: 申请退款
- `refunding`: 正在退款
- `refunded`: 已退款

### 7.2 创建订单
```http
POST /api/orders/
Content-Type: application/json

{
    "batch": 1,
    "customer": 1,
    "product": 1,
    "quantity": 10,
    "unit_price": "120.00",
    "other_costs": "30.00",
    "status": "pending",
    "remark": "VIP客户特价",
    "order_date": "2025-01-15"
}

注意：
- sales_amount、total_cost、gross_profit会自动计算
- 如果status为confirmed及以后状态，会自动检查并扣减库存
```

### 7.3 订单详情
```http
GET /api/orders/{order_id}/

响应包含订单详情和关联的批次、客户、产品信息：
{
    "id": 101,
    "batch_info": {
        "id": 1,
        "batch_number": "B20250115-001",
        "date": "2025-01-15"
    },
    "customer_info": {
        "id": 1,
        "name": "ABC公司",
        "contact": "13800138000"
    },
    "product_info": {
        "id": 1,
        "name": "产品A",
        "specification": "标准型",
        "cost_price": "50.00"
    },
    "quantity": 10,
    "unit_price": "120.00",
    "sales_amount": "1200.00",
    "other_costs": "30.00",
    "total_cost": "530.00",
    "gross_profit": "670.00",
    "status": "confirmed",
    "remark": "VIP客户特价",
    "order_date": "2025-01-15",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T14:30:00Z"
}
```

### 7.4 更新订单状态
```http
POST /api/orders/{order_id}/update_status/
Content-Type: application/json

{
    "status": "confirmed"
}

响应：
{
    "message": "订单状态已从\"待确认\"更新为\"已确认\"",
    "status": "confirmed"
}

注意：状态变更会自动处理库存变化
```

### 7.5 批量更新订单状态
```http
POST /api/orders/batch_update_status/
Content-Type: application/json

{
    "order_ids": [101, 102, 103],
    "status": "confirmed"
}

响应：
{
    "message": "成功更新3个订单",
    "updated_count": 3,
    "errors": []  // 如果有错误会列出
}
```

## 8. 库存管理

### 8.1 库存记录列表
```http
GET /api/stock-records/?operation_type=in&product=1&ordering=-operated_at
```

**过滤参数：**
- `operation_type`: 操作类型 (in/out/adjust)
- `product`: 产品ID

### 8.2 创建库存记录
```http
POST /api/stock-records/
Content-Type: application/json

// 入库操作
{
    "product": 1,
    "operation_type": "in",
    "quantity": 100,
    "remark": "新采购入库"
}

// 出库操作
{
    "product": 1,
    "operation_type": "out",
    "quantity": 50,
    "remark": "手动出库"
}

// 库存调整
{
    "product": 1,
    "operation_type": "adjust",
    "after_stock": 85,
    "remark": "盘点调整"
}
```

### 8.3 库存操作汇总
```http
GET /api/stock-records/summary/

响应：
{
    "today": {
        "total_operations": 5,
        "in_operations": 3,
        "out_operations": 1,
        "adjust_operations": 1
    },
    "this_week": {
        "total_operations": 25,
        "in_operations": 15,
        "out_operations": 8,
        "adjust_operations": 2
    }
}
```

## 9. 报表统计

### 9.1 产品销售统计
```http
GET /api/reports/product-sales/?start_date=2025-01-01&end_date=2025-01-31

响应：
[
    {
        "product_id": 1,
        "product_name": "产品A",
        "product_specification": "标准型",
        "total_quantity": 500,
        "total_sales": "75000.00",
        "total_profit": "12500.00",
        "avg_unit_price": "150.00"
    }
]
```

### 9.2 客户销售统计
```http
GET /api/reports/customer-sales/?start_date=2025-01-01&end_date=2025-01-31

响应：
[
    {
        "customer_id": 1,
        "customer_name": "ABC公司",
        "order_count": 15,
        "total_sales": "125000.00",
        "total_profit": "25000.00"
    }
]
```

### 9.3 每日销售统计
```http
GET /api/reports/daily-sales/?start_date=2025-01-01&end_date=2025-01-31

响应：
[
    {
        "date": "2025-01-15",
        "order_count": 8,
        "total_sales": "25000.00",
        "total_profit": "5000.00"
    }
]

注意：如果不提供日期参数，默认返回最近30天的数据
```

### 9.4 仪表盘统计
```http
GET /api/reports/dashboard/

响应：
{
    "today": {
        "order_count": 5,
        "total_sales": "8500.00",
        "total_profit": "1700.00"
    },
    "this_month": {
        "order_count": 120,
        "total_sales": "250000.00",
        "total_profit": "50000.00"
    },
    "stock": {
        "total_products": 50,
        "low_stock_products": 8,
        "out_of_stock_products": 2,
        "total_stock_value": "125000.00"
    },
    "customer": {
        "total_customers": 25,
        "active_customers": 18
    }
}
```

## 10. 错误处理

### 10.1 HTTP状态码
- `200 OK`: 请求成功
- `201 Created`: 创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

### 10.2 错误响应格式
```json
{
    "error": "错误信息",
    "details": {
        "field_name": ["字段相关的错误信息"]
    }
}
```

或

```json
{
    "field_name": ["字段相关的错误信息"],
    "non_field_errors": ["非字段错误信息"]
}
```

## 11. 分页

所有列表接口都支持分页，响应格式：
```json
{
    "count": 总数量,
    "next": "下一页URL",
    "previous": "上一页URL",
    "results": [数据列表]
}
```

**分页参数：**
- `page`: 页码（从1开始）
- `page_size`: 每页数量（默认20，最大100）

## 12. 权限说明

### 12.1 用户类型
- `admin`: 管理员 - 拥有所有权限
- `normal`: 普通用户 - 有限权限

### 12.2 权限矩阵

| 功能 | 管理员 | 普通用户 |
|------|--------|----------|
| 用户管理 | 增删改查 | 查看自己 |
| 客户管理 | 增删改查 | 增删改查 |
| 产品管理 | 增删改查 | 查看 |
| 批次管理 | 增删改查 | 管理自己创建的 |
| 订单管理 | 增删改查 | 管理自己创建的 |
| 库存管理 | 增删改查 | 查看 |
| 报表统计 | 查看所有 | 查看所有 |

## 13. 使用示例

### 13.1 完整流程示例

```bash
# 1. 登录获取token
curl -X POST http://api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. 创建客户
curl -X POST http://api/customers/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "新客户", "contact": "13900139000", "address": "地址"}'

# 3. 创建产品
curl -X POST http://api/products/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "新产品", "specification": "规格", "cost_price": "50.00", "current_stock": 100}'

# 4. 创建批次
curl -X POST http://api/batches/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"batch_number": "B20250120-001", "date": "2025-01-20"}'

# 5. 创建订单
curl -X POST http://api/orders/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"batch": 1, "customer": 1, "product": 1, "quantity": 10, "unit_price": "80.00"}'
```

### 13.2 JavaScript示例

```javascript
// API客户端类
class SalesAPI {
    constructor(baseURL, token) {
        this.baseURL = baseURL;
        this.token = token;
    }
    
    async request(method, endpoint, data = null) {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Token ${this.token}`
        };
        
        const config = {
            method,
            headers
        };
        
        if (data) {
            config.body = JSON.stringify(data);
        }
        
        const response = await fetch(`${this.baseURL}${endpoint}`, config);
        return await response.json();
    }
    
    // 登录
    async login(username, password) {
        const response = await fetch(`${this.baseURL}/auth/login/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await response.json();
        if (data.token) {
            this.token = data.token;
        }
        return data;
    }
    
    // 获取客户列表
    async getCustomers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await this.request('GET', `/customers/?${query}`);
    }
    
    // 创建订单
    async createOrder(orderData) {
        return await this.request('POST', '/orders/', orderData);
    }
    
    // 获取仪表盘数据
    async getDashboard() {
        return await this.request('GET', '/reports/dashboard/');
    }
}

// 使用示例
const api = new SalesAPI('http://your-domain.com/api');

// 登录
const loginResult = await api.login('admin', 'password');
console.log('登录结果:', loginResult);

// 获取客户列表
const customers = await api.getCustomers({search: '公司', page: 1});
console.log('客户列表:', customers);

// 创建订单
const newOrder = await api.createOrder({
    batch: 1,
    customer: 1,
    product: 1,
    quantity: 5,
    unit_price: '100.00'
});
console.log('新订单:', newOrder);
```

## 14. 注意事项

1. **认证**: 除了登录接口，所有API都需要在Header中提供有效的Token
2. **权限**: 普通用户只能操作自己创建的数据（批次、订单）
3. **库存**: 订单状态变更会自动处理库存变化，无需手动操作
4. **计算字段**: 订单的销售额、总成本、毛利润会自动计算
5. **批次利润**: 批次总利润会在订单变更时自动重新计算
6. **分页**: 建议使用分页来提高性能，特别是数据量大的列表
7. **日期格式**: 使用ISO 8601格式 (YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SSZ)
8. **金额精度**: 所有金额字段精确到小数点后2位
9. **产品唯一性**: 产品名称和规格的组合必须唯一
10. **批次号唯一性**: 批次号在系统中必须唯一

## 15. 常见问题

**Q: 如何处理库存不足的情况？**
A: 创建或更新订单为确认状态时，系统会自动检查库存。如果库存不足，会返回400错误并提示当前库存数量。

**Q: 如何批量导入产品？**
A: 目前需要逐个调用创建产品API。建议在前端实现批量导入功能，循环调用API。

**Q: 订单状态变更的规则是什么？**
A: 一般流程为：待确认→已确认→发货中→已完成。也可以从任何状态变更为已取消或申请退款。

**Q: 如何处理退货退款？**
A: 将订单状态改为"已退款"，系统会自动恢复库存。

**Q: 报表数据的统计范围是什么？**
A: 报表只统计状态为"已确认"、"发货中"、"已完成"的订单，不包括待确认、已取消、已退款的订单。

这份文档涵盖了销售管理系统API的所有功能和使用方法。如有疑问，请参考具体的API响应或联系开发团队。