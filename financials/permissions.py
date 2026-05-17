from rest_framework import permissions

class CanViewFinancials(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view financial data"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanEditFinancials(permissions.BasePermission):
    """Only Owner and Accountant can create/edit financial records"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewInvoices(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view invoices"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanCreateInvoices(permissions.BasePermission):
    """Owner, Manager, Accountant can create invoices"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewLoans(permissions.BasePermission):
    """Owner, Accountant, Auditor can view loans"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanViewPettyCash(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view petty cash"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanExportReports(permissions.BasePermission):
    """Only Owner and Accountant can export financial reports"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class IsAuditorReadOnly(permissions.BasePermission):
    """Auditor can only view, not modify"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return True
        
        if request.user.role.name == 'auditor':
            return request.method in permissions.SAFE_METHODS
        
        return True