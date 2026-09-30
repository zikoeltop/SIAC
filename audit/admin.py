from django.contrib import admin
from .models import AuditLog
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display=('created_at','user','action','ip_address','description')
    list_filter=('action','created_at')
    search_fields=('user__username','description','ip_address')
    readonly_fields=('user','action','description','ip_address','created_at')
