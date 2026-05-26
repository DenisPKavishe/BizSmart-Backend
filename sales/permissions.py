from rest_framework import permissions

class CanProcessSale(permissions.BasePermission):
    """Owner, Manager, Cashier can process sales"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'cashier']
        
        return request.user.role.name in allowed_roles


class CanViewSales(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor, Cashier can view sales"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor', 'cashier']
        
        return request.user.role.name in allowed_roles


class CanManageCustomers(permissions.BasePermission):
    """Owner, Manager, Cashier can create/edit customers"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'cashier']
        
        return request.user.role.name in allowed_roles


class CanViewSalesReports(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view sales reports"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanProcessReturn(permissions.BasePermission):
    """
    Owner, Manager and Cashier can process returns
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not request.user.role:
            return False

        role_name = (
            request.user.role.name
            .lower()
        )

        allowed_roles = [
            'owner',
            'general manager',
            'cashier',
            'sales rep',
        ]

        return any(
            role in role_name
            for role in allowed_roles
        )


class CanViewSalesReports(permissions.BasePermission):
    """
    Can view sales reports and returns
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not request.user.role:
            return False

        role_name = (
            request.user.role.name
            .lower()
        )

        allowed_roles = [
            'owner',
            'general manager',
            'accountant',
            'auditor',
            'viewer',
            'cashier',
            'sales rep',
        ]

        return any(
            role in role_name
            for role in allowed_roles
        )

class CanViewReceipt(permissions.BasePermission):
    """Owner, Manager, Cashier, Accountant, Auditor can view receipts"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'cashier', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class IsAuditorSalesReadOnly(permissions.BasePermission):
    """Auditor can only view, not modify sales"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return True
        
        if request.user.role.name == 'auditor':
            return request.method in permissions.SAFE_METHODS
        
        return True