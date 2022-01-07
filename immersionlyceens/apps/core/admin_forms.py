import importlib
import mimetypes
import re
from datetime import datetime
from typing import Any, Dict

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms.widgets import TextInput
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget

from ...libs.geoapi.utils import get_cities, get_departments, get_zipcodes
from .models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus,
    CancelType, CertificateLogo, CertificateSignature, CourseType,
    Establishment, EvaluationFormLink, EvaluationType, GeneralBachelorTeaching,
    GeneralSettings, HighSchool, Holiday, ImmersionUser, InformationText,
    MailTemplate, MailTemplateVars, OffOfferEventType, PublicDocument,
    PublicType, Structure, Training, TrainingDomain, TrainingSubdomain,
    UniversityYear, Vacation, HighSchoolLevel, PostBachelorLevel, StudentLevel,
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord

class CustomStructureMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.establishment:
            return f"{obj.establishment.code} - {str(obj)}"
        else:
            return str(obj)


class TypeFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user

            valid_groups = [
                user.is_superuser,
                user.is_master_establishment_manager(),
                user.is_operator()
            ]

            valid_user = any(valid_groups)
        except AttributeError:
            pass

        print(valid_user)

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data


class BachelorMentionForm(TypeFormMixin):
    class Meta:
        model = BachelorMention
        fields = '__all__'


class CampusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.fields.get("establishment") and not self.request.user.is_superuser \
                and self.request.user.is_establishment_manager():
            self.fields["establishment"].queryset = Establishment.objects.filter(pk=self.request.user.establishment.pk)

        try:
            if self.instance.establishment.id:
                self.fields["establishment"].disabled = True
        except (AttributeError, Establishment.DoesNotExist):
            pass

    def clean(self):
        cleaned_data = super().clean()
        establishment = cleaned_data.get("establishment")
        valid_user = False

        try:
            user = self.request.user
            valid_groups = [
                user.is_establishment_manager(),
                user.is_master_establishment_manager(),
                user.is_operator()
            ]
            valid_user = any(valid_groups)
        except AttributeError:
            pass

        if not self.request.user.is_superuser and self.request.user.is_establishment_manager():
            if establishment and establishment != self.request.user.establishment:
                msg = _("You must select your own establishment")
                if not self._errors.get("establishment"):
                    self._errors["establishment"] = forms.utils.ErrorList()
                self._errors['establishment'].append(self.error_class([msg]))

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # Check label uniqueness within the same establishment
        excludes = {}
        if self.instance:
            excludes['id'] = self.instance.id

        campus_queryset = Campus.objects.exclude(**excludes).filter(
            label__iexact=cleaned_data.get("label"),
            establishment=establishment
        )

        if campus_queryset.exists():
            msg = _("A campus with this label already exists within the same establishment")
            if not self._errors.get("label"):
                self._errors["label"] = forms.utils.ErrorList()
            self._errors['label'].append(self.error_class([msg]))

        return cleaned_data

    class Meta:
        model = Campus
        fields = ('establishment', 'label', 'active')


class CancelTypeForm(TypeFormMixin):
    class Meta:
        model = CancelType
        fields = '__all__'


class CourseTypeForm(TypeFormMixin):
    class Meta:
        model = CourseType
        fields = '__all__'


class TrainingDomainForm(TypeFormMixin):
    class Meta:
        model = TrainingDomain
        fields = '__all__'


class TrainingSubdomainForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.fields.get('training_domain'):
            self.fields['training_domain'].queryset = self.fields['training_domain'].queryset.order_by('label')

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_groups = [
                user.is_master_establishment_manager(),
                user.is_operator()
            ]
            valid_user = any(valid_groups)
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = TrainingSubdomain
        fields = '__all__'


class BuildingForm(forms.ModelForm):
    establishment = forms.ModelChoiceField(
        label=_("Establishment"),
        queryset=Establishment.objects.none(),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['campus'].queryset = Campus.objects.filter(active=True).order_by('label')

        valid_groups = [
            self.request.user.is_superuser,
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ]

        if any(valid_groups):
            self.fields['establishment'].queryset = Establishment.objects.all()
        else:
            if self.request.user.is_establishment_manager():
                user_establishment = self.request.user.establishment
                self.fields['establishment'].queryset = Establishment.objects.filter(pk=user_establishment.id)
                self.fields['campus'].queryset = Campus.objects.filter(establishment=user_establishment)

            if self.instance and self.instance.pk and self.instance.campus and self.instance.campus.establishment:
                self.fields['establishment'].disabled = True


        try:
            self.fields['establishment'].initial = self.instance.campus.establishment
        except (Campus.DoesNotExist, Establishment.DoesNotExist):
            # No initial value
            pass

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_groups = [
                user.is_master_establishment_manager(),
                user.is_establishment_manager(),
                user.is_operator(),
            ]
            valid_user = any(valid_groups)
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Building
        # fields = '__all__'
        fields = ('label', 'establishment', 'campus', 'url', 'active')


class TrainingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['training_subdomains'].queryset = (
            self.fields['training_subdomains']
            .queryset.filter(training_domain__active=True, active=True)
            .order_by('training_domain__label', 'label')
        )

        if self.fields and self.fields.get("structures"):
            self.fields["structures"] = CustomStructureMultipleChoiceField(
                queryset=Structure.objects.all().order_by('establishment__code', 'label'),
                widget=FilteredSelectMultiple(
                    verbose_name=Structure._meta.verbose_name,
                    is_stacked=False
                ),
                required=False
            )

        valid_groups = [
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ]

        if any(valid_groups):
            self.fields["highschool"].queryset = self.fields["highschool"].queryset\
                .filter(postbac_immersion=True)\
                .order_by('city', 'label')
        elif self.request.user.is_high_school_manager():
            self.fields["highschool"].queryset = self.fields["highschool"].queryset\
                .filter(id=self.request.user.highschool.id, postbac_immersion=True)\
                .order_by('city', 'label')

    @staticmethod
    def clean_highscool_or_structure(cleaned_data: Dict[str, Any]):
        high_school = cleaned_data.get("highschool")
        struct = cleaned_data.get("structures")

        if high_school is not None and struct is not None and struct.count() > 0:
            raise ValidationError(_("High school and structure can't be set together. Please choose one."))
        elif high_school is None and (struct is None or struct.count() <= 0):
            raise ValidationError(_("Neither high school nor structure is set. Please choose one."))

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user

            valid_groups = [
                user.is_establishment_manager(),
                user.is_master_establishment_manager(),
                user.is_high_school_manager(),
                user.is_operator()
            ]

            valid_user = any(valid_groups)
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        self.clean_highscool_or_structure(cleaned_data)
        # Check label uniqueness within the same establishment
        excludes = {}
        if self.instance:
            excludes['id'] = self.instance.id

        structure_establishments = [structure.establishment.id for structure in cleaned_data.get("structures", [])]

        tr_queryset = Training.objects.exclude(**excludes).filter(
            label__iexact=cleaned_data.get("label"),
            structures__establishment__in=structure_establishments)

        if tr_queryset.exists():
            msg = _("A training with this label already exists within the same establishment")
            if not self._errors.get("label"):
                self._errors["label"] = forms.utils.ErrorList()
            self._errors['label'].append(self.error_class([msg]))

        # Check structures : if user = establishment manager, we should have at least one
        # structure from its establishment
        if not self.request.user.is_superuser and self.request.user.is_establishment_manager():
            if not Establishment.objects.filter(
                pk=self.request.user.establishment.id,
                structures__in=cleaned_data.get("structures", [])
            ).exists():
                self.add_error('structures', _("At least one structure has to belong to your own establishment"))

        return cleaned_data

    class Meta:
        model = Training
        fields = '__all__'


class EstablishmentForm(forms.ModelForm):
    """
    Establishment form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.fields:
            self.fields["active"].initial = True

            # First establishment is always 'master'
            if not Establishment.objects.exists():
                self.fields["master"].initial = True
            # Next ones can't
            elif Establishment.objects.filter(master=True).exists():
                self.fields["master"].initial = False
                self.fields["master"].disabled = True
                self.fields["master"].help_text = _("A 'master' establishment already exists")

            # The 'master' flag can't be updated
            if self.instance:
                self.fields["master"].disabled = True
                self.fields["master"].help_text = _("This attribute cannot be updated")

        # Plugins
        # self.fields["data_source_plugins"] = forms.ChoiceField(choices=settings.AVAILABLE_ACCOUNTS_PLUGINS)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        code = cleaned_data.get('code')
        label = cleaned_data.get('label')
        short_label = cleaned_data.get('short_label')

        data_source_plugin = cleaned_data.get('data_source_plugin')
        data_source_settings = cleaned_data.get('data_source_settings')

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        if not data_source_plugin:
            cleaned_data['data_source_settings'] = None
        elif not data_source_settings:
            cleaned_data['data_source_settings'] = {}
            try:
                module_name = settings.ACCOUNTS_PLUGINS[data_source_plugin]
                source = importlib.import_module(module_name, package=None)

                for attr in source.AccountAPI.get_plugin_attrs():
                    cleaned_data['data_source_settings'][attr] = ""

            except KeyError:
                pass

        exclude_filter = {'id': self.instance.id} if self.instance else {}

        if not Establishment.objects.exists():
            cleaned_data["master"] = True
        elif Establishment.objects.filter(master=True).exclude(**exclude_filter).exists():
            cleaned_data["master"] = False

        if Establishment.objects.filter(code__iexact=code).exclude(**exclude_filter).exists():
            raise forms.ValidationError(_("This code already exists"))

        if Establishment.objects.filter(label__iexact=label).exclude(**exclude_filter).exists():
            raise forms.ValidationError(_("This label already exists"))

        if Establishment.objects.filter(short_label__iexact=short_label).exclude(**exclude_filter).exists():
            raise forms.ValidationError(_("This short label already exists"))

        # TODO : run selected plugin settings selftests when available

        return cleaned_data

    class Meta:
        model = Establishment
        fields = '__all__'
        widgets = {
            'badge_html_color': TextInput(attrs={'type': 'color'}),
        }


class StructureForm(forms.ModelForm):
    """
    Structure form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Disable code and structure fields if it already exists
        if self.initial:
            self.fields["code"].disabled = True
            self.fields["establishment"].disabled = True
            self.fields["establishment"].help_text = _("The establishment cannot be updated")

        if self.fields.get("establishment") and not self.request.user.is_superuser \
                and self.request.user.is_establishment_manager():
            self.fields["establishment"].queryset = Establishment.objects.filter(pk=self.request.user.establishment.pk)


    def clean(self):
        cleaned_data = super().clean()
        establishment = cleaned_data.get("establishment")

        valid_user = False

        try:
            user = self.request.user

            valid_groups = [
                user.is_establishment_manager(),
                user.is_master_establishment_manager(),
                user.is_operator()
            ]

            valid_user = any(valid_groups)
        except AttributeError:
            pass

        if not self.request.user.is_superuser and self.request.user.is_establishment_manager():
            if establishment and establishment != self.request.user.establishment:
                msg = _("You must select your own establishment")
                if not self._errors.get("establishment"):
                    self._errors["establishment"] = forms.utils.ErrorList()
                self._errors['establishment'].append(self.error_class([msg]))

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = Structure
        fields = '__all__'


class GeneralBachelorTeachingForm(TypeFormMixin):
    class Meta:
        model = GeneralBachelorTeaching
        fields = '__all__'


class PublicTypeForm(TypeFormMixin):
    """public type form class"""
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
        label = cleaned_data.get('label')
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        if start_date and start_date <= datetime.today().date():
            raise forms.ValidationError(_("Start date can't be today or earlier"))
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(_("Start date greater than end date"))
        if registration_start_date and start_date and registration_start_date < start_date:
            raise forms.ValidationError(_("Start of registration date must be set between start and end date"))
        if registration_start_date and end_date and registration_start_date >= end_date:
            raise forms.ValidationError(_("Start of registration date must be set between start and end date"))

        if start_date and end_date:
            if self.instance:
                all_univ_year = UniversityYear.objects.exclude(pk=self.instance.pk)
            else:
                all_univ_year = UniversityYear.objects.all()

            for uy in all_univ_year:
                if uy.active and not uy.purge_date:
                    raise forms.ValidationError(_("All university years are not purged. you can't create a new one"))
                if uy.date_is_between(start_date):
                    raise forms.ValidationError(_("University year starts inside another university year"))
                if uy.date_is_between(end_date):
                    raise forms.ValidationError(_("University year ends inside another university year"))
                if start_date <= uy.start_date <= end_date:
                    raise forms.ValidationError(_("University year contains another"))
                if start_date <= uy.end_date <= end_date:
                    raise forms.ValidationError(_("University year contains another"))

                if uy.active and uy.purge_date:
                    uy.active = False
                    uy.save()

        cleaned_data['active'] = True

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
        label = cleaned_data.get('label')
        now = datetime.now().date()

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existence if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(_("You have to set an university year"))

        univ_year = univ_years[0]

        if _date:
            if not user.is_superuser:
                if user.is_operator() and now > univ_year.start_date:
                    raise forms.ValidationError(_("Error : the university year has already begun"))

            if _date < univ_year.start_date or _date >= univ_year.end_date:
                raise forms.ValidationError(_("Holiday must set between university year dates"))

            if _date < now:
                raise forms.ValidationError(_("Holiday must be set in the future"))

            all_holidays = Holiday.objects.exclude(label=label)
            for hol in all_holidays:
                if _date == hol.date:
                    raise forms.ValidationError(_("Holiday date already exists in other holiday"))

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
        label = cleaned_data.get('label')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        now = datetime.now().date()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existence if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(_("You have to set an university year"))
        univ_year = univ_years[0]

        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError(_("Start date greater than end date"))

            if start_date < univ_year.start_date or start_date > univ_year.end_date:
                raise forms.ValidationError(_("Vacation start date must set between university year dates"))

            if end_date < univ_year.start_date or end_date >= univ_year.end_date:
                raise forms.ValidationError(_("Vacation end date must set between university year dates"))

            if start_date < now:
                raise forms.ValidationError(_("Vacation start date must be set in the future"))

            if not user.is_superuser:
                if user.is_operator() and now > univ_year.start_date:
                    raise forms.ValidationError(_("Error : the university year has already begun"))

            all_vacations = Vacation.objects.exclude(label=label)
            for vac in all_vacations:
                if vac.date_is_between(start_date):
                    raise forms.ValidationError(_("Vacation start inside another vacation"))
                if vac.date_is_between(end_date):
                    raise forms.ValidationError(_("Vacation end inside another vacation"))
                if start_date <= vac.start_date and vac.start_date <= end_date:
                    raise forms.ValidationError(_("A vacation exists inside this vacation"))
                if start_date <= vac.end_date and vac.end_date <= end_date:
                    raise forms.ValidationError(_("A vacation exists inside this vacation"))

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
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass
        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existance if an active university year
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            raise forms.ValidationError(_("You have to set an university year"))
        univ_year = univ_years[0]

        # YEAR MODE
        if calendar_mode and calendar_mode.lower() == Calendar.CALENDAR_MODE[0][0].lower():
            # if not all([year_start_date, year_end_date, year_registration_start_date]):
            #     raise forms.ValidationError(_("Mandatory fields not filled in"))
            if year_start_date and year_end_date:
                if year_start_date < univ_year.start_date or year_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("Start date must be set between university year dates"))
                if year_end_date < univ_year.start_date or year_end_date > univ_year.end_date:
                    raise forms.ValidationError(_("End date must set be between university year dates"))

        # SEMESTER MODE
        elif calendar_mode and calendar_mode.lower() == Calendar.CALENDAR_MODE[1][0].lower():
            # if not all(
            #     [
            #         s1_start_date,
            #         s1_end_date,
            #         s1_registration_start_date,
            #         s2_start_date,
            #         s2_end_date,
            #         s2_registration_start_date,
            #     ]
            # ):
            #     raise forms.ValidationError(_("Mandatory fields not filled in"))
            if (
                s1_start_date
                and s2_start_date
                and s1_end_date
                and s2_end_date
                and s1_registration_start_date
                and s2_registration_start_date
            ):
                if s1_start_date < univ_year.start_date or s1_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 1 start date must set between university year dates"))
                if s2_start_date < univ_year.start_date or s2_start_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 2 start date must set between university year dates"))
                if s1_end_date < univ_year.start_date or s1_end_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 1 end date must set between university year dates"))
                if s2_end_date < univ_year.start_date or s2_end_date > univ_year.end_date:
                    raise forms.ValidationError(_("semester 2 end date must set between university year dates"))
                if s1_registration_start_date < univ_year.start_date or s1_registration_start_date > univ_year.end_date:
                    raise forms.ValidationError(
                        _("semester 1 start registration date must set between university year dates")
                    )
                if s2_registration_start_date < univ_year.start_date or s2_registration_start_date > univ_year.end_date:
                    raise forms.ValidationError(
                        _("semester 2 start registration date must set between university year dates")
                    )

        # start < end
        if year_start_date and year_end_date and year_start_date >= year_end_date:
            raise forms.ValidationError(_("Start date greater than end date"))
        # start1 < end1
        if s1_start_date and s1_end_date and s1_start_date >= s1_end_date:
            raise forms.ValidationError(_("Semester 1 start date greater than semester 1 end date"))
        # start2 < end2
        if s2_start_date and s2_end_date and s2_start_date >= s2_end_date:
            raise forms.ValidationError(_("Semester 2 start date greater than semester 2 end date"))
        # end1 < start2
        if s1_end_date and s2_start_date and s1_end_date >= s2_start_date:
            raise forms.ValidationError(_("Semester 1 ends after the beginning of semester 2"))
        # <==>   start1 < end1 < start2 < end2

        return cleaned_data

    class Meta:
        model = Calendar
        fields = '__all__'


class ImmersionUserCreationForm(UserCreationForm):
    search = forms.CharField(
        max_length=150,
        label=_("User search"),
        required=False,
        help_text=_("This field is only useful if the selected establishment has a source plugin set")
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields["password1"].required = False
        self.fields["password2"].required = False

        self.fields["last_name"].required = True
        self.fields["first_name"].required = True
        self.fields["email"].required = True

        if self.request.user.is_high_school_manager():
            self.fields["email"].help_text = _("The user email will be used as username")

        # Establishment
        if self.fields.get("establishment"):
            self.fields["establishment"].required = False

        if self.fields.get("search"):
            self.fields["search"].widget.attrs["class"] = "vTextField"

        if not self.request.user.is_superuser:
            # Master establishment manager has access to all establishments
            #if self.request.user.is_master_establishment_manager():
            #    self.fields["establishment"].queryset = self.fields["establishment"].queryset.filter(master=False)

            # A regular establishment manager has only access to his own establishment
            if self.request.user.is_establishment_manager() and "establishment" in self.fields:
                self.fields["establishment"].empty_label = None
                self.fields["establishment"].queryset = Establishment.objects.filter(
                    pk=self.request.user.establishment.pk
                )

            if self.request.user.is_high_school_manager() and self.fields.get("username"):
                self.fields["username"].required = False

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")

        # A high-school manager can only create high-school speakers
        # For them, the login in always the email address

        establishment = cleaned_data.get("establishment")

        if ImmersionUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            self.add_error('email', _("This email address is already used"))
            return cleaned_data

        # Override username
        if not establishment or (establishment and establishment.data_source_plugin is None):
            cleaned_data["username"] = email

        # Override high school when a high school manager creates an account
        if not self.request.user.is_superuser and self.request.user.is_high_school_manager():
            self.instance.highschool = self.request.user.highschool

        return cleaned_data


    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)

        if not self.request.user.is_superuser and self.request.user.is_high_school_manager():
            obj.highschool = self.request.user.highschool
            obj.username = obj.email
            obj.save()
            Group.objects.get(name='INTER').user_set.add(obj)

        return obj


    class Meta(UserCreationForm.Meta):
        model = ImmersionUser
        # fields = '__all__'
        fields = ("establishment", "username", "search", "password1", "password2", "email",
                  "first_name", "last_name", "is_active")


class ImmersionUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.fields and self.fields.get('highschool'):
            self.fields["highschool"].queryset = HighSchool.objects.all().order_by("city", "label")

        if self.fields and self.fields.get('structures'):
            self.fields["structures"] = CustomStructureMultipleChoiceField(
                queryset=Structure.objects.all().order_by('establishment__code', 'label'),
                widget=FilteredSelectMultiple(
                    verbose_name=Structure._meta.verbose_name,
                    is_stacked=False
                ),
                required=False
            )

        if not self.request.user.is_superuser:
            # Disable establishment modification
            if self.fields.get('establishment'):
                if self.instance.establishment:
                    self.fields["establishment"].queryset = Establishment.objects.filter(id=self.instance.establishment.id)
                    self.fields["establishment"].empty_label = None

                    # Lock fields when the selected establishment has a source plugin set
                    has_plugin = self.instance.establishment.data_source_plugin is not None
                    if has_plugin:
                        self.fields["username"].disabled = True
                        self.fields["email"].disabled = True
                        self.fields["first_name"].disabled = True
                        self.fields["last_name"].disabled = True

                    self.fields["groups"].queryset = \
                        self.fields["groups"].queryset.exclude(name__in=['ETU', 'LYC', 'REF-LYC'])
                else:
                    self.fields["establishment"].queryset = Establishment.objects.none()
                    self.fields["groups"].queryset = \
                        self.fields["groups"].queryset.filter(name__in=['REF-LYC', 'INTER'])

                self.fields["establishment"].help_text = _("The establishment cannot be updated once the user created")

            for field in ["last_name", "first_name", "email"]:
                if self.fields.get(field):
                    self.fields[field].required = True

            for field in ["is_staff", "is_superuser", "username"]:
                if self.fields.get(field):
                    self.fields[field].disabled = True

            # Restrictions on structures selection
            if self.fields.get('structures'):
                if self.instance.establishment:
                    self.fields["structures"].queryset = Structure.objects.filter(
                        establishment=self.instance.establishment
                    )
                else:
                    self.fields["structures"].queryset = Structure.objects.none()

            # Restrictions on group depending on current user group
            if self.request.user.is_master_establishment_manager():
                if not self.instance.is_master_establishment_manager():
                    self.fields["groups"].queryset = \
                        self.fields["groups"].queryset.exclude(name__in=['REF-ETAB-MAITRE']).order_by('name')

            if self.request.user.is_establishment_manager():
                user_establishment = self.request.user.establishment

                if self.fields.get('groups'):
                    self.fields["groups"].queryset = self.fields["groups"].queryset.filter(
                        name__in=settings.HAS_RIGHTS_ON_GROUP['REF-ETAB']
                    ).order_by('name')

                if self.fields.get('structures'):
                    self.fields["structures"].queryset = Structure.objects.filter(establishment=user_establishment)

                if self.fields.get('establishment'):
                    self.fields["establishment"].queryset = Establishment.objects.filter(pk=user_establishment.id)

            if self.request.user.is_high_school_manager():
                user_highschool = self.request.user.highschool

                if self.fields.get("username"):
                    self.fields["username"].widget.attrs['readonly'] = 'readonly'

                if self.fields.get("structures"):
                    self.fields["structures"].disabled = True

                if self.fields.get("groups"):
                    self.fields["groups"].queryset = self.fields["groups"].queryset.filter(
                        name__in=['INTER']
                    )
                    self.fields["groups"].disabled = True

                if self.fields.get('highschool'):
                    self.fields["highschool"].empty_label = None
                    self.fields["highschool"].queryset = \
                        HighSchool.objects.filter(pk=user_highschool.id).order_by("city", "label")


    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data.get('groups')
        structures = cleaned_data.get('structures')
        establishment = cleaned_data.get('establishment')
        highschool = cleaned_data.get('highschool')
        forbidden_msg = _("Forbidden")

        if groups:
            if groups and groups.filter(name__in=('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')).exists():
                cleaned_data['is_staff'] = True

            if groups and groups.filter(name__in='REF-ETAB').exists():
                if establishment is None or establishment.master:
                    msg = _("Please select a non-master establishment for a user belonging to the 'REF-ETAB' group")
                    self._errors['establishment'] = self.error_class([msg])
                    del cleaned_data["establishment"]

            if groups and groups.filter(name='REF-ETAB-MAITRE').exists():
                if establishment is None or not establishment.master:
                    msg = _("Please select a master establishment for a user belonging to the 'REF-ETAB-MAITRE' group")
                    self._errors['establishment'] = self.error_class([msg])
                    del cleaned_data["establishment"]

            if groups.filter(name='REF-STR').exists() and not structures.count():
                msg = _("This field is mandatory for a user belonging to 'REF-STR' group")
                self._errors['structures'] = self.error_class([msg])
                del cleaned_data["structures"]

            if structures.count() and not groups.filter(name='REF-STR').exists():
                msg = _("The group 'REF-STR' is mandatory when you add a structure")
                if not self._errors.get("groups"):
                    self._errors["groups"] = forms.utils.ErrorList()
                self._errors['groups'].append(self.error_class([msg]))

            if groups.filter(name='REF-LYC').exists():
                if not highschool:
                    msg = _("This field is mandatory for a user belonging to 'REF-LYC' group")
                    self._errors["highschool"] = self.error_class([msg])
                    del cleaned_data["highschool"]
                elif highschool.postbac_immersion:
                    cleaned_data['is_staff'] = True


            if highschool and not groups.filter(name__in=('REF-LYC', 'INTER')).exists():
                msg = _("The groups 'REF-LYC' or 'INTER' is mandatory when you add a highschool")
                if not self._errors.get("groups"):
                    self._errors["groups"] = forms.utils.ErrorList()
                self._errors['groups'].append(self.error_class([msg]))

        if not self.request.user.is_superuser and not self.request.user.is_operator():
            # Check and alter fields when authenticated user is
            # a member of REF-ETAB group
            if self.request.user.has_groups('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC'):
                if (self.request.user.has_groups('REF-ETAB') and self.instance.is_establishment_manager()) or \
                   (self.request.user.has_groups('REF-ETAB-MAITRE') and self.instance.is_master_establishment_manager()):
                    raise forms.ValidationError(_("You don't have enough privileges to modify this account"))

                # Add groups to this list when needed
                can_change_groups = False

                if self.request.user.has_groups('REF-ETAB'):
                    can_change_groups = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB',)
                elif self.request.user.has_groups('REF-ETAB-MAITRE'):
                    can_change_groups = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB-MAITRE', )
                elif self.request.user.has_groups('REF-TEC'):
                    can_change_groups = settings.HAS_RIGHTS_ON_GROUP.get('REF-TEC', )

                current_groups = set(self.instance.groups.all().values_list('name', flat=True))
                new_groups = set(groups.all().values_list('name', flat=True)) if groups else set()

                forbidden_groups = [
                    g for g in current_groups.symmetric_difference(new_groups) if g not in can_change_groups
                ]

                if forbidden_groups:
                    raise forms.ValidationError(
                        _("You can't modify these groups : %s" % ', '.join(x for x in forbidden_groups))
                    )

            if self.instance.is_superuser != cleaned_data["is_superuser"]:
                self._errors['is_superuser'] = self.error_class([forbidden_msg])

                raise forms.ValidationError(_("You can't modify the superuser status"))

        return cleaned_data


    def save(self, *args, **kwargs):
        # If REF-LYC is in new groups, send a mail to choose a password
        # if no password has been set yet
        ref_lyc_group = None
        inter_group = None
        try:
            ref_lyc_group = Group.objects.get(name='REF-LYC')
            inter_group = Group.objects.get(name='INTER')
        except Group.DoesNotExist:
            pass

        try:
            current_groups = {str(g.id) for g in self.instance.groups.all()}
        except Exception:
            current_groups = set()

        new_groups = set(self.data.get('groups', []))

        if inter_group:
            if self.request.user.is_high_school_manager():
                if not self.instance.groups.filter(name='INTER').exists():
                    new_groups.add(str(inter_group.id))

        if not self.request.user.is_superuser and not self.request.user.is_operator():
            conditions = [
                self.instance.establishment and not self.instance.establishment.data_source_plugin,
                self.instance.highschool is not None
            ]

            if any(conditions):
                self.instance.username = self.instance.email
            # TODO: send CPT_CREATE_INTER in case of a new user

        if ref_lyc_group and str(ref_lyc_group.id) in new_groups - current_groups:
            # REF-LYC group spotted : if the password is not set, send an email to the user
            user = self.instance
            if not user.last_login:
                user.set_recovery_string()
                user.send_message(self.request, "CPT_CREATE_LYCEE")

        self.instance = super().save(*args, **kwargs)

        if self.request.user.is_high_school_manager():
            if not self.instance.groups.filter(name='INTER').exists():
                self.instance.groups.add(inter_group)

        return self.instance

    class Meta(UserChangeForm.Meta):
        model = ImmersionUser
        fields = ("establishment", "username", "first_name", "last_name", "email", "is_active", "is_staff",
                  "is_superuser", "groups", "structures", "highschool")


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

            department_choices = get_departments()

            # if this test fails, it's probably an API error or timeout => switch to manual form
            if department_choices:
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

                self.fields['department'] = forms.TypedChoiceField(
                    label=_("Department"), widget=forms.Select(), choices=department_choices, required=True
                )
                self.fields['city'] = forms.TypedChoiceField(
                    label=_("City"), widget=forms.Select(), choices=city_choices, required=True
                )
                self.fields['zip_code'] = forms.TypedChoiceField(
                    label=_("Zip code"), widget=forms.Select(), choices=zip_choices, required=True
                )


        if not self.instance or (self.instance and not self.instance.postbac_immersion) \
            and self.fields.get("mailing_list"):
            self.fields["mailing_list"].disabled = True

        if self.fields.get('mailing_list'):
            self.fields["mailing_list"].help_text = \
                _("This field is available when 'Offer post-bachelor immersions is enabled")


    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user

            valid_groups = [
                user.is_operator(),
                user.is_master_establishment_manager(),
                user.is_high_school_manager() and user.highschool
            ]

            valid_user = any(valid_groups)
        except AttributeError as exc:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = HighSchool
        fields = '__all__'


class MailTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        for field in ('label', 'description'):
            if self.fields.get(field):
                self.fields[field].widget.attrs['class'] = 'form-control'
                self.fields[field].widget.attrs['size'] = 80

        if self.fields:
            if self.instance.id:
                self.fields['code'].disabled = True

            if not self.request.user.is_superuser and not self.request.user.is_operator():
                self.fields['available_vars'].widget = forms.MultipleHiddenInput()

                if self.request.user.is_master_establishment_manager():
                    self.fields['available_vars'].queryset = self.fields['available_vars'].queryset.order_by('code')
                else:
                    self.fields['description'].disabled = True
                    self.fields['label'].disabled = True

            self.fields['available_vars'].required = False


    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code", '')
        body = cleaned_data.get("body", '')
        available_vars = cleaned_data.get("available_vars", '')

        valid_user = False

        try:
            user = self.request.user
            if self.instance.pk:
                valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
            else:
                valid_user = user.is_superuser
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        cleaned_data["code"] = code.upper()

        body_errors_list = []

        # Check variables and raise an error if forbidden ones are found
        forbidden_vars = MailTemplateVars.objects.exclude(code__in=[v.code for v in available_vars])

        forbidden_vars_list = [f_var.code for f_var in forbidden_vars if f_var.code.lower() in body.lower()]

        if forbidden_vars_list:
            forbidden_vars_msg = _("The message body contains forbidden variables : ") + ', '.join(forbidden_vars_list)

            body_errors_list.append(self.error_class([forbidden_vars_msg]))

        # Check for unknown variables in body
        all_vars = re.findall(r"(\$\{[\w+\.]*\})", body)
        unknown_vars = [v for v in all_vars if not MailTemplateVars.objects.filter(code__iexact=v.lower()).exists()]

        if unknown_vars:
            unknown_vars_msg = _("The message body contains unknown variable(s) : ") + ', '.join(unknown_vars)
            body_errors_list.append(self.error_class([unknown_vars_msg]))

        if body_errors_list:
            raise forms.ValidationError(body_errors_list)

        return cleaned_data

    class Meta:
        model = MailTemplate
        fields = '__all__'
        widgets = {
            'body': SummernoteWidget(),
        }


class AccompanyingDocumentForm(forms.ModelForm):
    """
    Accompanying document form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_document(self):
        document = self.cleaned_data['document']
        if document and isinstance(document, UploadedFile):
            # See settings content types allowed
            allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in settings.CONTENT_TYPES]

            if document.content_type in allowed_content_type:
                if document.size > int(settings.MAX_UPLOAD_SIZE):
                    raise forms.ValidationError(
                        _('Please keep filesize under %(maxupload)s. Current filesize %(current_size)s')
                        % {
                            'maxupload': filesizeformat(settings.MAX_UPLOAD_SIZE),
                            'current_size': filesizeformat(document.size),
                        }
                    )
            else:
                raise forms.ValidationError(_('File type is not allowed'))

        return document

    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

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


    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            if self.instance.pk:
                valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
            else:
                valid_user = user.is_superuser
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data


    class Meta:
        model = InformationText
        fields = '__all__'
        widgets = {'content': SummernoteWidget}


class PublicDocumentForm(forms.ModelForm):
    """
    Public document form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_document(self):
        document = self.cleaned_data['document']
        if document and isinstance(document, UploadedFile):
            # See settings content types allowed
            allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in settings.CONTENT_TYPES]

            if document.content_type in allowed_content_type:
                if document.size > int(settings.MAX_UPLOAD_SIZE):
                    raise forms.ValidationError(
                        _('Please keep filesize under %(maxupload)s. Current filesize %(current_size)s') % {
                            'maxupload': filesizeformat(settings.MAX_UPLOAD_SIZE),
                            'current_size': filesizeformat(document.size),
                        }
                    )
            else:
                raise forms.ValidationError(_('File type is not allowed'))
        return document

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = PublicDocument
        fields = '__all__'


class EvaluationTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = EvaluationType
        fields = '__all__'


class EvaluationFormLinkForm(TypeFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            if self.fields.get("evaluation_type") and self.instance.evaluation_type:
                self.fields["evaluation_type"].disabled = True
        except AttributeError:
            pass

    def clean(self):
        cleaned_data = super().clean()
        if not self.request.user.is_superuser and not self.instance.pk:
            raise forms.ValidationError(_("You are not allowed to create a new Evaluation Form Link"))

        return cleaned_data

    class Meta:
        model = EvaluationFormLink
        fields = '__all__'


class GeneralSettingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = GeneralSettings
        fields = '__all__'


class CertificateLogoForm(forms.ModelForm):
    """
    Certificate logo form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_logo(self):
        logo = self.cleaned_data['logo']
        if logo and isinstance(logo, UploadedFile):

            allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in ['png', 'jpeg', 'jpg', 'gif']]

            if not logo.content_type in allowed_content_type:
                raise forms.ValidationError(_('File type is not allowed'))

        return logo

    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = CertificateLogo
        fields = '__all__'


class CertificateSignatureForm(forms.ModelForm):
    """
    Certificate logo form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_signature(self):
        signature = self.cleaned_data['signature']
        if signature and isinstance(signature, UploadedFile):

            allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in ['png', 'jpeg', 'jpg', 'gif']]

            if not signature.content_type in allowed_content_type:
                raise forms.ValidationError(_('File type is not allowed'))

        return signature

    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = CertificateSignature
        fields = '__all__'


class OffOfferEventTypeForm(TypeFormMixin):
    """Off over event type form"""
    class Meta:
        model = OffOfferEventType
        fields = '__all__'


class HighSchoolLevelForm(TypeFormMixin):
    """
    High school level form
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            if HighSchoolStudentRecord.objects.filter(level=self.instance).exists():
                self.fields['active'].disabled = True
                self.fields['active'].help_text = _("Field locked : a high school record uses this level")

    class Meta:
        model = HighSchoolLevel
        fields = '__all__'


class PostBachelorLevelForm(TypeFormMixin):
    """
    Post bachelor level form
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            if HighSchoolStudentRecord.objects.filter(post_bachelor_level=self.instance).exists():
                self.fields['active'].disabled = True
                self.fields['active'].help_text = _("Field locked : a high school record uses this level")

    class Meta:
        model = PostBachelorLevel
        fields = '__all__'


class StudentLevelForm(TypeFormMixin):
    """
    Student level form
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            if StudentRecord.objects.filter(student_level=self.instance).exists():
                self.fields['active'].disabled = True
                self.fields['active'].help_text = _("Field locked : a student record uses this level")

    class Meta:
        model = StudentLevel
        fields = '__all__'