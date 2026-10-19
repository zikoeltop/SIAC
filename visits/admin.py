from django.contrib import admin
from .models import Visit, VisitItem

class VisitItemInline(admin.TabularInline):
    model = VisitItem
    extra = 0

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("project", "visit_date", "technician_name", "status", "created_by")
    list_filter = ("status", "visit_date", "project")
    search_fields = ("project", "technician_name", "items__serial_number", "items__computer_name")
    inlines = [VisitItemInline]

admin.site.register(VisitItem)
