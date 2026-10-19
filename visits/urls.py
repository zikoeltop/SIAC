from django.urls import path
from . import views

urlpatterns = [
    path("", views.visit_list, name="visit_list"),
    path("new/", views.visit_create, name="visit_create"),
    path("dashboard/", views.project_dashboard, name="project_dashboard"),
    path("<int:pk>/", views.visit_detail, name="visit_detail"),
    path("<int:pk>/export.xlsx", views.visit_export, name="visit_export"),
    path("<int:pk>/items/<int:item_pk>/edit/", views.visit_item_edit, name="visit_item_edit"),
    path("lookup-device/", views.lookup_device, name="visit_device_lookup"),
]
