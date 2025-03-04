from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.views.decorators.csrf import csrf_protect
from .models import User, Customer, Employee

from .mixins import AuthenticatedMixin
from ..core.mixins import IsSuperUserMixin
from ..utils.character_generator import random_character_generator
from ..utils.sms_sender import send_single_sms

from .forms import (
    UserLoginForm,
    RegisterForm,
    AccountUpdateForm,
    AccountPasswordChangeForm,
    UserCreateForm,
    UserUpdateForm
)
from ...envs.common import SMS_SETTINGS


# Create your views here.


@login_required
def account_view(request):
    """
    The main account view
    """
    return render(request, 'registration/profile/profile_home.html')


class Login(AuthenticatedMixin, LoginView):
    """
    Customize Login form,
    customize redirect url.
    """
    authentication_form = UserLoginForm

    def get_success_url(self):
        return reverse('users:home')


class RegisterView(AuthenticatedMixin, CreateView):
    """
    The view for register a user.
    """
    model = User
    success_url = reverse_lazy('login')
    form_class = RegisterForm
    template_name = 'registration/register.html'


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    """
    The view for update account,
    if user authenticated can use this view.
    """

    def get_object(self, queryset=None):
        request = self.request
        return User.objects.get(pk=request.user.pk)

    template_name = 'registration/profile/profile_update.html'
    success_url = reverse_lazy('users:home')
    form_class = AccountUpdateForm


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    The view for change account password,
    if user authenticated can use this view.
    """
    success_url = reverse_lazy('users:home')
    template_name = 'registration/profile/profile_change_password.html'
    form_class = AccountPasswordChangeForm


class UserListView(IsSuperUserMixin, ListView):
    """
    The view return active users,
    only superuser can see this view.
    """

    def get_queryset(self):
        return User.objects.filter(is_active=True).order_by('-id')

    template_name = 'users/users_list.html'
    paginate_by = 12


class DeactivateUserListView(IsSuperUserMixin, ListView):
    """
    The view return deactivated users,
    only superuser can see this view.
    """

    def get_queryset(self):
        return User.objects.filter(is_active=False).order_by('-id')

    template_name = 'users/users_list.html'
    paginate_by = 12


@user_passes_test(lambda u: u.is_superuser)
def user_create_view(request):
    """
    The function-based view for create a new user,
    uses user_passes_test decorator.
    """
    create_form = UserCreateForm(
        data=request.POST or None,
        initial={
            'bio': 'لطفا بیوگرافی خودرا ویرایش کنید'
        }
    )

    password = random_character_generator(4)

    if request.method == "POST":
        if create_form.is_valid():
            username = create_form.cleaned_data.get('username')
            email = create_form.cleaned_data.get('email')
            first_name = create_form.cleaned_data.get('first_name')
            last_name = create_form.cleaned_data.get('last_name')
            bio = create_form.cleaned_data.get('bio')
            status = create_form.cleaned_data.get('status')
            phone_number = create_form.cleaned_data.get('phone_number')

            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                bio=bio
            )
            user.set_password(password)
            user.save()

            match status:
                case "staff":
                    user.is_staff = True
                    user.save()
                case "customer":
                    Customer.objects.create(account=user)
                case "employee":
                    Employee.objects.create(account=user)

            send_single_sms(
                message="کاربر جدید ایجاد شد \n"
                        f"نام کاربری: {user.username}\n"
                        f"رمز عبور: {password}\n"
                        f"ایمیل: {user.email}\n"
                        f"شماره تلفن: {user.phone_number}\n",
                receptor=SMS_SETTINGS['ADMIN_PHONE_NUMBER']
            )

            return redirect('users:users-list')

    context = {
        'default_password': password,
        'form': create_form
    }
    return render(request, 'users/users_create_update.html', context)


@user_passes_test(lambda u: u.is_superuser)
def user_update_view(request, pk, username):
    """
    The function-based view takes pk and username parameters,
    then return current user and update his.
    """
    user = get_object_or_404(User, pk=pk, username=username)
    employee = Employee.objects.filter(account=user)
    customer = Customer.objects.filter(account=user)
    user_status = 'superuser'

    if user.is_staff:
        user_status = 'staff'
    elif employee.exists():
        user_status = 'employee'
    elif customer.exists():
        user_status = 'customer'

    update_form = UserUpdateForm(
        data=request.POST or None,
        initial={
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': user.bio
        }
    )

    if request.method == "POST":
        if update_form.is_valid():
            user.username = update_form.cleaned_data.get('username')
            user.email = update_form.cleaned_data.get('email')
            user.first_name = update_form.cleaned_data.get('first_name')
            user.last_name = update_form.cleaned_data.get('last_name')
            user.bio = update_form.cleaned_data.get('bio')
            user.phone_number = update_form.cleaned_data.get('phone_number')
            status = update_form.cleaned_data.get('status')

            if user_status != status:
                if user.is_staff:
                    user.is_staff = False
                    user.save()
                elif employee.exists():
                    employee.delete()
                elif customer.exists():
                    customer.delete()

                match status:
                    case "staff":
                        user.is_staff = True
                        user.save()
                    case "customer":
                        Customer.objects.create(account=user)
                    case "employee":
                        Employee.objects.create(account=user)

            return redirect('users:users-list')

    context = {
        'form': update_form,
        'user': user
    }
    return render(request, 'users/users_create_update.html', context)


class UserDetailView(IsSuperUserMixin, DetailView):
    model = User
    template_name = 'users/users_detail.html'


@user_passes_test(lambda u: u.is_superuser)
@csrf_protect
def users_activate_deactivate_view(request):
    """
    The view takes pk parameter,
    if the current user is active it will deactivate it,
    if the current user is deactivate it will active it.
    """
    user_pk = request.GET.get('pk')
    user = User.objects.filter(pk=user_pk).first()
    if user:
        match user.is_active:
            case True:
                user.is_active = False
            case False:
                user.is_active = True
        user.save()
        return JsonResponse(status=204, data={'message': 'deleted'})
    else:
        return JsonResponse(status=404, data={'message': 'user not found'})
