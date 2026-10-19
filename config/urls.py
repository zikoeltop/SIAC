from django.contrib import admin
from django.urls import path, include
from devices.views import dashboard
from accounts.views import logout_view, SIACLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('login/', SIACLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/', include('accounts.urls')),
    path('devices/', include('devices.urls')),
    path('audit/', include('audit.urls')),
    path('visits/', include('visits.urls')),
]
