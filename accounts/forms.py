from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User

class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active')

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'role', 'is_active')

class SIACPasswordChangeForm(PasswordChangeForm):
    pass
