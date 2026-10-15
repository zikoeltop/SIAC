from django.conf import settings
from django.db import models


class Employee(models.Model):
    """IT-relevant employee reference data (intentionally excludes sensitive HR fields)."""
    hr_code = models.CharField(max_length=80, unique=True, db_index=True, verbose_name='HR Code')
    name = models.CharField(max_length=255, verbose_name='Employee Name')
    arabic_name = models.CharField(max_length=255, blank=True, verbose_name='Arabic Name')
    company = models.CharField(max_length=255, blank=True, verbose_name='Company')
    project = models.CharField(max_length=255, blank=True, verbose_name='Project / Site')
    sector = models.CharField(max_length=255, blank=True, verbose_name='Sector')
    department = models.CharField(max_length=255, blank=True, verbose_name='Department')
    section = models.CharField(max_length=255, blank=True, verbose_name='Section')
    unit = models.CharField(max_length=255, blank=True, verbose_name='Unit')
    office = models.CharField(max_length=255, blank=True, verbose_name='Office')
    team = models.CharField(max_length=255, blank=True, verbose_name='Team')
    position = models.CharField(max_length=255, blank=True, verbose_name='Position')
    employment_status = models.CharField(max_length=80, blank=True, verbose_name='Employment Status')
    termination_date = models.DateField(null=True, blank=True, verbose_name='Termination Date')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'hr_code']
        indexes = [models.Index(fields=['name'], name='employee_name_idx')]

    def __str__(self):
        return f'{self.hr_code} - {self.name}'


class Asset(models.Model):
    class Types(models.TextChoices):
        COMPUTER = 'computer', 'Computers'
        PRINTER = 'printer', 'Printers'
        MONITOR = 'monitor', 'Monitors'
        GSTAR = 'gstar_license', 'GStar CAD licenses'
        NEW_2026 = 'new_2026', 'New hires 2026'
        REQUEST_2025 = 'request_2025', 'Requests 2025'
        SCRAP = 'scraped', 'Scrapped assets'
        OTHER = 'other', 'Other assets'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active / Custody'
        PENDING = 'pending', 'Pending'
        SCRAPPED = 'scrapped', 'Scrapped'
        ARCHIVED = 'archived', 'Archived'

    employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='assets', verbose_name='Matched Employee')
    hr_code = models.CharField(max_length=80, blank=True, db_index=True, verbose_name='HR Code')
    employee_name = models.CharField(max_length=255, blank=True, verbose_name='Employee Name (source)')
    asset_type = models.CharField(max_length=30, choices=Types.choices, default=Types.COMPUTER,
                                  db_index=True, verbose_name='Asset Type')
    asset_status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE,
                                    db_index=True, verbose_name='Asset Status')
    source_sheet = models.CharField(max_length=64, default='manual', db_index=True, verbose_name='Source Sheet')
    source_row = models.PositiveIntegerField(null=True, blank=True, verbose_name='Source Row')

    company = models.CharField(max_length=255, blank=True)
    project = models.CharField(max_length=255, blank=True, db_index=True)
    sector = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    computer_name_new = models.CharField(max_length=255, blank=True, verbose_name='Computer Name New')
    computer_name = models.CharField(max_length=255, blank=True, verbose_name='Computer Name')
    item_type = models.CharField(max_length=255, blank=True, verbose_name='Item / Type')
    brand = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    serial_number = models.CharField(max_length=180, blank=True, db_index=True, verbose_name='Serial Number')
    asset_tag = models.CharField(max_length=180, blank=True, verbose_name='Asset Number')
    manufacturing_year = models.CharField(max_length=40, blank=True, verbose_name='Manufacturing Year')
    processor = models.CharField(max_length=255, blank=True)
    ram = models.CharField(max_length=120, blank=True)
    storage = models.CharField(max_length=255, blank=True, verbose_name='Storage / HDD')
    email = models.EmailField(max_length=254, blank=True)
    toner_code = models.CharField(max_length=180, blank=True, verbose_name='Toner Code')
    license_version = models.CharField(max_length=180, blank=True, verbose_name='License Version')
    license_activated = models.CharField(max_length=80, blank=True, verbose_name='License Activated')
    purchase_date = models.DateField(null=True, blank=True)
    scrap_date = models.CharField(max_length=80, blank=True, verbose_name='Scrap Date')
    scrap_number = models.CharField(max_length=120, blank=True, verbose_name='Scrap Number')
    notes = models.TextField(blank=True)
    software_licenses = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['asset_type', 'employee_name', 'serial_number']
        constraints = [
            models.UniqueConstraint(
                fields=['source_sheet', 'source_row'],
                name='uniq_asset_source_row',
            )
        ]
        indexes = [
            models.Index(fields=['hr_code', 'asset_status'], name='asset_hr_status_idx'),
            models.Index(fields=['asset_type', 'asset_status'], name='asset_type_status_idx'),
        ]

    def save(self, *args, **kwargs):
        self.hr_code = str(self.hr_code or '').strip()
        self.serial_number = str(self.serial_number or '').strip()
        if self.hr_code:
            matched = Employee.objects.filter(hr_code__iexact=self.hr_code).first()
            self.employee = matched
            if matched:
                if not self.employee_name:
                    self.employee_name = matched.name
                if not self.project:
                    self.project = matched.project
                if not self.sector:
                    self.sector = matched.sector
                if not self.department:
                    self.department = matched.department
        else:
            self.employee = None
        super().save(*args, **kwargs)

    @property
    def included_in_custody(self):
        return self.asset_status == self.Status.ACTIVE and self.asset_type != self.Types.SCRAP

    @property
    def display_employee_name(self):
        return self.employee.name if self.employee_id else self.employee_name or '-'

    @property
    def display_type(self):
        return self.get_asset_type_display()

    def __str__(self):
        return f'{self.serial_number or self.model or self.item_type or self.get_asset_type_display()} ({self.hr_code or "unassigned"})'


class AssetMovement(models.Model):
    """Append-only audit trail of custody/stock/status changes for each asset record."""
    class EventTypes(models.TextChoices):
        SOURCE_STATE = 'source_state', 'الحالة المسجلة في الملف المرجعي'
        ADDED_TO_STOCK = 'added_to_stock', 'إضافة إلى المخزون'
        ASSIGNED = 'assigned', 'تسليم لموظف'
        TRANSFERRED = 'transferred', 'نقل عهدة بين موظفين'
        RETURNED = 'returned', 'إرجاع إلى المخزون'
        SCRAPPED = 'scrapped', 'تخريد'
        STATUS_CHANGED = 'status_changed', 'تغيير حالة الأصل'

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='movements', verbose_name='الأصل')
    event_type = models.CharField(max_length=32, choices=EventTypes.choices, db_index=True)
    effective_date = models.DateField(null=True, blank=True, db_index=True, verbose_name='تاريخ الحركة')
    from_employee = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='asset_movements_from', verbose_name='الموظف السابق',
    )
    to_employee = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='asset_movements_to', verbose_name='الموظف الجديد',
    )
    from_hr_code = models.CharField(max_length=80, blank=True, db_index=True)
    from_employee_name = models.CharField(max_length=255, blank=True)
    to_hr_code = models.CharField(max_length=80, blank=True, db_index=True)
    to_employee_name = models.CharField(max_length=255, blank=True)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    reason = models.CharField(max_length=255, blank=True, verbose_name='سبب الحركة')
    reference_number = models.CharField(max_length=120, blank=True, verbose_name='رقم المستند')
    notes = models.TextField(blank=True)
    source_sheet = models.CharField(max_length=64, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    # Stable key makes source-baseline events idempotent when the workbook is re-imported.
    source_event_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='asset_movement_events',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['effective_date', 'created_at', 'id']
        indexes = [
            models.Index(fields=['asset', 'effective_date'], name='move_asset_date_idx'),
            models.Index(fields=['from_hr_code', 'effective_date'], name='move_from_hr_date_idx'),
            models.Index(fields=['to_hr_code', 'effective_date'], name='move_to_hr_date_idx'),
        ]

    @property
    def from_display(self):
        return self.from_employee_name or self.from_hr_code or 'المخزون'

    @property
    def to_display(self):
        return self.to_employee_name or self.to_hr_code or ('التخريد' if self.event_type == self.EventTypes.SCRAPPED else 'المخزون')

    @property
    def from_status_display(self):
        labels = dict(Asset.Status.choices)
        return labels.get(self.from_status, self.from_status or '-')

    @property
    def to_status_display(self):
        labels = dict(Asset.Status.choices)
        return labels.get(self.to_status, self.to_status or '-')

    def __str__(self):
        return f'{self.asset} - {self.get_event_type_display()}'


# Legacy computer-only inventory model is retained for compatibility with the earlier report/import flow.
class Device(models.Model):
    serial_number = models.CharField(max_length=150, unique=True, db_index=True)
    user_name = models.CharField(max_length=255, blank=True)
    project = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    processor = models.CharField(max_length=500, blank=True)
    ram = models.CharField(max_length=255, blank=True)
    computer_name = models.CharField(max_length=255, blank=True)
    hdd = models.CharField(max_length=500, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.serial_number


class DeviceImport(models.Model):
    file = models.FileField(upload_to='excel/')
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    rows_imported = models.PositiveIntegerField(default=0)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']


class PendingExcelImport(models.Model):
    file = models.FileField(upload_to='excel/pending/')
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    preview_rows = models.JSONField(default=list, blank=True)
    columns = models.JSONField(default=list, blank=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

class PendingInventoryImport(models.Model):
    file = models.FileField(upload_to='excel/inventory-pending/')
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    summary = models.JSONField(default=dict, blank=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

