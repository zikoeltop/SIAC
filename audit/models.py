from django.conf import settings
from django.db import models

class AuditLog(models.Model):
    ACTIONS = [
        ('LOGIN','Login'),('LOGOUT','Logout'),('DEVICE_SEARCH','Device search'),('ASSET_SEARCH','Asset search'),
        ('PDF_DOWNLOAD','PDF download'),('CUSTODY_PDF_DOWNLOAD','Custody PDF download'),('EXCEL_IMPORT','Excel import'),('EXCEL_PREVIEW','Excel preview'),
        ('INVENTORY_PREVIEW','Inventory import preview'),('INVENTORY_IMPORT','Inventory import'),('INVENTORY_EXPORT','Inventory export'),
        ('EMPLOYEE_CREATE','Employee create'),('EMPLOYEE_EDIT','Employee edit'),('ASSET_CREATE','Asset create'),('ASSET_EDIT','Asset edit'),
        ('USER_CREATE','User create'),('USER_EDIT','User edit'),('USER_DELETE','User delete'),
        ('ASSET_ASSIGN','Asset assigned'),('ASSET_TRANSFER','Asset custody transferred'),
        ('ASSET_RETURN','Asset returned to stock'),('ASSET_SCRAP','Asset scrapped'),
        ('DASHBOARD_EXPORT','Management dashboard export'),('EMPLOYEE_DELETE','Employee delete'),
        ('LEGACY_DEVICE_CREATE','Legacy device create'),('LEGACY_DEVICE_EDIT','Legacy device edit'),('LEGACY_DEVICE_DELETE','Legacy device delete'),
        ('LEGACY_IMPORT_CREATE','Legacy import create'),('LEGACY_IMPORT_EDIT','Legacy import edit'),('LEGACY_IMPORT_DELETE','Legacy import delete'),
        ('PASSWORD_CHANGE','Password change'),('PASSWORD_RESET','Password reset'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40, choices=ACTIONS)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
