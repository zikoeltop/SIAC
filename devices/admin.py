from django.contrib import admin
from .models import Device, DeviceImport
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('serial_number','user_name','project','model','computer_name','imported_at')
    search_fields = ('serial_number','user_name','computer_name','project')
@admin.register(DeviceImport)
class DeviceImportAdmin(admin.ModelAdmin):
    list_display = ('file','uploaded_by','uploaded_at','rows_imported','is_current')


from .models import Asset, Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('hr_code', 'name', 'project', 'department', 'position', 'employment_status')
    search_fields = ('hr_code', 'name', 'arabic_name', 'project', 'department')
    list_filter = ('sector', 'department', 'employment_status')

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'asset_type', 'hr_code', 'employee_name', 'project', 'asset_status', 'source_sheet')
    search_fields = ('serial_number', 'hr_code', 'employee_name', 'computer_name_new', 'computer_name', 'model')
    list_filter = ('asset_type', 'asset_status', 'source_sheet', 'project')

from .models import AssetMovement

@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    list_display = ('effective_date', 'asset', 'event_type', 'from_hr_code', 'from_employee_name', 'to_hr_code', 'to_employee_name', 'created_by')
    search_fields = ('asset__serial_number', 'asset__computer_name_new', 'from_hr_code', 'from_employee_name', 'to_hr_code', 'to_employee_name', 'reason', 'reference_number')
    list_filter = ('event_type', 'effective_date', 'source_sheet')
    date_hierarchy = 'effective_date'
    readonly_fields = tuple(field.name for field in AssetMovement._meta.fields)

    def has_add_permission(self, request):
        # Movement history is written through controlled asset workflows and imports.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
