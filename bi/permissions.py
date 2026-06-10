# bi/permissions.py

from rest_framework import permissions


class CanViewBIDashboard(permissions.BasePermission):
    """Allow Owner, Manager, Accountant, Auditor to view BI dashboard"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanViewFinancialBI(permissions.BasePermission):
    """Only Owner and Accountant can see financial insights"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewInventoryBI(permissions.BasePermission):
    """Owner, Manager, and Inventory Manager can see inventory insights"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles


class CanViewSalesBI(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can see sales insights"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanViewHRBI(permissions.BasePermission):
    """Owner, Manager, HR Manager can see HR insights"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'hr_manager']
        
        return request.user.role.name in allowed_roles


class CanViewCustomerBI(permissions.BasePermission):
    """Owner, Manager, Accountant can see customer insights"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant']
        
        return request.user.role.name in allowed_roles


class IsOwnerOnly(permissions.BasePermission):
    """Only Owner can access sensitive data like forecasts and goals"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        return request.user.role.name == 'owner'