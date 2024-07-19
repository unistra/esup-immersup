import importlib
import magic
import mimetypes
import re
from datetime import datetime
from typing import Any, Dict
from ckeditor.widgets import CKEditorWidget
from django import forms, template
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.management import get_commands, load_command_class
from django.db.models import Count, Q
from django.forms.widgets import TextInput, TimeInput
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _, pgettext


from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord,
)

from ...libs.geoapi.utils import get_cities, get_departments, get_zipcodes
from .models import (
    AccompanyingDocument, AttestationDocument, BachelorMention, BachelorType,
    Building, Campus, CancelType, CertificateLogo, CertificateSignature, CourseType,
    CustomThemeFile, Establishment, EvaluationFormLink, EvaluationType, FaqEntry,
    GeneralBachelorTeaching, GeneralSettings, HighSchool, HighSchoolLevel,
    Holiday, ImmersionUser, ImmersionUserGroup, InformationText,
    MailTemplate, MailTemplateVars, OffOfferEventType, Period,
    PostBachelorLevel, Profile, PublicDocument, PublicType, ScheduledTask,
    Structure, StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UAI, UniversityYear, Vacation,
)


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

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data


class BachelorMentionForm(TypeFormMixin):
    class Meta:
        model = BachelorMention
        fields = '__all__'

class BachelorTypeForm(TypeFormMixin):
    class Meta:
        model = BachelorType
        fields = '__all__'

class CampusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if settings.USE_GEOAPI and (not self.is_bound or self.errors):
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
                user.is_superuser,
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
        fields = ('establishment', 'label', 'department', 'city', 'zip_code', 'active')


class CancelTypeForm(TypeFormMixin):
    def clean(self):
        cleaned_data = super().clean()

        system = cleaned_data.get("system", None)
        code = cleaned_data.get("code", None)

        if system is None:
            cleaned_data["system"] = False
        elif system is True and not code:
            raise forms.ValidationError(_("A code is needed when 'system' is True"))

        return cleaned_data

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
                user.is_superuser,
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
                user.is_superuser,
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
            self.request.user.is_superuser,
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
    def clean_highschool_or_structure(cleaned_data: Dict[str, Any]):
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
                user.is_superuser,
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

        self.clean_highschool_or_structure(cleaned_data)
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
            if self.fields.get("active"):
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
            valid_user = user.is_superuser or user.is_operator() or user.is_master_establishment_manager()
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
            'certificate_header': CKEditorWidget(),
            'certificate_footer': CKEditorWidget(),
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
                user.is_superuser,
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
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        if not self.instance.pk and start_date and start_date <= timezone.localdate():
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
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
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
        excludes = {}

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # existence if an active university year
        try:
            univ_year = UniversityYear.get_active()
        except Exception as e:
            raise

        if not univ_year:
            raise forms.ValidationError(_("You have to set an university year"))

        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError(_("Start date must be set before end date"))

            if start_date < univ_year.start_date or start_date > univ_year.end_date:
                raise forms.ValidationError(_("Vacation start date must be set between university year dates"))

            if end_date < univ_year.start_date or end_date >= univ_year.end_date:
                raise forms.ValidationError(_("Vacation end date must be set between university year dates"))

            if not user.is_superuser:
                if user.is_operator() and now > univ_year.start_date:
                    raise forms.ValidationError(_("Error : the university year has already begun"))

            if self.instance and self.instance.id:
                excludes['pk'] = self.instance.id

            all_vacations = Vacation.objects.exclude(**excludes)
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


class PeriodForm(forms.ModelForm):
    """
    Period form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        now = timezone.now()

        if self.instance and self.instance.pk:
            # Lock start date update if in the past
            if self.instance.immersion_start_date < today:
                if "immersion_start_date" in self.fields:
                    self.fields["immersion_start_date"].disabled = True

                # Cannot change registration end date
                if self.instance.registration_end_date_policy == Period.REGISTRATION_END_DATE_PERIOD:
                    if "registration_end_date" in self.fields:
                        self.fields["registration_end_date"].disabled = True

            if self.instance.registration_start_date < now:
                if "registration_start_date" in self.fields:
                    self.fields["registration_start_date"].disabled = True

            """
            OBSOLETE
            if self.instance.registration_start_date >= today:
                self.fields["allowed_immersions"] = forms.IntegerField(disabled=True)
                self.fields["allowed_immersions"].help_text = _("Registrations have begun, this field can't be updated")
            """

            readonly_fields = []

            if self.instance.immersion_end_date < today:
                readonly_fields = [
                    'label',
                    'immersion_start_date',
                    'immersion_end_date',
                    'registration_start_date',
                    'allowed_immersions',
                ]
            elif self.instance.immersion_start_date <= today <= self.instance.immersion_end_date:
                readonly_fields = [
                    'label',
                    'immersion_start_date',
                    'registration_end_date_policy',
                    'registration_start_date',
                    'registration_end_date',
                ]
            elif self.instance.immersion_start_date > today:
                if self.instance.registration_start_date.date() < today:
                    readonly_fields += [
                        'label',
                        'registration_start_date',
                        'registration_end_date_policy'
                    ]

            for field in readonly_fields:
                if field in self.fields:
                    self.fields[field].disabled = True


    def clean(self):
        today = timezone.localdate()
        now = timezone.now()

        cleaned_data = super().clean()

        immersion_start_date = cleaned_data.get('immersion_start_date')
        immersion_end_date = cleaned_data.get('immersion_end_date')
        registration_start_date = cleaned_data.get('registration_start_date')
        registration_end_date = cleaned_data.get('registration_end_date')
        registration_end_date_policy = cleaned_data.get('registration_end_date_policy')
        allowed_immersions = cleaned_data.get('allowed_immersions')

        valid_user = False

        # Test user group
        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass
        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        # active university year
        univ_year = UniversityYear.get_active()

        if not univ_year:
            raise forms.ValidationError(_("An active university year is required to create a period"))

        # Mandatory dates
        period_dates = [
            "immersion_start_date", "immersion_end_date", "registration_start_date"
        ]

        if registration_end_date_policy == Period.REGISTRATION_END_DATE_PERIOD:
            period_dates.append("registration_end_date")

            try:
                if int(cleaned_data.get("cancellation_limit_delay")) < 0:
                    raise ValueError
            except (ValueError, TypeError):
                self.add_error("cancellation_limit_delay", _("A null or positive value is required"))

        date_error = False
        for d in period_dates:
            if not cleaned_data.get(d):
                date_error = True
                self.add_error(d, _("A value is required"))

        if date_error:
            raise forms.ValidationError(_("A period requires all dates to be filled in"))

        # Dates check
        dates_conditions = [
            not (univ_year.start_date <= registration_start_date.date() < univ_year.end_date),
            registration_end_date and not (univ_year.start_date <= registration_end_date.date() < univ_year.end_date),
            not (univ_year.start_date < immersion_start_date < univ_year.end_date),
            not (univ_year.start_date < immersion_end_date <= univ_year.end_date),
        ]

        if any(dates_conditions):
            raise forms.ValidationError(_("All period dates must be between university year start/end dates"))

        if not self.instance.id and immersion_start_date < today:
            raise forms.ValidationError(_("A new period can't be set with a start_date in the past"))

        if registration_start_date.date() >= immersion_start_date:
            raise forms.ValidationError(_("Registration start date must be before the immersions start date"))

        if registration_end_date and registration_end_date.date() >= immersion_start_date:
            raise forms.ValidationError(_("Registration end date must be before the immersions start date"))

        if registration_end_date and registration_start_date and registration_end_date <= registration_start_date:
            raise forms.ValidationError(_("Registration end date must be after the registration start date"))

        # check immersions start < end
        if immersion_start_date and immersion_end_date and immersion_start_date >= immersion_end_date:
            raise forms.ValidationError(_("Immersions end date must be after immersions start date"))

        # Fields that can be updated with conditions
        if self.instance and self.instance.pk:
            if self.instance.immersion_start_date <= today <= self.instance.immersion_end_date:
                if self.has_changed():
                    if 'immersion_end_date' in self.changed_data:
                        # change end date only for a future date
                        if immersion_end_date < self.instance.immersion_end_date:
                            raise forms.ValidationError(_("Immersions end date can only be set after the actual one"))
                    if 'allowed_immersions' in self.changed_data:
                        if allowed_immersions < self.instance.allowed_immersions:
                            raise forms.ValidationError(
                                _("New allowed immersions value can only be higher than the previous one")
                            )
            if self.instance.immersion_start_date > today:
                if self.has_changed():
                    slots_exist = self.instance.slots.exists()
                    if 'immersion_start_date' in self.changed_data:
                        if slots_exist and immersion_start_date > self.instance.immersion_start_date:
                            raise forms.ValidationError(
                                _("Immersions start date can only be set before the actual one")
                            )
                    if 'immersion_end_date' in self.changed_data:
                        if slots_exist and immersion_end_date < self.instance.immersion_end_date:
                            raise forms.ValidationError(
                                _("Immersions end date can only be set after the actual one")
                            )

        return cleaned_data

    class Meta:
        model = Period
        fields = "__all__"


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

        establishment = cleaned_data.get("establishment")

        if establishment and establishment.provides_accounts():
            # do not transform email and username
            email = cleaned_data.get("email", "").strip()
        else:
            email = cleaned_data.get("email", "").strip().lower()

        if ImmersionUser.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            self.add_error('email', _("This email address is already used"))
            return cleaned_data

        # Override username
        cleaned_data["username"] = email
        cleaned_data["email"] = email

        # Override high school when a high school manager creates an account
        if not self.request.user.is_superuser and self.request.user.is_high_school_manager():
            self.instance.highschool = self.request.user.highschool

        return cleaned_data


    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)

        obj.username = obj.email

        if not self.request.user.is_superuser and self.request.user.is_high_school_manager():
            obj.highschool = self.request.user.highschool
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
                if not self.instance.is_master_establishment_manager() and self.fields.get('groups'):
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

        if establishment and establishment.provides_accounts():
            # do not transform email and username
            cleaned_data["email"] = cleaned_data.get("email", "").strip()
        else:
            cleaned_data["email"] = cleaned_data.get("email", "").strip().lower()

        if groups:
            linked_groups_conditions = [
                len(self.instance.linked_users()) > 1 and not groups.filter(name='INTER').exists(),
                len(self.instance.linked_users()) > 1 and groups.filter(name='INTER').exists() and groups.count() > 1
            ]

            if any(linked_groups_conditions):
                msg = _("This user has linked accounts, you can't update his/her groups")
                if not self._errors.get("groups"):
                    self._errors["groups"] = forms.utils.ErrorList()
                self._errors['groups'].append(self.error_class([msg]))

            # A user can have two groups if one of them is INTER
            if groups.count() > 2 or groups.count() > 1 and not groups.filter(name='INTER').exists():
                msg = _("A user cannot have multiple profiles except for the INTER one")
                if not self._errors.get("groups"):
                    self._errors["groups"] = forms.utils.ErrorList()
                self._errors['groups'].append(self.error_class([msg]))

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

            if groups.filter(name='CONS-STR').exists() and not structures.count():
                msg = _("This field is mandatory for a user belonging to 'REF-CONS' group")
                self._errors['structures'] = self.error_class([msg])
                del cleaned_data["structures"]

            if structures.count() and not groups.filter(name__in=('REF-STR', 'CONS-STR')).exists():
                msg = _("The group 'REF-STR' or 'CONS-STR' is mandatory when you add a structure")
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
        inter_group = None
        try:
            inter_group = Group.objects.get(name='INTER')
        except Group.DoesNotExist:
            pass

        new_groups = set(self.data.get('groups', []))

        if inter_group:
            if self.request.user.is_high_school_manager():
                if not self.instance.groups.filter(name='INTER').exists():
                    new_groups.add(str(inter_group.id))

        # Username override except for high school students using EduConnect
        exceptions = [
            not self.instance.is_high_school_student(),
            not self.instance.get_high_school_student_record(),
            self.instance.get_high_school_student_record()
                and self.instance.high_school_student_record.highschool
                and not self.instance.high_school_student_record.highschool.uses_student_federation
        ]

        if any(exceptions):
            self.instance.username = self.instance.email

        # New account : send an account creation message
        user = self.instance

        if not user.creation_email_sent:
            if not user.establishment or not user.establishment.data_source_plugin:
                user.set_recovery_string()

            ret = user.send_message(self.request, "CPT_CREATE")
            if ret is None:
                self.instance.creation_email_sent = True

        self.instance = super().save(*args, **kwargs)

        if self.request.user.is_high_school_manager():
            if not self.instance.groups.filter(name='INTER').exists():
                self.instance.groups.add(inter_group)

        return self.instance

    class Meta(UserChangeForm.Meta):
        model = ImmersionUser
        fields = ("establishment", "username", "first_name", "last_name", "email", "is_active", "is_staff",
                  "is_superuser", "groups", "structures", "highschool")


class ImmersionUserGroupForm(forms.ModelForm):
    """
    Immersion Users Group form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)

        super().__init__(*args, **kwargs)

        self.fields["immersionusers"].queryset = ImmersionUser.objects\
            .annotate(cnt=Count('groups'))\
            .filter(cnt=1, groups__name='INTER')\
            .order_by("last_name", "first_name")

    class Meta:
        model = ImmersionUserGroup
        fields = '__all__'


class HighSchoolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.fields and self.fields.get('uai_codes'):
            self.fields['uai_codes'].queryset = UAI.objects.exclude(Q(city__isnull=True)|Q(city='')).order_by('city')

        if settings.USE_GEOAPI and self.instance.country == 'FR' and (not self.is_bound or self.errors):
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
                    label=_("Department"), widget=forms.Select(), choices=department_choices
                )
                self.fields['city'] = forms.TypedChoiceField(
                    label=_("City"), widget=forms.Select(), choices=city_choices
                )
                self.fields['zip_code'] = forms.TypedChoiceField(
                    label=_("Zip code"), widget=forms.Select(), choices=zip_choices
                )

        postbac_dependant_fields = ['mailing_list', 'logo', 'signature', 'certificate_header', 'certificate_footer']

        for field in postbac_dependant_fields:
            if not self.instance or (self.instance and not self.instance.postbac_immersion) \
                and self.fields.get(field):
                self.fields[field].disabled = True
                self.fields[field].help_text = \
                    _("This field is available when 'Offer post-bachelor immersions is enabled")

        # General settings dependant field
        try:
            w_agreement = GeneralSettings.get_setting(name="ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT")
            wo_agreement = GeneralSettings.get_setting(name="ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT")
        except Exception as e:
            raise forms.ValidationError(str(e)) from e

        # Both activated : option can be updated, else it's locked (XOR)
        if self.fields.get("with_convention"):
            self.fields["with_convention"].disabled = w_agreement ^ wo_agreement

            if self.fields["with_convention"].disabled:
                self.fields["with_convention"].initial = w_agreement
                self.fields["with_convention"].widget.attrs['checked'] = w_agreement

                self.fields["with_convention"].help_text = pgettext(
                    "convention",
                    """Always %s : this option cannot be changed due to high school agreements """
                    """options in general settings""") % w_agreement

                if w_agreement:
                    # field disabled and conventions activated : make convention dates required if active
                    try:
                        active = kwargs['data']['active']
                    except:
                        active = False

                    if active:
                        self.fields['convention_start_date'].required = True
                        self.fields['convention_end_date'].required = True
                else:
                    # field disabled and conventions deactivated : disabled convention dates
                    self.fields['convention_start_date'].disabled = True
                    self.fields['convention_end_date'].disabled = True

        # Federations fields
        try:
            agent_federation_setting = GeneralSettings.get_setting(name="ACTIVATE_FEDERATION_AGENT")
            educonnect_federation_setting = GeneralSettings.get_setting(name="ACTIVATE_EDUCONNECT")
        except Exception as e:
            raise forms.ValidationError(str(e)) from e

        if not educonnect_federation_setting:
            self.fields['uses_student_federation'].help_text = _(
                "This field cannot be changed because ACTIVATE_EDUCONNECT is not set"
            )
        elif self.instance.pk and self.instance.student_records.exists():
            # Disable student identity federation choice if the high school has students
            self.fields['uses_student_federation'].help_text = _(
                "This field cannot be changed because this high school already has student records"
            )

        if not agent_federation_setting:
            self.fields['uses_agent_federation'].help_text = _(
                "This field cannot be changed because ACTIVATE_FEDERATION_AGENT is not set"
            )

    """
    def clean_uses_student_federation(self):
        instance = getattr(self, 'instance', None)

        print(f"cleaned data uses_student_federation : {self.cleaned_data.get('uses_student_federation')}")

        if 'uses_student_federation' not in self.cleaned_data:
            if instance and instance.pk:
                return instance.uses_student_federation
            else:
                return False
        else:
            return self.cleaned_data['uses_student_federation']
    """

    def clean(self):
        valid_user = False
        cleaned_data = super().clean()

        active = cleaned_data.get("active", False)
        uses_student_federation = cleaned_data.get("uses_student_federation")
        uses_agent_federation = cleaned_data.get("uses_agent_federation")
        uai_codes = cleaned_data.get('uai_codes')

        try:
            user = self.request.user

            valid_groups = [
                user.is_superuser,
                user.is_operator(),
                user.is_master_establishment_manager(),
                user.is_high_school_manager() and user.highschool
            ]

            valid_user = any(valid_groups)
        except AttributeError as exc:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        try:
            agent_federation_setting = GeneralSettings.get_setting(name="ACTIVATE_FEDERATION_AGENT")
            educonnect_federation_setting = GeneralSettings.get_setting(name="ACTIVATE_EDUCONNECT")
        except Exception as e:
            raise forms.ValidationError(str(e)) from e

        # General settings dependant field
        if "with_convention" in cleaned_data:
            #TODO : rewrite clean() in MyHighSchoolForm
            try:
                w_agreement = GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT")
                wo_agreement = GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT")
            except Exception as e:
                raise forms.ValidationError() from e

            if w_agreement ^ wo_agreement:
                cleaned_data["with_convention"] = w_agreement

            if not cleaned_data["with_convention"]:
                cleaned_data["convention_start_date"] = None
                cleaned_data["convention_end_date"] = None
            elif active and (not cleaned_data.get("convention_start_date") \
                    or not cleaned_data.get("convention_end_date")):
                if 'convention_start_date' in self.fields and 'convention_end_date' in self.fields:
                    raise forms.ValidationError({
                        'convention_start_date': _("Both convention dates are required if 'convention' is checked"),
                        'convention_end_date': _("Both convention dates are required if 'convention' is checked")
                    })

        # Student identity federation (educonnect) : test only when setting is in use
        if educonnect_federation_setting:
            if (self.instance.pk and self.instance.student_records.exists()
                and uses_student_federation != self.instance.uses_student_federation):
                raise forms.ValidationError({
                    'uses_student_federation': _(
                        "You can't change this setting because this high school already has records."
                    ),
                })

            if cleaned_data.get('uses_student_federation', False) and not cleaned_data.get('uai_codes', ''):
                raise forms.ValidationError({
                    'uai_codes': _("This field is mandatory when using the student federation"),
                })

        if agent_federation_setting:
            if (self.instance.pk and self.instance.users.count()
                    and uses_agent_federation != self.instance.uses_agent_federation):
                raise forms.ValidationError({
                    'uses_agent_federation': _(
                        "You can't change this setting because this high school already has users."
                    ),
                })

        if uai_codes:
            for uai_code in uai_codes:
                if HighSchool.objects.filter(uai_codes=uai_code).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError({
                        'uai_codes': _(
                            "The uai code %s - %s is already associated with another high school"
                        ) % (uai_code.code, uai_code.label)
                    })

        return cleaned_data

    class Meta:
        model = HighSchool
        fields = ('active', 'postbac_immersion', 'label', 'country', 'address', 'address2', 'address3',
                  'department', 'zip_code', 'city', 'phone_number', 'fax', 'email', 'head_teacher_name',
                  'with_convention', 'convention_start_date', 'convention_end_date', 'signed_charter',
                  'mailing_list', 'badge_html_color', 'logo', 'signature', 'certificate_header',
                  'certificate_footer', 'uses_agent_federation', 'uses_student_federation',
                  'allow_individual_immersions', 'uai_codes')
        widgets = {
            'badge_html_color': TextInput(attrs={'type': 'color'}),
            'certificate_header': CKEditorWidget(),
            'certificate_footer': CKEditorWidget(),
        }


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

            # The superuser is the only user allowed to update available mail template variables
            if not self.request.user.is_superuser:
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
        # all_vars = re.findall(r"(\$\{[\w+\.]*\})", body)  # match for ${my_var}
        all_vars = re.findall(r"(\{\{ *[\w+\.]* *\}\})", body)  # match for {{ my_var }}
        unknown_vars = [v for v in all_vars if not MailTemplateVars.objects.filter(code__iexact=v.lower()).exists()]

        # Check for body syntax errors
        try:
            template.Template(body).render(template.Context())
        except template.TemplateSyntaxError as e:

            if "template_debug" in dir(e):
                before: str = e.template_debug["before"]
                line: int = 1 + before.count("<br>") + before.count("</br>")
                line += before.count("&lt;br&gt;") + before.count("&lt;/br&gt;")
                body_syntax_error_msg = _("The message body contains syntax error(s) : ")
                body_syntax_error_msg += _('at "%(pos)s" line %(line)s') % {
                    'pos': e.template_debug["during"],
                    'line': line
                }
                body_errors_list.append(self.error_class([body_syntax_error_msg]))
            else:
                body_syntax_error_msg = _("The message body contains syntax error(s) : ") + str(e)
                body_errors_list.append(self.error_class([body_syntax_error_msg]))

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
            'body': CKEditorWidget(),
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
            # allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in settings.CONTENT_TYPES]

            if document.content_type in settings.MIME_TYPES:
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
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
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
        widgets = {'content': CKEditorWidget}


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
            if document.content_type in settings.MIME_TYPES:
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
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = PublicDocument
        fields = '__all__'


class AttestationDocumentForm(forms.ModelForm):
    """
    Attestation document form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # amend default queryset
        default_queryset = self.fields["profiles"].queryset
        excludes = { 'code__in': [] }

        if not GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT"):
            excludes["code__in"].append("LYC_W_CONV")

        if not GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT"):
            excludes["code__in"].append("LYC_WO_CONV")

        self.fields["profiles"].queryset = default_queryset.exclude(**excludes)

    def clean_document(self):
        template = self.cleaned_data['template']
        if template and isinstance(template, UploadedFile):
            # See settings content types allowed
            if template.content_type in settings.MIME_TYPES:
                if template.size > int(settings.MAX_UPLOAD_SIZE):
                    raise forms.ValidationError(
                        _('Please keep filesize under %(maxupload)s. Current filesize %(current_size)s') % {
                            'maxupload': filesizeformat(settings.MAX_UPLOAD_SIZE),
                            'current_size': filesizeformat(template.size),
                        }
                    )
            else:
                raise forms.ValidationError(_('File type is not allowed'))
        return template

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        if not cleaned_data.get("profiles", None):
            raise forms.ValidationError(_("At least one profile is required"))

        return cleaned_data

    class Meta:
        model = AttestationDocument
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

        user = self.request.user

        # setting_type field only writable by admins and REF-TECs
        if not any([user.is_superuser, user.is_operator()]) and "setting_type" in self.fields:
            self.fields["setting_type"].disabled = True
            self.fields["setting_type"].help_text = _("Read only")


    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = any([
                user.is_superuser,
                user.is_operator(),
                user.is_master_establishment_manager() and self.instance.setting_type == GeneralSettings.FUNCTIONAL
            ])
        except AttributeError:
            pass

        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        try:
            # Settings that can't be deactivated because users already exist
            if cleaned_data['setting'] == 'ACTIVATE_STUDENTS' \
                and not cleaned_data['parameters']['value']:

                if ImmersionUser.objects.filter(groups__name='ETU').first():
                    raise forms.ValidationError(
                        _("Students users exist you can't deactivate students"))

            if cleaned_data['setting'] == 'ACTIVATE_VISITORS' \
                and not cleaned_data['parameters']['value']:

                if ImmersionUser.objects.filter(groups__name='VIS').first():
                    raise forms.ValidationError(
                        _("Visitors users exist you can't deactivate visitors"))

            # Check that at least one of these parameter is True
            if cleaned_data['setting'] in [
                'ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT', 'ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT'
            ]:
                # Value to save
                setting_name = cleaned_data['setting']
                value = cleaned_data['parameters']['value']

                try:
                    w_agreement = GeneralSettings.objects.get(setting="ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT")
                    w_agreement_v = w_agreement.parameters['value']
                except (GeneralSettings.DoesNotExist, KeyError):
                    raise ValidationError(
                        _("ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT general setting is missing or incorrect. Please fix.")
                    )

                try:
                    without_agreement = GeneralSettings.objects.get(setting="ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT")
                    without_agreement_v = without_agreement.parameters['value']
                except (GeneralSettings.DoesNotExist, KeyError):
                    raise ValidationError(
                        _("ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT general setting is missing or incorrect. Please fix.")
                    )

                raise_conditions = [
                    setting_name == 'ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT' and not value and not without_agreement_v,
                    setting_name == 'ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT' and not value and not w_agreement_v,
                ]

                if any(raise_conditions):
                    raise ValidationError(_(
                        """ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT and ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT """
                        """cannot be both set to False """)
                    )

                if setting_name == 'ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT' and not value and \
                    HighSchool.objects.filter(with_convention=True).exists():
                    raise ValidationError(_(
                        """This parameter can't be set to False : there are high schools """
                        """with agreements in database, please update or delete these first"""
                    ))

                if setting_name == 'ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT' and not value and \
                    HighSchool.objects.filter(with_convention=False).exists():
                    raise ValidationError(_(
                        """This parameter can't be set to False : there are high schools """
                        """without agreements in database, please update or delete these first"""
                    ))

            # ACTIVATE_TRAINING_QUOTAS value constraints
            if cleaned_data['setting'] == 'ACTIVATE_TRAINING_QUOTAS':
                dict_value = cleaned_data['parameters']['value']

                if dict_value.get('activate', False):
                    try:
                        default_quota = int(dict_value.get('default_quota'))
                    except (ValueError, TypeError):
                        raise ValidationError(_("A default quota value is mandatory"))

                    if default_quota <= 0:
                        raise ValidationError(_("The default quota value must be a positive integer > 0"))
                else:
                    cleaned_data['parameters']['value']['activate'] = False
                    cleaned_data['parameters']['value']['default_quota'] = 2

            if cleaned_data['setting'] == 'ACTIVATE_FEDERATION_AGENT':
                value = cleaned_data['parameters']['value']
                if not value and HighSchool.objects.filter(uses_agent_federation=True).exists():
                    raise ValidationError(_(
                        """This parameter can't be set to False : some high schools """
                        """use the agent federation to authenticate their users"""
                    ))

            if cleaned_data['setting'] == 'ACTIVATE_EDUCONNECT':
                value = cleaned_data['parameters']['value']
                if not value and HighSchool.objects.filter(uses_student_federation=True).exists():
                    raise ValidationError(_(
                        """This parameter can't be set to False : some high schools """
                        """use the student identity federation to authenticate their students"""
                    ))

        except KeyError:
            raise ValidationError('')

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
            if not logo.content_type in CertificateLogo.ALLOWED_TYPES.values():
                raise forms.ValidationError(_('File type is not allowed'))

        return logo

    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
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
            if not signature.content_type in CertificateSignature.ALLOWED_TYPES.values():
                raise forms.ValidationError(_('File type is not allowed'))

        return signature

    def clean(self):
        cleaned_data = super().clean()

        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_master_establishment_manager() or user.is_operator()
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
                self.initial['active'] = True
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
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            if HighSchoolStudentRecord.objects.filter(post_bachelor_level=self.instance).exists():
                self.initial['active'] = True
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
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            if StudentRecord.objects.filter(level=self.instance).exists():
                self.initial['active'] = True
                self.fields['active'].disabled = True
                self.fields['active'].help_text = _("Field locked : a student record uses this level")

    class Meta:
        model = StudentLevel
        fields = '__all__'


class CustomThemeFileForm(forms.ModelForm):
    """
    Custome theme file form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_file(self):
        file = self.cleaned_data['file']
        if file and isinstance(file, UploadedFile):
            # TODO: check later cause text/javascript is deprecated !
            #mimetypes.add_type("text/javascript", ".js")
            #allowed_content_type = [mimetypes.types_map[f'.{c}'] for c in ['png', 'jpeg', 'jpg', 'ico', 'css', 'js']]
            if not file.content_type in CustomThemeFile.ALLOWED_TYPES.values():
                raise forms.ValidationError(_('File type is not allowed'))

        return file

    def clean(self):
        cleaned_data = super().clean()
        valid_user = False

        try:
            user = self.request.user
            valid_user = user.is_superuser or user.is_operator()
        except AttributeError:
            pass


        if cleaned_data["type"] == 'FAVICON' and CustomThemeFile.objects.filter(type='FAVICON').first():
            raise forms.ValidationError(
                _("A favicon already exists"))


        if not valid_user:
            raise forms.ValidationError(_("You don't have the required privileges"))

        return cleaned_data

    class Meta:
        model = CustomThemeFile
        fields = '__all__'


class FaqEntryAdminForm(forms.ModelForm):
    """
    Faq entry form
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


    class Meta:
        model = FaqEntry
        fields = '__all__'
        widgets = {'answer': CKEditorWidget,}


class ProfileForm(forms.ModelForm):
    """
    User Profiles form class
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Profile
        fields = '__all__'


class ScheduledTaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Limit command choice to the schedulable ones

        choices_dict = MultiValueDict()

        for command, app in get_commands().items():
            if app.startswith("immersionlyceens"):
                try:
                    CommandClass = load_command_class(app, command)
                    if CommandClass.is_schedulable():
                        choices_dict.appendlist(app, command)
                except AttributeError:
                    # 'is_schedulable' is missing : nothing to do
                    pass

        choices = []
        for key in choices_dict.keys():
            commands = choices_dict.getlist(key)
            commands.sort()
            choices.append([key, [[c, c] for c in commands]])

        # When readonly (for some groups), command_name is not in self.fields
        if 'command_name' in self.fields:
            choices.insert(0, ('', '---------'))
            self.fields["command_name"].widget = forms.widgets.Select(choices=choices)

        # Other field options
        if "frequency" in self.fields:
            self.fields["frequency"].help_text = _("If not empty, uses 'Execution time' field for the first execution")

        if "time" in self.fields:
            # Time field : remove seconds
            self.fields["time"].widget.format = "%H:%M"
            self.fields["time"].help_text = _("Minutes will be rounded to force 5 min steps")


    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("date") and cleaned_data.get("frequency"):
            raise forms.ValidationError(_("Date and frequency can't be both set"))

        # Input format can take seconds and microseconds : force clean them
        # + force 5 min steps to avoid running master cron every minute
        if cleaned_data.get("time"):
            cleaned_data["time"] = cleaned_data["time"].replace(
                minute=cleaned_data["time"].minute - (cleaned_data["time"].minute % 5),
                second=0,
                microsecond=0
            )

        return cleaned_data

    class Meta:
        model = ScheduledTask
        fields = '__all__'
