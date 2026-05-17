import logging
from django.utils import timezone
from .models import AuditLog

logger = logging.getLogger('django')

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

def get_client_ip(request):
    """Get client IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def log_activity(request, action, module, description, details=None):
    """Log user activity to database (Audit Trail)"""
    if not request.user.is_authenticated:
        return
    
    AuditLog.objects.create(
        business=request.user.business,
        user=request.user,
        action=action,
        module=module,
        description=description,
        details=details or {},
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    
    # Also log to console
    logger.info(f"AUDIT: {request.user.email} - {action} - {module} - {description}")