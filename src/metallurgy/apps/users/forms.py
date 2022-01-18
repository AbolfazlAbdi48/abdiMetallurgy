from django.contrib.auth.forms import AuthenticationForm, UsernameField

from django import forms


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    username = UsernameField(
        widget=forms.TextInput(
            attrs={'class': 'form-control form-control-solid h-auto py-7 px-6 rounded-lg',
                   'placeholder': 'نام کاربری'}
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-solid h-auto py-7 px-6 rounded-lg',
                'placeholder': 'کلمه عبور'
            }
        ))
