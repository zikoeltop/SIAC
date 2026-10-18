from django.contrib import admin

from audit.utils import log_event
from .models import Asset, AssetMovement, Device, DeviceImport, Employee, SiteInspection, SiteVisit


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'user_name', 'project', 'model', 'computer_name', 'imported_at')
    search_fields = ('serial_number', 'user_name', 'computer_name', 'project')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = 'LEGACY_DEVICE_EDIT' if change else 'LEGACY_DEVICE_CREATE'
        log_event(request.user, action, request, f"{'Updated' if change else 'Created'} legacy device record serial={obj.serial_number}")

    def delete_model(self, request, obj):
        serial = obj.serial_number
        super().delete_model(request, obj)
        log_event(request.user, 'LEGACY_DEVICE_DELETE', request, f'Deleted legacy device record serial={serial}')

    def delete_queryset(self, request, queryset):
        serials = list(queryset.values_list('serial_number', flat=True))
        super().delete_queryset(request, queryset)
        summary = '; '.join(serials[:100])
        log_event(request.user, 'LEGACY_DEVICE_DELETE', request, f'Deleted legacy device records serials={summary}')


@admin.register(DeviceImport)
class DeviceImportAdmin(admin.ModelAdmin):
    list_display = ('file', 'uploaded_by', 'uploaded_at', 'rows_imported', 'is_current')
    readonly_fields = ('uploaded_at',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = 'LEGACY_IMPORT_EDIT' if change else 'LEGACY_IMPORT_CREATE'
        log_event(request.user, action, request, f"{'Updated' if change else 'Created'} legacy import record id={obj.pk}, rows={obj.rows_imported}")

    def delete_model(self, request, obj):
        import_id = obj.pk
        super().delete_model(request, obj)
        log_event(request.user, 'LEGACY_IMPORT_DELETE', request, f'Deleted legacy import record id={import_id}')

    def delete_queryset(self, request, queryset):
        import_ids = list(queryset.values_list('pk', flat=True))
        super().delete_queryset(request, queryset)
        summary = ', '.join(str(item_id) for item_id in import_ids[:100])
        log_event(request.user, 'LEGACY_IMPORT_DELETE', request, f'Deleted legacy import records ids={summary}')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('hr_code', 'name', 'cost_center', 'project', 'department', 'position', 'hiring_date', 'employment_status')
    search_fields = ('hr_code', 'name', 'arabic_name', 'cost_center', 'project', 'department')
    list_filter = ('sector', 'department', 'employment_status')

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and 'hr_code' not in base:
            # Correcting HR codes via the site updates linked assets and is audited as one operation.
            base.append('hr_code')
        return tuple(base)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = 'EMPLOYEE_EDIT' if change else 'EMPLOYEE_CREATE'
        log_event(request.user, action, request, f"{'Updated' if change else 'Created'} employee HR Code={obj.hr_code}, name={obj.name}")

    def delete_model(self, request, obj):
        hr_code, name = obj.hr_code, obj.name
        super().delete_model(request, obj)
        log_event(request.user, 'EMPLOYEE_DELETE', request, f'Deleted employee HR Code={hr_code}, name={name}')

    def delete_queryset(self, request, queryset):
        employees = list(queryset.values_list('hr_code', 'name'))
        super().delete_queryset(request, queryset)
        summary = '; '.join(f'{code} - {name}' for code, name in employees[:100])
        log_event(request.user, 'EMPLOYEE_DELETE', request, f'Deleted employees via Django admin: {summary}')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'asset_type', 'hr_code', 'employee_name', 'project', 'asset_status', 'source_sheet')
    search_fields = ('serial_number', 'hr_code', 'employee_name', 'computer_name_new', 'computer_name', 'model')
    list_filter = ('asset_type', 'asset_status', 'source_sheet', 'project')

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj:
            for field in ('hr_code', 'asset_status', 'scrap_date', 'scrap_number'):
                if field not in base:
                    base.append(field)
        return tuple(base)

    def has_add_permission(self, request):
        # Use the application form so the initial asset state is captured in history.
        return False

    def has_delete_permission(self, request, obj=None):
        # Assets are retired through the scrap workflow to preserve a custody trail.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = 'ASSET_EDIT' if change else 'ASSET_CREATE'
        log_event(request.user, action, request, f"{'Updated' if change else 'Created'} asset id={obj.pk}, serial={obj.serial_number}")


@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    list_display = ('effective_date', 'asset', 'event_type', 'from_hr_code', 'from_employee_name', 'to_hr_code', 'to_employee_name', 'created_by')
    search_fields = ('asset__serial_number', 'asset__computer_name_new', 'from_hr_code', 'from_employee_name', 'to_hr_code', 'to_employee_name', 'reason', 'reference_number')
    list_filter = ('event_type', 'effective_date', 'source_sheet')
    date_hierarchy = 'effective_date'
    readonly_fields = tuple(field.name for field in AssetMovement._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ('visit_date', 'project', 'technician_name', 'status', 'created_by', 'created_at')
    search_fields = ('project', 'technician_name', 'notes')
    list_filter = ('status', 'visit_date', 'project')
    readonly_fields = tuple(field.name for field in SiteVisit._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteInspection)
class SiteInspectionAdmin(admin.ModelAdmin):
    list_display = ('visit', 'serial_number_snapshot', 'type_snapshot', 'user_name', 'status', 'is_additional', 'inspected_at')
    search_fields = ('serial_number_snapshot', 'computer_name_snapshot', 'user_name', 'visit__project', 'auto_comments')
    list_filter = ('status', 'is_additional', 'visit__project', 'visit__visit_date')
    readonly_fields = tuple(field.name for field in SiteInspection._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
