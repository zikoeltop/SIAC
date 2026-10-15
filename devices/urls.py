from django.urls import path
from .views import (
    asset_create, asset_edit, asset_list, dashboard, download_custody_report,
    download_report, employee_create, employee_edit, employee_list, excel_preview,
    inventory_export, inventory_import, inventory_import_preview, manage_excel, search_device,
)

urlpatterns = [
    path('search/', search_device, name='search_device'),
    path('custody-report/<str:hr_code>/', download_custody_report, name='download_custody_report'),
    path('report/<int:pk>/', download_report, name='download_report'),
    path('inventory/employees/', employee_list, name='employee_list'),
    path('inventory/employees/add/', employee_create, name='employee_create'),
    path('inventory/employees/<int:pk>/edit/', employee_edit, name='employee_edit'),
    path('inventory/assets/', asset_list, name='asset_list'),
    path('inventory/assets/add/', asset_create, name='asset_create'),
    path('inventory/assets/<int:pk>/edit/', asset_edit, name='asset_edit'),
    path('inventory/import/', inventory_import, name='inventory_import'),
    path('inventory/import/preview/<int:pk>/', inventory_import_preview, name='inventory_import_preview'),
    path('inventory/export.xlsx', inventory_export, name='inventory_export'),
    path('excel/', manage_excel, name='manage_excel'),
    path('excel/preview/<int:pk>/', excel_preview, name='excel_preview'),
]
