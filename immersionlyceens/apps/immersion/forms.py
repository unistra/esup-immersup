from typing import List, Tuple, Any, Dict, Optional

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate

from immersionlyceens.apps.core.models import (
    ImmersionUser, HighSchool, GeneralBachelorTeaching, BachelorMention, HighSchoolLevel, PostBachelorLevel,
    StudentLevel, Calendar
)
from .models import HighSchoolStudentRecord, StudentRecord, VisitorRecord

class LoginForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)

        self.fields["login"] = forms.CharField(label=_("Login"), max_length=100, required=True)

        self.fields["password"]  = forms.CharField(
            label=_("Password"), max_length=100,
            widget=forms.PasswordInput(),
            required = True
        )

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

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
        if not self.profile:
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

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

        # self.email2.widget.attrs['class'] = 'form-control'


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


class PersonForm(forms.ModelForm):
    required_fields: Tuple[str, ...] = ("last_name", "first_name")

    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        for field_name in self.required_fields:
            self.fields[field_name].required = True

        self.fields["email"].help_text = _(
            "Warning : changing the email will require an account reactivation")

        for field_name in self.fields:
            self.fields[field_name].widget.attrs["class"] = "form-control"

    def clean(self) -> Dict[str, Any]:
        cleaned_data: Dict[str, Any] = super().clean()

        email: str = cleaned_data.get("email", "").strip().lower()
        if ImmersionUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(
                _("Error : an account already exists with this email address"))
        cleaned_data["email"] = email
        return cleaned_data

    class Meta:
        model = ImmersionUser
        fields = ("last_name", "first_name", "email", "id",)


class VisitorForm(PersonForm):
    required_fields: Tuple[str, ...] = ("last_name", "first_name", "email",)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance:
            record: Optional[VisitorRecordForm] = self.instance.get_visitor_record()
            if record and record.validation == 2:
                for field_name in ("first_name", "last_name"):
                    self.fields[field_name].disabled = True


    class Meta:
        model = ImmersionUser
        fields = ("last_name", "first_name", "email", "id",)


class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.fields["last_name"].required = True
        self.fields["first_name"].required = True

        self.fields["email"].help_text = _(
            "Warning : changing the email will require an account reactivation")

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email").strip().lower()

        """ MOVED IN VIEW
        if email != self.instance.email:
            self.request.user.set_validation_string()
            try:
                msg = self.request.user.send_message(self.request, 'CPT_MIN_CHANGE_MAIL')
            except Exception as e:
                logger.exception("Cannot send 'change mail' message : %s", e)
        """
        cleaned_data['email'] = email
        return cleaned_data

    class Meta:
        model = ImmersionUser
        fields = ['last_name', 'first_name', 'email']


class HighSchoolStudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.fields["last_name"].required = True
        self.fields["first_name"].required = True
        self.fields["email"].required = True
        
        self.fields["email"].help_text = _(
            "Warning : changing the email will require an account reactivation")

        # CSS
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

        if self.instance:
            record = self.instance.get_high_school_student_record()

            if record and record.validation == 2:
                self.fields["last_name"].disabled = True
                self.fields["first_name"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get('email', '').strip().lower()

        if ImmersionUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(
                _("Error : an account already exists with this email address"))

        """ MOVED IN VIEW
        if email != self.instance.email:
            self.request.user.set_validation_string()
            try:
                msg = self.request.user.send_message(self.request, 'CPT_MIN_CHANGE_MAIL')
            except Exception as e:
                logger.exception("Cannot send 'change mail' message : %s", e)
        """

        cleaned_data['email'] = email

        return cleaned_data

    class Meta:
        model = ImmersionUser
        fields = ['last_name', 'first_name', 'email']


class NewPassForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        # self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    class Meta:
        model = ImmersionUser
        fields = ('password1', 'password2')


class HighSchoolStudentRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        valid_groups = [
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ]

        is_hs_manager_or_master: bool = any(valid_groups)

        self.fields["student"].widget = forms.HiddenInput()
        self.fields["highschool"].queryset = HighSchool.agreed.order_by('city','label')
        # self.fields['professional_bachelor_mention'].widget.attrs['class'] = 'form-control'
        self.fields['professional_bachelor_mention'].widget.attrs['size'] = 80
        # self.fields['current_diploma'].widget.attrs['class'] = 'form-control'
        self.fields['current_diploma'].widget.attrs['size'] = 80
        self.fields['technological_bachelor_mention'].queryset = BachelorMention.objects.filter(active=True)
        self.fields['general_bachelor_teachings'] = forms.ModelMultipleChoiceField(
            queryset=GeneralBachelorTeaching.objects.filter(active=True).order_by('label'),
            widget=forms.CheckboxSelectMultiple           
        )
        self.fields['general_bachelor_teachings'].required = False
        self.fields['level'].queryset = HighSchoolLevel.objects.filter(active=True).order_by('order')
        self.fields['post_bachelor_level'].queryset = PostBachelorLevel.objects.filter(active=True).order_by('order')

        # CSS
        excludes = ['visible_immersion_registrations', 'visible_email', 'general_bachelor_teachings', 'birth_date']
        for field in self.fields:
            if field not in excludes:
                self.fields[field].widget.attrs['class'] = 'form-control'

        if not self.request or not is_hs_manager_or_master:
            del self.fields['allowed_global_registrations']
            del self.fields['allowed_first_semester_registrations']
            del self.fields['allowed_second_semester_registrations']

            if self.instance and self.instance.validation == 2:
                for field in ["highschool", "birth_date", "class_name", "level"]:
                    self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        level = cleaned_data['level']
        bachelor_type = cleaned_data['bachelor_type']
        general_bachelor_teachings = cleaned_data.get('general_bachelor_teachings', '')
        technological_bachelor_mention = cleaned_data.get('technological_bachelor_mention', '')
        professional_bachelor_mention = cleaned_data.get('professional_bachelor_mention', '')
        origin_bachelor_type = cleaned_data['origin_bachelor_type']

        if level in [2, 3]:
            if bachelor_type == 1:
                cleaned_data['technological_bachelor_mention'] = None
                cleaned_data['professional_bachelor_mention'] = ""
                if not general_bachelor_teachings:
                    raise forms.ValidationError(
                        _("Please choose one or more bachelor teachings"))
            elif bachelor_type == 2:
                cleaned_data['general_bachelor_teachings'] = []
                cleaned_data['professional_bachelor_mention'] = ""
                if not technological_bachelor_mention:
                    raise forms.ValidationError(
                        _("Please choose a mention for your technological bachelor"))
            elif bachelor_type == 3:
                cleaned_data['general_bachelor_teachings'] = []
                cleaned_data['technological_bachelor_mention'] = None
                if not professional_bachelor_mention:
                    raise forms.ValidationError(
                        _("Please enter a mention for your professional bachelor"))
        elif level == 3:
            cleaned_data['general_bachelor_teachings'] = []
            cleaned_data['technological_bachelor_mention'] = None
            cleaned_data['professional_bachelor_mention'] = ""
            if not origin_bachelor_type:
                raise forms.ValidationError(
                    _("Please choose your origin bachelor type"))

        return cleaned_data

    class Meta:
        model = HighSchoolStudentRecord
        fields = ['birth_date', 'phone', 'highschool', 'level', 'class_name',
                  'bachelor_type', 'general_bachelor_teachings', 'technological_bachelor_mention',
                  'professional_bachelor_mention', 'post_bachelor_level', 'origin_bachelor_type',
                  'current_diploma', 'visible_immersion_registrations', 'visible_email', 'student',
                  'allowed_global_registrations', 'allowed_first_semester_registrations',
                  'allowed_second_semester_registrations']

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('birth_date',)


class StudentRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.fields["student"].widget = forms.HiddenInput()
        self.fields["uai_code"].disabled = True
        self.fields['current_diploma'].widget.attrs['class'] = 'form-control'
        self.fields['current_diploma'].widget.attrs['size'] = 80

        self.fields['level'].queryset = StudentLevel.objects.filter(active=True).order_by('order')

        # CSS
        excludes = ['birth_date']
        for field in self.fields:
            if field not in excludes:
                self.fields[field].widget.attrs['class'] = 'form-control'

        if not self.request or not self.request.user.is_establishment_manager():
            del self.fields['allowed_global_registrations']
            del self.fields['allowed_first_semester_registrations']
            del self.fields['allowed_second_semester_registrations']

    class Meta:
        model = StudentRecord
        fields = ['birth_date', 'phone', 'uai_code', 'level',
                  'origin_bachelor_type', 'current_diploma', 'student',
                  'allowed_global_registrations', 'allowed_first_semester_registrations',
                  'allowed_second_semester_registrations']

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('birth_date',)


class HighSchoolStudentRecordManagerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].widget = forms.HiddenInput()
        self.fields['level'].widget.attrs['class'] = 'form-control'
        self.fields['class_name'].widget.attrs['class'] = 'form-control'

    class Meta:
        model = HighSchoolStudentRecord
        fields = ['birth_date', 'level', 'class_name', 'student']

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('birth_date',)


class VisitorRecordForm(forms.ModelForm):

    validation_disabled_fields: Tuple[str, ...] = (
        "birth_date", "motivation", "identity_document",
        "civil_liability_insurance",
    )

    def has_change_permission(self):
        return any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ])

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        fields: List[str] = [
            "phone", "allowed_first_semester_registrations",
            "allowed_second_semester_registrations", "allowed_global_registrations",
            "motivation"
        ]
        for field_name in fields:
            self.fields[field_name].widget.attrs["class"] = 'form-control'
        for field_name in ["identity_document", "civil_liability_insurance"]:
            self.fields[field_name].widget.attrs["class"] = "form-control-file"

        is_hs_manager_or_master: bool = self.has_change_permission()
        self.fields["visitor"].widget = forms.HiddenInput()

        if self.instance and self.instance.validation == 2:
            for field in self.validation_disabled_fields:
                self.fields[field].disabled = True

        if is_hs_manager_or_master:
            self.fields["birth_date"].disabled = False
        else:
            for field_name in (
                   "allowed_first_semester_registrations",
                   "allowed_second_semester_registrations",
                   "allowed_global_registrations"):
                self.fields[field_name].disabled = True

    class Meta:
        model = VisitorRecord
        fields = ['id',
            'birth_date', 'phone', 'visitor',
            'motivation', 'identity_document', 'civil_liability_insurance',
            'allowed_first_semester_registrations', 'allowed_second_semester_registrations',
            'allowed_global_registrations',
        ]

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('birth_date',)
