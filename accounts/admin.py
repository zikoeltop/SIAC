from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
@admin.register(User)
class SIACUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('SIAC', {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_active', 'last_login')
    list_filter = ('role', 'is_active')
