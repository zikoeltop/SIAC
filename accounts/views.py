from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from audit.utils import log_event
from .decorators import admin_required
from .forms import UserCreateForm, UserEditForm, SIACPasswordChangeForm
from .models import User

@login_required
def logout_view(request):
    log_event(request.user, 'LOGOUT', request, 'User logged out')
    logout(request)
    return redirect('login')

class ChangePasswordView(PasswordChangeView):
    form_class = SIACPasswordChangeForm
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('dashboard')
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'تم تغيير كلمة المرور بنجاح.')
        log_event(self.request.user, 'PASSWORD_CHANGE', self.request, 'User changed own password')
        return response

@admin_required
def user_list(request):
    return render(request, 'accounts/user_list.html', {'users': User.objects.order_by('username')})

@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_event(request.user, 'USER_CREATE', request, f'Created user {user.username}')
        messages.success(request, f'تم إنشاء المستخدم {user.username}.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'إضافة مستخدم'})

@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_event(request.user, 'USER_EDIT', request, f'Edited user {user.username}')
        messages.success(request, 'تم حفظ بيانات المستخدم.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'تعديل المستخدم {user.username}'})

@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'لا يمكنك حذف حسابك الحالي.')
        return redirect('user_list')
    if request.method == 'POST':
        username = user.username
        user.delete()
        log_event(request.user, 'USER_DELETE', request, f'Deleted user {username}')
        messages.success(request, 'تم حذف المستخدم.')
    return redirect('user_list')

@admin_required
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        password = request.POST.get('new_password', '')
        if len(password) < 8:
            messages.error(request, 'كلمة المرور يجب أن تكون 8 أحرف/أرقام على الأقل.')
        else:
            user.set_password(password)
            user.save(update_fields=['password'])
            log_event(request.user, 'PASSWORD_RESET', request, f'Admin reset password for {user.username}')
            messages.success(request, f'تم تغيير كلمة مرور {user.username}.')
            return redirect('user_list')
    return render(request, 'accounts/password_reset.html', {'target_user': user})
