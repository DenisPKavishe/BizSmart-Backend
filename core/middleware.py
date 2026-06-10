# backend/audit/middleware.py

import logging
from django.utils import timezone

from core.logging_utils import get_client_ip, log_activity

logger = logging.getLogger('django')

class RequestLoggingMiddleware:
    """Log all requests and responses for debugging"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = timezone.now()
        user = str(request.user) if request.user.is_authenticated else 'Anonymous'
        ip = get_client_ip(request)
        
        logger.info(f"→ {request.method} {request.path} | User: {user} | IP: {ip}")
        
        response = self.get_response(request)
        
        duration = (timezone.now() - start_time).total_seconds()
        logger.info(f"← {request.method} {request.path} | Status: {response.status_code} | Duration: {duration:.2f}s")
        
        return response


class AuditLogMiddleware:
    """Log important user actions to database automatically"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log modifications (POST, PUT, PATCH, DELETE)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and request.user.is_authenticated:
            
            # Determine module based on URL path
            module = self.get_module_from_path(request.path)
            action = self.get_action_from_method(request.method)
            description = f"{request.method} {request.path}"
            
            # Get entity ID if present in URL
            entity_id = self.get_entity_id_from_path(request.path)
            
            log_activity(
                request=request,
                action=action,
                module=module,
                description=description,
                details={
                    'path': request.path,
                    'method': request.method,
                    'status_code': response.status_code,
                    'entity_id': entity_id,
                }
            )
        
        # Log login/logout specifically
        if request.path.endswith('/login/') and request.method == 'POST' and response.status_code == 200:
            log_activity(
                request=request,
                action='LOGIN',
                module='auth',
                description=f"User logged in",
                details={'path': request.path}
            )
        
        if request.path.endswith('/logout/') and request.method == 'POST':
            log_activity(
                request=request,
                action='LOGOUT',
                module='auth',
                description=f"User logged out",
                details={'path': request.path}
            )
        
        return response
    
    def get_module_from_path(self, path):
        """Determine module from URL path"""
        if '/api/v1/auth/' in path:
            return 'auth'
        elif '/api/v1/financials/' in path:
            return 'financials'
        elif '/api/v1/inventory/' in path:
            return 'inventory'
        elif '/api/v1/sales/' in path:
            return 'sales'
        elif '/api/v1/hr/' in path:
            return 'hr'
        elif '/api/v1/bi/' in path:
            return 'bi'
        elif '/api/v1/reports/' in path:
            return 'reports'
        return 'auth'
    
    def get_action_from_method(self, method):
        """Get action type from HTTP method"""
        if method == 'POST':
            return 'CREATE'
        elif method == 'PUT' or method == 'PATCH':
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        return 'READ'
    
    def get_entity_id_from_path(self, path):
        """Extract entity ID from URL path if present"""
        parts = path.split('/')
        for part in parts:
            if part.isdigit():
                return int(part)
        return None