from .models import AuditLog

def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def log_event(user, action, request=None, description=''):
    AuditLog.objects.create(user=user if getattr(user, 'is_authenticated', False) else None, action=action, description=description, ip_address=get_client_ip(request) if request else None)
