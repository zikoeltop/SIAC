from django.urls import path
from .views import ChangePasswordView, user_list, user_create, user_edit, user_delete, user_reset_password
urlpatterns = [
    path('password/change/', ChangePasswordView.as_view(), name='password_change'),
    path('users/', user_list, name='user_list'),
    path('users/add/', user_create, name='user_create'),
    path('users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),
    path('users/<int:pk>/reset-password/', user_reset_password, name='user_reset_password'),
]
