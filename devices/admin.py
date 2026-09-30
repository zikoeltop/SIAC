from django.contrib import admin
from .models import Device, DeviceImport
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('serial_number','user_name','project','model','computer_name','imported_at')
    search_fields = ('serial_number','user_name','computer_name','project')
@admin.register(DeviceImport)
class DeviceImportAdmin(admin.ModelAdmin):
    list_display = ('file','uploaded_by','uploaded_at','rows_imported','is_current')
