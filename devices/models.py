from django.db import models

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
