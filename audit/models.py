from django.conf import settings
from django.db import models

class AuditLog(models.Model):
    ACTIONS = [
        ('LOGIN','Login'),('LOGOUT','Logout'),('DEVICE_SEARCH','Device search'),
        ('PDF_DOWNLOAD','PDF download'),('EXCEL_IMPORT','Excel import'),
        ('USER_CREATE','User create'),('USER_EDIT','User edit'),('USER_DELETE','User delete'),
        ('PASSWORD_CHANGE','Password change'),('PASSWORD_RESET','Password reset'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40, choices=ACTIONS)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
