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

        self.fields["student"].widget = forms.HiddenInput()

        if not self.request or not self.request.user.is_scuio_ip_manager():
            for field in ('allowed_global_registrations', 'allowed_first_semester_registrations' ,
                'allowed_second_semester_registrations'):
                self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        level = cleaned_data['level']
        bachelor_type = cleaned_data['bachelor_type']
        general_bachelor_teachings = cleaned_data['general_bachelor_teachings']
        technological_bachelor_mention = cleaned_data['technological_bachelor_mention']
        professional_bachelor_mention = cleaned_data['professional_bachelor_mention']
        origin_bachelor_type = cleaned_data['origin_bachelor_type']

        if level in [1, 2]:
            if bachelor_type == 1:
                if not general_bachelor_teachings:
                    raise forms.ValidationError(
                        _("Please choose one or more bachelor teachings"))
            elif bachelor_type == 2:
                if not technological_bachelor_mention:
                    raise forms.ValidationError(
                        _("Please choose a mention for your technological bachelor"))
            elif bachelor_type == 3:
                if not professional_bachelor_mention:
                    raise forms.ValidationError(
                        _("Please enter a mention for your professional bachelor"))
        elif level == 3:
            if not origin_bachelor_type:
                raise forms.ValidationError(
                    _("Please choose your origin bachelor type"))

    class Meta:
        model = HighSchoolStudentRecord
        fields = ['civility', 'birth_date', 'phone', 'highschool', 'level', 'class_name',
                  'bachelor_type', 'general_bachelor_teachings', 'technological_bachelor_mention',
                  'professional_bachelor_mention', 'post_bachelor_level', 'origin_bachelor_type',
                  'current_diploma', 'visible_immersion_registrations', 'visible_email',
                  'allowed_global_registrations', 'allowed_first_semester_registrations',
                  'allowed_second_semester_registrations', 'student']

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker'}),
        }

        localized_fields = ('birth_date',)