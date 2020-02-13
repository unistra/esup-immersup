from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate

from immersionlyceens.apps.core.models import ImmersionUser
from .models import HighSchoolStudentRecord

class LoginForm(forms.Form):
    login = forms.CharField(label=_("Login"), max_length=100, required=True)

    password = forms.CharField(
        label=_("Password"), max_length=100,
        widget=forms.PasswordInput(),
        required = True
    )

    # TODO : Django's authentication system
    # (does not work, needs authentication backend attribute
    """
    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_user(self):
        cleaned_data = super().clean()
        login = settings.USERNAME_PREFIX + cleaned_data.get('login')
        password = cleaned_data.get('password')

        user = authenticate(username=login, password=password)

        return user
    """

    def clean(self):
        cleaned_data = super().clean()

        # Add prefix to search in database
        login = settings.USERNAME_PREFIX + cleaned_data.get('login')
        cleaned_data['login'] = login

        return cleaned_data


class RegistrationForm(UserCreationForm):
    email2 = forms.EmailField(
        label=_("Email"), max_length=100,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def clean(self):
        cleaned_data = super().clean()

        if not all([cleaned_data.get('email'), cleaned_data.get('email2'),
                cleaned_data.get('email')==cleaned_data.get('email2')]):
            raise forms.ValidationError(
                _("Error : emails don't match"))

        if not all([cleaned_data.get('password1'), cleaned_data.get('password2'),
                cleaned_data.get('password1')==cleaned_data.get('password2')]):
            raise forms.ValidationError(
                _("Error : passwords don't match"))

        email = cleaned_data.get('email')

        if ImmersionUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Error : an account already exists with this email address"))

        username = settings.USERNAME_PREFIX + email

        # Shouldn't get there if the email unicity test fails
        if ImmersionUser.objects.filter(username=username).exists():
            raise forms.ValidationError(
                _("Error : duplicated account detected"))

        cleaned_data['username'] = username
        return cleaned_data


    class Meta:
        model = ImmersionUser
        fields = ('last_name', 'first_name', 'email', 'password1', 'password2')


class HighSchoolStudentRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    class meta:
        model = HighSchoolStudentRecord
