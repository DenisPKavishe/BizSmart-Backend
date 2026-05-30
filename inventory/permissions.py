# inventory/permissions.py

from rest_framework import permissions


class CanViewInventory(permissions.BasePermission):
    """Owner, Manager, Inventory Manager, Cashier, Auditor can view inventory"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager', 'cashier', 'auditor']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanManageInventory(permissions.BasePermission):
    """Owner, Manager, Inventory Manager can create/edit inventory"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanDeleteInventory(permissions.BasePermission):
    """Only Owner can delete inventory items"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        return request.user.role.name == 'owner' or request.user.is_superuser


class CanAdjustStock(permissions.BasePermission):
    """Owner, Manager, Inventory Manager can adjust stock levels"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanViewSuppliers(permissions.BasePermission):
    """Owner, Manager, Inventory Manager, Auditor can view suppliers"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager', 'auditor']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanManageSuppliers(permissions.BasePermission):
    """Owner, Manager, Inventory Manager can manage suppliers"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanViewCategories(permissions.BasePermission):
    """Most roles can view categories"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager', 'cashier', 'auditor']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class CanManageCategories(permissions.BasePermission):
    """Owner, Manager, Inventory Manager can manage categories"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return request.user.is_superuser
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles or request.user.is_superuser


class IsAuditorInventoryReadOnly(permissions.BasePermission):
    """Auditor can only view, not modify inventory"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return True
        
        if request.user.role.name == 'auditor':
            return request.method in permissions.SAFE_METHODS
        
        return True