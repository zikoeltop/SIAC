from django.conf import settings
from django.db import models
from devices.models import Asset

class Visit(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        APPROVED = "approved", "معتمدة"
        CANCELLED = "cancelled", "ملغاة"

    project = models.CharField(max_length=255, db_index=True)
    visit_date = models.DateField()
    technician_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_visits")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_project_visits")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-visit_date", "-created_at"]

    def __str__(self):
        return f"{self.project} - {self.visit_date}"

class VisitItem(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="items")
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="inspection_rows")
    user_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=255, blank=True)
    serial_number = models.CharField(max_length=180, blank=True, db_index=True)
    computer_name = models.CharField(max_length=255, blank=True)
    monitor_model = models.CharField(max_length=255, blank=True)
    monitor_serial = models.CharField(max_length=180, blank=True)
    printer_model = models.CharField(max_length=255, blank=True)
    printer_serial = models.CharField(max_length=180, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["serial_number", "id"]

    def __str__(self):
        return f"{self.visit.project} / {self.serial_number}"
