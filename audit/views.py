from django.shortcuts import render
from accounts.decorators import admin_required
from .models import AuditLog
@admin_required
def log_list(request):
    return render(request, 'audit/log_list.html', {'logs': AuditLog.objects.select_related('user')[:500]})
