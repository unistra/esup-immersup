from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from ...libs.geoapi.utils import get_cities, get_zipcodes
from .models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus, CancelType, Component,
    CourseType, GeneralBachelorTeaching, HighSchool, Holiday, ImmersionUser, PublicType, Training,
    TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
    InformationText
)


class BachelorMentionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = BachelorMention
        fields = '__all__'


class CampusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Campus
        fields = '__all__'


class CancelTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = CancelType
        fields = '__all__'


class CourseTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = CourseType
        fields = '__all__'


class TrainingDomainForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = TrainingDomain
        fields = '__all__'


class TrainingSubdomainForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['training_domain'].queryset = self.fields['training_domain'].queryset.order_by(
            'label'
        )

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = TrainingSubdomain
        fields = '__all__'


class BuildingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['campus'].queryset = Campus.objects.order_by('label')

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Building
        fields = '__all__'


class TrainingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['training_subdomains'].queryset = (
            self.fields['training_subdomains']
            .queryset.filter(training_domain__active=True, active=True)
            .order_by('training_domain__label', 'label')
        )

        self.fields['components'].queryset = self.fields['components'].queryset.order_by(
            'code', 'label'
        )

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Training
        fields = '__all__'


class ComponentForm(forms.ModelForm):
    """
    Component form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Disable code field if it already exists
        if self.initial:
            self.fields["code"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Component
        fields = '__all__'


class GeneralBachelorTeachingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = GeneralBachelorTeaching
        fields = '__all__'


class PublicTypeForm(forms.ModelForm):
    """
    public type form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = PublicType
        fields = '__all__'


class UniversityYearForm(forms.ModelForm):
    """
    University Year form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_start_date = cleaned_data.get('registration_start_date')
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        if start_date and start_date <= datetime.today().date():
            raise forms.ValidationError(_("Start date can't be today or earlier"))
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(_("Start date greater than end date"))
        if registration_start_date and end_date and registration_start_date >= end_date:
            raise forms.ValidationError(_("Start of registration date greater than end date"))

        return cleaned_data

    class Meta:
        model = UniversityYear
        fields = '__all__'


class HolidayForm(forms.ModelForm):
    """
    Holiday form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        _date = cleaned_data.get('date')

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass
        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existence if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(
                _("You have to set an university year")
            )
        univ_year = univ_years[0]

        if _date and (_date < univ_year.start_date or _date > univ_year.end_date):
            raise forms.ValidationError(
                _("Holiday must set between university year dates")
            )

        return cleaned_data

    class Meta:
        model = Holiday
        fields = '__all__'


class VacationForm(forms.ModelForm):
    """
    Vacations form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass
        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existence if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(
                _("You have to set an university year")
            )
        univ_year = univ_years[0]

        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError(
                    _("Start date greater than end date")
                )
            if start_date < univ_year.start_date or start_date > univ_year.end_date:
                raise forms.ValidationError(
                    _("Vacation start date must set between university year dates")
                )
            if end_date < univ_year.start_date or end_date > univ_year.end_date:
                raise forms.ValidationError(
                    _("Vacation end date must set between university year dates")
                )

        return cleaned_data

    class Meta:
        model = Vacation
        fields = '__all__'


class CalendarForm(forms.ModelForm):
    """
    Calendar form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        calendar_mode = cleaned_data.get('calendar_mode')

        year_start_date = cleaned_data.get('year_start_date')
        year_end_date = cleaned_data.get('year_end_date')
        year_registration_start_date = cleaned_data.get('year_registration_start_date')

        s1_start_date = cleaned_data.get('semester1_start_date')
        s1_end_date = cleaned_data.get('semester1_end_date')
        s1_registration_start_date = cleaned_data.get('semester1_registration_start_date')
        s2_start_date = cleaned_data.get('semester2_start_date')
        s2_end_date = cleaned_data.get('semester2_end_date')
        s2_registration_start_date = cleaned_data.get('semester2_registration_start_date')
        valid_user = False

        # Test user group
        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass
        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existance if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(
                _("You have to set an university year")
            )
        univ_year = univ_years[0]

        # YEAR MODE
        if calendar_mode and \
            calendar_mode.lower() == Calendar.CALENDAR_MODE[0][0].lower():
            if not all([
                year_start_date, year_end_date, year_registration_start_date]):
                raise forms.ValidationError(
                    _("Mandatory fields not filled in")
                )
            if year_start_date and year_end_date:
                if year_start_date < univ_year.start_date or year_start_date > univ_year.end_date:
                    raise forms.ValidationError(
                        _("Start date must set between university year dates")
                    )
                if year_end_date < univ_year.start_date or year_end_date > univ_year.end_date:
                    raise forms.ValidationError(
                        _("End date must set between university year dates")
                    )

        # SEMESTER MODE
        elif calendar_mode and \
            calendar_mode.lower() == Calendar.CALENDAR_MODE[1][0].lower():
            if not all([s1_start_date, s1_end_date, s1_registration_start_date,
                s2_start_date, s2_end_date, s2_registration_start_date]):
                raise forms.ValidationError(
                    _("Mandatory fields not filled in")
                )
            if s1_start_date and s2_start_date and s1_end_date and \
                    s2_end_date and s1_registration_start_date and s2_registration_start_date:
                if s1_start_date < univ_year.start_date or s1_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 1 start date must set between university year dates"))
                if s2_start_date < univ_year.start_date or s2_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 2 start date must set between university year dates"))
                if s1_end_date < univ_year.start_date or s1_end_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 1 end date must set between university year dates"))
                if s2_end_date < univ_year.start_date or s2_end_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 2 end date must set between university year dates"))
                if s1_registration_start_date < univ_year.start_date or s1_registration_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 1 start registration date must set between university year dates"))
                if s2_registration_start_date < univ_year.start_date or s2_registration_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 2 start registration date must set between university year dates"))

        # start < end
        if year_start_date and year_end_date and year_start_date >= year_end_date:
            raise forms.ValidationError(_("Start date greater than end date"))
        # start1 < end1
        if s1_start_date and s1_end_date and s1_start_date >= s1_end_date:
            raise forms.ValidationError(
                _("Semester 1 start date greater than semester 1 end date")
            )
        # start2 < end2
        if s2_start_date and s2_end_date and s2_start_date >= s2_end_date:
            raise forms.ValidationError(
                _("Semester 2 start date greater than semester 2 end date")
            )
        # end1 < start2
        if s1_end_date and s2_start_date and s1_end_date >= s2_start_date:
            raise forms.ValidationError(
                _("Semester 1 ends after the beginning of semester 2")
            )
        # <==>   start1 < end1 < start2 < end2

        return cleaned_data

    class Meta:
        model = Calendar
        fields = '__all__'


class ImmersionUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields["password1"].required = False
        self.fields["password2"].required = False

    class Meta(UserCreationForm.Meta):
        model = ImmersionUser
        fields = '__all__'


class ImmersionUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if not self.request.user.is_superuser:
            if self.fields.get("is_staff"):
                self.fields["is_staff"].disabled = True
            if self.fields.get("is_superuser"):
                self.fields["is_superuser"].disabled = True

            if self.request.user.id == self.instance.id:
                self.fields["groups"].disabled = True
                self.fields["components"].disabled = True


    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data['groups']
        components = cleaned_data['components']
        forbidden_msg = _("Forbidden")

        is_own_account = self.request.user.id == self.instance.id

        if groups.filter(name='SCUIO-IP').exists():
            cleaned_data['is_staff'] = True

        if groups.filter(name='REF-CMP').exists() and not components.count():
            msg = _("This field is mandatory for a user belonging to 'REF-CMP' group")
            self._errors['components'] = self.error_class([msg])
            del cleaned_data["components"]

        if not self.request.user.is_superuser:
            # Check and alter fields when authenticated user is
            # a member of SCUIO-IP group
            if is_own_account:
                del cleaned_data['groups']
                del cleaned_data['components']

            elif self.request.user.has_groups('SCUIO-IP'):
                if self.instance.is_scuio_ip_manager():
                    raise forms.ValidationError(
                        _("You don't have enough privileges to modify this account")
                    )

                # Add groups to this list when needed
                can_change_groups = settings.HAS_RIGHTS_ON_GROUP.get('SCUIO-IP',)

                current_groups = set(self.instance.groups.all().values_list('name', flat=True))
                new_groups = set(groups.all().values_list('name', flat=True))

                forbidden_groups = [
                    g
                    for g in current_groups.symmetric_difference(new_groups)
                    if g not in can_change_groups
                ]

                if forbidden_groups:
                    raise forms.ValidationError(
                        _(
                            "You can't modify these groups : %s"
                            % ', '.join(x for x in forbidden_groups)
                        )
                    )

            if self.instance.is_superuser != cleaned_data["is_superuser"]:
                self._errors['is_superuser'] = self.error_class([forbidden_msg])

                raise forms.ValidationError(_("You can't modify the superuser status"))

            if self.instance.is_staff != cleaned_data["is_staff"]:
                self._errors['is_staff'] = self.error_class([forbidden_msg])

                raise forms.ValidationError(_("You can't modify the staff status"))

        return cleaned_data

    class Meta(UserCreationForm.Meta):
        model = ImmersionUser
        fields = '__all__'


class HighSchoolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if settings.USE_GEOAPI:
            city_choices = [
                ('', '---------'),
            ]
            zip_choices = [
                ('', '---------'),
            ]

            # Put datas in choices fields if form instance
            if self.instance.department:
                city_choices = get_cities(self.instance.department)

            if self.instance.city:
                zip_choices = get_zipcodes(self.instance.department, self.instance.city)

            # Put datas in choices fields if form data
            if 'department' in self.data:
                city_choices = get_cities(self.data.get('department'))

            if 'city' in self.data:
                zip_choices = get_zipcodes(self.data.get('department'), self.data.get('city'))

            self.fields['city'] = forms.TypedChoiceField(
                label=_("City"), widget=forms.Select(), choices=city_choices, required=True
            )
            self.fields['zip_code'] = forms.TypedChoiceField(
                label=_("Zip code"), widget=forms.Select(), choices=zip_choices, required=True
            )

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = HighSchool
        fields = '__all__'


class AccompanyingDocumentForm(forms.ModelForm):
    """
    Accompanying document form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_scuio_ip_manager()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # TODO: should we use only pdfs ?
        return cleaned_data

    class Meta:
        model = AccompanyingDocument
        fields = '__all__'


class InformationTextForm(forms.ModelForm):
    """
    Information text form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = InformationText
        fields = '__all__'

