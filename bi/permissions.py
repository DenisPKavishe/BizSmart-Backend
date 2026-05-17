from rest_framework import permissions

class CanViewBIDashboard(permissions.BasePermission):
    """
    Allow Owner, Manager, Accountant, Auditor to view BI dashboard.
    
    Cashier and Inventory Manager cannot see full BI.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanViewFinancialBI(permissions.BasePermission):
    """
    Only Owner and Accountant can see financial insights.
    
    Financial data is sensitive and should be restricted.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewInventoryBI(permissions.BasePermission):
    """
    Owner, Manager, and Inventory Manager can see inventory insights.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'inventory_manager']
        
        return request.user.role.name in allowed_roles


class CanViewSalesBI(permissions.BasePermission):
    """
    Owner, Manager, Accountant, and Auditor can see sales insights.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class IsOwnerOnly(permissions.BasePermission):
    """
    Only Owner can access sensitive data like forecasts.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.business:
            return False
        
        if not request.user.role:
            return False
        
        return request.user.role.name == 'owner'