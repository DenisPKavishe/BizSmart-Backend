from rest_framework import permissions

class CanRegisterUsers(permissions.BasePermission):
    """Only Owner and Manager can register new users"""
    
    def has_permission(self, request, view):
        # Allow Swagger schema generation
        if getattr(view, 'swagger_fake_view', False):
            return True
        
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager']
        
        return request.user.role.name in allowed_roles


class CanViewUsers(permissions.BasePermission):
    """Owner, Manager, Accountant, Auditor can view users"""
    
    def has_permission(self, request, view):
        if getattr(view, 'swagger_fake_view', False):
            return True
        
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        allowed_roles = ['owner', 'general_manager', 'accountant', 'auditor']
        
        return request.user.role.name in allowed_roles


class CanManageUsers(permissions.BasePermission):
    """Only Owner can delete or change roles of users"""
    
    def has_permission(self, request, view):
        if getattr(view, 'swagger_fake_view', False):
            return True
        
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return False
        
        return request.user.role.name == 'owner'


class IsAuditorUserReadOnly(permissions.BasePermission):
    """Auditor can only view, not modify users"""
    
    def has_permission(self, request, view):
        if getattr(view, 'swagger_fake_view', False):
            return True
        
        if not request.user.is_authenticated:
            return False
        
        if not request.user.role:
            return True
        
        if request.user.role.name == 'auditor':
            return request.method in permissions.SAFE_METHODS
        
        return True