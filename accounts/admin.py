from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from audit.utils import log_event
from .models import User


@admin.register(User)
class SIACUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('SIAC', {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_active', 'last_login')
    list_filter = ('role', 'is_active')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = 'USER_EDIT' if change else 'USER_CREATE'
        log_event(request.user, action, request, f"{'Updated' if change else 'Created'} user {obj.username} via Django admin")

    def delete_model(self, request, obj):
        username = obj.username
        super().delete_model(request, obj)
        log_event(request.user, 'USER_DELETE', request, f'Deleted user {username} via Django admin')

    def delete_queryset(self, request, queryset):
        usernames = list(queryset.values_list('username', flat=True))
        super().delete_queryset(request, queryset)
        log_event(request.user, 'USER_DELETE', request, f'Deleted users via Django admin: {", ".join(usernames[:100])}')
