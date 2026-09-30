from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import User

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin_role:
            messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه الصفحة.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
