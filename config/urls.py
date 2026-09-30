from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from devices.views import dashboard
from accounts.views import logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/', include('accounts.urls')),
    path('devices/', include('devices.urls')),
    path('audit/', include('audit.urls')),
]
