import logging
from django.utils import timezone
from .models import AuditLog

logger = logging.getLogger('django')

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def log_activity(request, action, module, description, details=None):
    """
    Log user activity to database (Audit Trail)
    
    Args:
        request: Django request object
        action: CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, IMPORT
        module: auth, financials, inventory, sales, hr, bi, reports
        description: Human readable description
        details: Dictionary with additional details
    """
    if not request.user or not request.user.is_authenticated:
        return None
    
    try:
        audit_log = AuditLog.objects.create(
            business=request.user.business if hasattr(request.user, 'business') else None,
            user=request.user,
            action=action.upper(),
            module=module.lower(),
            description=description,
            details=details or {},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Also log to console
        logger.info(f"AUDIT: {request.user.email} - {action} - {module} - {description}")
        
        return audit_log
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")
        return None

def log_error(error, request=None):
    """Log an error"""
    error_msg = f"ERROR: {str(error)}"
    if request:
        user = str(request.user) if request.user.is_authenticated else 'Anonymous'
        error_msg = f"[User: {user}] [Path: {request.path}] ERROR: {str(error)}"
    logger.error(error_msg)

def log_info(message, request=None):
    """Log info message"""
    msg = message
    if request:
        user = str(request.user) if request.user.is_authenticated else 'Anonymous'
        msg = f"[User: {user}] [Path: {request.path}] {message}"
    logger.info(msg)