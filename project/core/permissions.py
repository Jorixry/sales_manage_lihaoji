# permissions.py
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    自定义权限：管理员可以进行所有操作，普通用户只能查看
    """
    def has_permission(self, request, view):
        # 已登录用户才能访问
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 读取权限对所有用户开放
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 写入权限只对管理员开放
        return request.user.is_superuser or request.user.user_type == 'admin'


class IsAdminOrOwner(BasePermission):
    """
    自定义权限：管理员可以访问所有对象，普通用户只能访问自己创建的对象
    """
    def has_permission(self, request, view):
        # 已登录用户才能访问
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 管理员可以访问所有对象
        if request.user.is_superuser or request.user.user_type == 'admin':
            return True
        
        # 检查对象是否有created_by字段
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # 如果没有created_by字段，则允许访问（如Customer, Product等）
        return True


class IsAdminUserOnly(BasePermission):
    """
    只有管理员才能访问的权限
    """
    def has_permission(self, request, view):
        return (request.user and 
                request.user.is_authenticated and 
                (request.user.is_superuser or request.user.user_type == 'admin'))


class IsOwnerOrAdmin(BasePermission):
    """
    对象的所有者或管理员才能访问
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 如果对象就是用户本身（用户管理）
        if hasattr(obj, 'username'):  # User对象
            return obj == request.user or request.user.is_superuser or request.user.user_type == 'admin'
        
        # 其他对象的权限检查
        return (request.user.is_superuser or 
                request.user.user_type == 'admin' or
                (hasattr(obj, 'created_by') and obj.created_by == request.user))


class CanManageStock(BasePermission):
    """
    库存管理权限：管理员和有库存管理权限的用户
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 管理员拥有所有权限
        if request.user.is_superuser or request.user.user_type == 'admin':
            return True
        
        # 普通用户只能查看库存记录
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 创建库存记录需要额外权限验证（可以根据实际需求扩展）
        return False