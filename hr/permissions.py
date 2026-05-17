from rest_framework import permissions

class CanViewHR(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view HR data"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanManageEmployees(permissions.BasePermission):
    """Only Owner and Accountant can create/edit employees"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewSalaries(permissions.BasePermission):
    """Owner, Accountant, Auditor can view salaries (Manager cannot)"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanManageSalaries(permissions.BasePermission):
    """Only Owner and Accountant can manage salaries"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanProcessPayroll(permissions.BasePermission):
    """Only Owner and Accountant can process payroll"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'accountant']
        
        return request.user.role.name in allowed_roles


class CanViewHRReports(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view HR reports"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class IsAuditorHRReadOnly(permissions.BasePermission):
    """Auditor can only view, not modify HR data"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return True
        
        if request.user.role.name == 'auditor':
            return request.method in permissions.SAFE_METHODS
        
        return True