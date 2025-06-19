# sales_manage_lihaoji

如果你是第一次设置项目，推荐按以下顺序执行：

## 1. 安装依赖（如果还没安装）
```bash
pip install djangorestframework
pip install djangorestframework-authtoken  
pip install django-filter
```

## 2. 创建迁移文件
```
python manage.py makemigrations
```

## 3. 运行迁移
```
python manage.py migrate
```

## 4. 创建超级用户（可选）
```
python manage.py createsuperuser
```

## 5. 创建测试数据
```
python manage.py create_test_data
```

## 6. 启动服务器
```
python manage.py runserver
```