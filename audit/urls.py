from django.urls import path
from .views import log_list
urlpatterns=[path('', log_list, name='audit_logs')]
