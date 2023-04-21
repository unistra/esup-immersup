from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from immersionlyceens.apps.core.models import (
    BachelorMention, GeneralBachelorTeaching, GeneralSettings, HighSchool, HighSchoolLevel,
    ImmersionUser, Period, PostBachelorLevel, StudentLevel,
)

from .models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordQuota, HighSchoolStudentRecordDocument,
    StudentRecord, StudentRecordQuota, VisitorRecord, VisitorRecordDocument,
    VisitorRecordQuota
)


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

    def clean(self):
        cleaned_data = super().clean()

        # Add prefix to search in database
        if not self.profile or self.profile in ["vis"]:
            login = cleaned_data.get('login')
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

    def clean(self):
        cleaned_data = super().clean()

        cleaned_data["email"] = cleaned_data.get('email', '').strip().lower()
        cleaned_data["email2"] = cleaned_data.get('email2', '').strip().lower()

        if not all([cleaned_data.get('email'), cleaned_data.get('email2'),
                cleaned_data.get('email') == cleaned_data.get('email2')]):
            self.add_error('email', _("Emails do not match"))
            self.add_error('email2', _("Emails do not match"))

        if cleaned_data.get("email"):
            if ImmersionUser.objects.filter(email__iexact=cleaned_data["email"]).exists():
                self.add_error('email', _("An account already exists with this email address"))
            else:
                username = cleaned_data["email"]

                # Shouldn't get there if the email unicity test fails
                if ImmersionUser.objects.filter(username__iexact=username).exists():
                    raise forms.ValidationError(_("Error : duplicated account detected"))

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

        email = cleaned_data.get("email", "").strip().lower()

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


class HighSchoolStudentRecordQuotaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["record"].widget = forms.HiddenInput()
        self.fields["period"].widget = forms.HiddenInput()

        if self.instance and hasattr(self.instance, "period"):
            self.period_label = '%s' % self.instance.period

            # Do not allow a lower quota value
            self.fields['allowed_immersions'].widget.attrs['min'] = self.instance.allowed_immersions

    class Meta:
        model = HighSchoolStudentRecordQuota
        fields = ('record', 'period', 'allowed_immersions', 'id', )


class StudentRecordQuotaForm(HighSchoolStudentRecordQuotaForm):
    """
    Same form as HighSchoolStudentRecordQuotaForm but for Students
    """
    class Meta:
        model = StudentRecordQuota
        fields = ('record', 'period', 'allowed_immersions', 'id', )


class VisitorRecordQuotaForm(HighSchoolStudentRecordQuotaForm):
    """
    Same form as HighSchoolStudentRecordQuotaForm but for Visitors
    """
    class Meta:
        model = VisitorRecordQuota
        fields = ('record', 'period', 'allowed_immersions', 'id', )


class HighSchoolStudentRecordDocumentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        self.attestation_label = None
        self.attestation_template = None
        self.can_renew = True

        self.renew_document = ""

        self.fields["record"].widget = forms.HiddenInput()
        self.fields["attestation"].widget = forms.HiddenInput()
        self.fields["document"].widget.attrs["class"] = "form-control-file"

        try:
            attestation_resend_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")
        except Exception as e:
            # display error only for managers
            attestation_resend_delay = 0 # good default value ?
            if not self.request.user.is_high_school_student() and not self.request.user.is_visitor():
                messages.error(
                    request,
                    _("ATTESTATION_DOCUMENT_DEPOSIT_DELAY setting is missing, please check your configuration.")
                )

        if self.instance and hasattr(self.instance, "attestation"):
            self.validity_required = False
            self.attestation_label = '%s' % self.instance.attestation
            self.attestation_template = self.instance.attestation.template

            self.fields["document"].required = self.instance.mandatory

            # Lock document field if the record has been validated and (now() < (validity_date - delay))
            if self.instance.validity_date is not None:
                self.can_renew = self.instance.requires_validity_date and \
                        timezone.localdate() > (self.instance.validity_date - timedelta(days=attestation_resend_delay))

                lock_file_conditions = [
                    self.request.user.is_high_school_student() or self.request.user.is_visitor(),
                    self.instance.record.validation == 2 and (
                        not self.instance.requires_validity_date or not self.can_renew
                    )
                ]

                if all(lock_file_conditions):
                    self.fields["document"].disabled = True

                if self.can_renew:
                    self.renew_document = _("Please renew this attestation")


            # Validity date is only required for managers
            conditions = [
                not self.request.user.is_high_school_student(),
                not self.request.user.is_visitor(),
                self.instance.requires_validity_date
            ]

            if all(conditions):
                self.validity_required = True
                self.fields["validity_date"].required = True
            else:
                self.fields["validity_date"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        # Check if the user can post a new document
        conditions = [
            self.instance and self.instance.record.validation == self.instance.record.STATUSES["VALIDATED"],
            self.has_changed(),
            "document" in self.changed_data,
            not self.can_renew,
        ]

        if all(conditions):
            self.add_error("document", _("You are not allowed to send a new file yet"))
            cleaned_data["validity_date"] = self.instance.validity_date

        return cleaned_data

    class Meta:
        model = HighSchoolStudentRecordDocument
        fields = ('id', 'record', 'attestation', 'document', 'validity_date', )

        widgets = {
            'validity_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('validity_date',)


class VisitorRecordDocumentForm(HighSchoolStudentRecordDocumentForm):
    """
    Reuse HighSchoolStudentRecordDocumentForm
    """
    class Meta:
        model = VisitorRecordDocument
        fields = ('id', 'record', 'attestation', 'document', 'validity_date', )


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

        # HighSchool choices : depends on conventions general settings:
        self.fields["highschool"].queryset = HighSchool.agreed.order_by('city', 'label')

        self.fields['professional_bachelor_mention'].widget.attrs['size'] = 80
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
        excludes = ['visible_immersion_registrations', 'visible_email', 'general_bachelor_teachings', 'birth_date',
            'allow_high_school_consultation'
        ]
        for field in self.fields:
            if field not in excludes:
                self.fields[field].widget.attrs['class'] = 'form-control'


    def clean(self):
        cleaned_data = super().clean()

        level = cleaned_data['level']
        bachelor_type = cleaned_data['bachelor_type']
        general_bachelor_teachings = cleaned_data.get('general_bachelor_teachings', '')
        technological_bachelor_mention = cleaned_data.get('technological_bachelor_mention', '')
        professional_bachelor_mention = cleaned_data.get('professional_bachelor_mention', '')
        origin_bachelor_type = cleaned_data['origin_bachelor_type']

        need_bachelor_speciality = HighSchoolLevel.objects \
            .filter(active=True, requires_bachelor_speciality=True)

        post_bachelor_levels = HighSchoolLevel.objects \
            .filter(active=True, is_post_bachelor=True)

        if level in need_bachelor_speciality:
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
        elif level in post_bachelor_levels:
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
                  'allow_high_school_consultation']

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

        valid_users = [
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ]

    class Meta:
        model = StudentRecord
        fields = ['birth_date', 'phone', 'uai_code', 'level', 'origin_bachelor_type', 'current_diploma',
                  'student']
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
        "birth_date", "motivation",
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

        fields: List[str] = ["phone", "motivation"]

        for field_name in fields:
            self.fields[field_name].widget.attrs["class"] = 'form-control'

        is_hs_manager_or_master: bool = self.has_change_permission()
        self.fields["visitor"].widget = forms.HiddenInput()

        if self.instance and self.instance.validation == 2:
            for field in self.validation_disabled_fields:
                self.fields[field].disabled = True

        if is_hs_manager_or_master:
            self.fields["birth_date"].disabled = False


    class Meta:
        model = VisitorRecord
        fields = ['id', 'birth_date', 'phone', 'visitor', 'motivation']

        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

        localized_fields = ('birth_date',)
