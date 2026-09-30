from django.urls import path
from .views import search_device, download_report, manage_excel, excel_preview
urlpatterns = [
    path('search/', search_device, name='search_device'),
    path('report/<int:pk>/', download_report, name='download_report'),
    path('excel/', manage_excel, name='manage_excel'),
    path('excel/preview/<int:pk>/', excel_preview, name='excel_preview'),
]
