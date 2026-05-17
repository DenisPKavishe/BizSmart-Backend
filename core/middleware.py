import logging
from django.utils import timezone
from .logging_utils import get_client_ip, log_activity

logger = logging.getLogger('django')

class RequestLoggingMiddleware:
    """Log all requests and responses"""
    
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
    """Log important user actions to database"""
    
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
            
            log_activity(
                request=request,
                action=action,
                module=module,
                description=description,
                details={
                    'path': request.path,
                    'method': request.method,
                    'status_code': response.status_code
                }
            )
        
        return response
    
    def get_module_from_path(self, path):
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
        return 'auth'
    
    def get_action_from_method(self, method):
        if method == 'POST':
            return 'CREATE'
        elif method == 'PUT' or method == 'PATCH':
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        return 'READ'