import json
from datetime import datetime, timedelta
from typing import Any, Dict

from ckeditor.widgets import CKEditorWidget
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q, Sum, Min, Max
from django.forms.widgets import DateInput, TimeInput
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _, ngettext
from django_countries.fields import CountryField
from rest_framework.exceptions import ValidationError

from ..user.models import Student
from ...libs.utils import get_general_setting
from ..immersion.forms import StudentRecordForm
from ..immersion.models import HighSchoolStudentRecord, StudentRecord
from .admin_forms import HighSchoolForm, TrainingForm
from .models import (
    BachelorMention, BachelorType, Building, Campus, Course, CourseType,
    Establishment, GeneralBachelorTeaching, HighSchool, HighSchoolLevel,
    Immersion, ImmersionUser, OffOfferEvent, OffOfferEventType, Period,
    PostBachelorLevel, Slot, Structure, StudentLevel, Training, UniversityYear
)


class CourseForm(forms.ModelForm):
    establishment = forms.ModelChoiceField(queryset=Establishment.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["training"].queryset = self.fields["training"].queryset.filter(active=True)

        for field_name, field in self.fields.items():
            if not field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-control'})

        if self.request:
            can_choose_establishment = any([
                self.request.user.is_establishment_manager(),
                self.request.user.is_master_establishment_manager(),
                self.request.user.is_operator(),
                self.request.user.is_structure_manager()
            ])

            if can_choose_establishment:
                allowed_establishments = Establishment.activated.filter(
                    is_host_establishment=True
                ).user_establishments(self.request.user)
                self.fields["establishment"].queryset = allowed_establishments.order_by('code', 'label')
            else:
                allowed_establishments = Establishment.objects.none()

            allowed_structs = self.request.user.get_authorized_structures()
            self.fields["structure"].queryset = allowed_structs.order_by('code', 'label')

            if allowed_establishments.count() == 1:
                self.fields["establishment"].initial = allowed_establishments.first().id
                self.fields["establishment"].empty_label = None
            elif self.instance.structure:
                self.fields["establishment"].initial = self.instance.structure.establishment.id

            if allowed_structs.count() == 1:
                self.fields["structure"].initial = allowed_structs.first().id
                self.fields["structure"].empty_label = None

            allowed_highschools = HighSchool.objects.none()

            if self.request.user.is_high_school_manager() and self.request.user.highschool \
                and self.request.user.highschool.postbac_immersion:
                allowed_highschools = HighSchool.agreed.filter(pk=self.request.user.highschool.id)
                self.fields['highschool'].empty_label = None
            elif self.request.user.is_master_establishment_manager() or self.request.user.is_operator():
                allowed_highschools = HighSchool.agreed.filter(postbac_immersion=True)

            self.fields["highschool"].queryset = allowed_highschools.order_by('city', 'label')

            if self.instance.id and not self.request.user.has_course_rights(self.instance.id):
                for field in self.fields:
                    self.fields[field].disabled = True
        else:
            self.fields["structure"].queryset = self.fields["structure"].queryset.order_by('code', 'label')


    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')

        if start and end and end < start:
            raise forms.ValidationError(_("The end date must be after the start date."))

        try:
            active_year = UniversityYear.objects.get(active=True)
        except UniversityYear.MultipleObjectsReturned:
            raise forms.ValidationError(_("Error : multiple active university years"))
        except UniversityYear.DoesNotExist:
            raise forms.ValidationError(_("Error : can't find any active university year"))

        if active_year.start_date and active_year.end_date:
            if not (active_year.start_date <= datetime.today().date() <= active_year.end_date):
                raise forms.ValidationError(
                    _("Error : a course can only be created between start and end of the active university year")
                )
        else:
            raise forms.ValidationError(_("Error : dates of active university year improperly configured"))

        # Check user rights
        if self.request:
            highschool = cleaned_data.get("highschool")
            training = cleaned_data['training']
            course_structs = training.structures.all()

            if not self.request.user.is_superuser:
                if self.request.user.is_establishment_manager():
                    allowed_structs = self.request.user.get_authorized_structures()
                    if not (course_structs & allowed_structs).exists():
                        raise forms.ValidationError(_("You don't have enough privileges to update this course"))
                if self.request.user.is_high_school_manager() and self.request.user.highschool:
                    allowed_highschools = HighSchool.agreed.filter(pk=self.request.user.highschool.id)
                    if not allowed_highschools.filter(pk=highschool.id).exists():
                        raise forms.ValidationError(_("You don't have enough privileges to update this course"))

        return cleaned_data

    class Meta:
        model = Course
        fields = ('id', 'label', 'url', 'published', 'start_date', 'end_date', 'training', 'structure', 'establishment', 'highschool')
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format="%Y-%m-%dT%H:%M"),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'},format="%Y-%m-%dT%H:%M"),
        }


class SlotForm(forms.ModelForm):
    establishment = forms.ModelChoiceField(queryset=Establishment.objects.none(), required=False)
    structure = forms.ModelChoiceField(queryset=Structure.objects.all(), required=False)
    training = forms.ModelChoiceField(queryset=Training.objects.all(), required=False)
    highschool = forms.ModelChoiceField(queryset=HighSchool.objects.all(), required=False)
    repeat = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)

        try:
            getattr(self, "slot_dates")
        except AttributeError:
            self.slot_dates = []

        if "published" in self.data:
            self.fields["period"].required = self.data.get("published", False)
        elif self.instance and self.instance.published:
            self.fields["period"].required = True

        if self.instance and self.instance.date:
            self.fields["period"].help_text = _("Available periods depend on the slot date")

        course = self.instance.course if self.instance and self.instance.course_id else None

        for elem in ['establishment', 'highschool', 'structure', 'event', 'training', 'course', 'course_type',
            'campus', 'building', 'room', 'start_time', 'end_time', 'n_group_places', 'n_places',
            'additional_information', 'url', 'allowed_establishments', 'allowed_highschools',
            'allowed_highschool_levels', 'allowed_student_levels', 'allowed_post_bachelor_levels',
            'allowed_bachelor_types', 'allowed_bachelor_mentions', 'allowed_bachelor_teachings',
            'registration_limit_delay', 'cancellation_limit_delay', 'period', 'place', 'group_mode',
            'speakers']:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

        # n_places widget
        try:
            max_slot_places = int(get_general_setting('MAX_SLOT_PLACES'))
        except (ValueError, NameError):
            max_slot_places = 200

        self.fields['n_places'].widget = forms.NumberInput(attrs={'min': 1, 'max': max_slot_places})

        # Disable autocomplete for date fields
        self.fields['date'].widget.attrs.update({'autocomplete': 'off'})

        can_choose_establishment = any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator(),
            self.request.user.is_structure_manager()
        ])

        self.fields["highschool"].queryset = HighSchool.agreed.filter(postbac_immersion=True)
        self.fields["allowed_highschools"].queryset = HighSchool.agreed.order_by('city', 'label')

        # Level restrictions
        self.fields["allowed_highschool_levels"].queryset = HighSchoolLevel.objects\
            .filter(active=True).order_by('order')
        self.fields["allowed_student_levels"].queryset = StudentLevel.objects\
            .filter(active=True).order_by('order')
        self.fields["allowed_post_bachelor_levels"].queryset = PostBachelorLevel.objects\
            .filter(active=True).order_by('order')

        # Bachelor restrictions
        self.fields["allowed_bachelor_types"].queryset = BachelorType.objects\
            .filter(active=True).order_by('label')
        self.fields["allowed_bachelor_mentions"].queryset = BachelorMention.objects\
            .filter(active=True).order_by('label')
        self.fields["allowed_bachelor_teachings"].queryset = GeneralBachelorTeaching.objects\
            .filter(active=True).order_by('label')

        if can_choose_establishment:
            allowed_establishments = Establishment.activated.user_establishments(self.request.user)
            self.fields["establishment"].queryset = allowed_establishments.filter(
                is_host_establishment=True
            ).order_by('code', 'label')
        else:
            allowed_establishments = Establishment.objects.none()

        if allowed_establishments.count() == 1:
            self.fields["establishment"].initial = allowed_establishments.first().id
            self.fields["establishment"].empty_label = None
        elif course and course.structure:
            self.fields["establishment"].initial = course.structure.establishment.id

        allowed_structs = self.request.user.get_authorized_structures()
        self.fields["structure"].queryset = allowed_structs.order_by('code', 'label')

        if allowed_structs.count() == 1:
            self.fields["structure"].initial = allowed_structs.first().id
            self.fields["structure"].empty_label = None

        # Update valid choices (useful when validating the form)
        structure = self.data.get("structure") or (self.instance and self.instance.course_id and course.structure)
        if structure:
            self.fields["training"].queryset = Training.objects.filter(structures=structure)

        if course:
            self.fields["structure"].initial = course.structure.id if course.structure else None
            self.fields["highschool"].initial = course.highschool.id if course.highschool else None
            self.fields["training"].initial = course.training.id

        allowed_highschools = HighSchool.objects.none()

        if self.request.user.is_high_school_manager() and self.request.user.highschool \
                and self.request.user.highschool.postbac_immersion:
            allowed_highschools = HighSchool.agreed.filter(pk=self.request.user.highschool.id)
            self.fields['highschool'].empty_label = None
        elif self.request.user.is_master_establishment_manager() or self.request.user.is_operator():
            allowed_highschools = HighSchool.agreed.filter(postbac_immersion=True)

        self.fields["highschool"].queryset = allowed_highschools.order_by('city', 'label')

        # course type filter
        self.fields['course_type'].queryset = CourseType.objects.filter(active=True).order_by('label')
        # campus filter
        self.fields['campus'].queryset = Campus.objects.filter(active=True).order_by('label')
        # building filter
        self.fields['building'].queryset = Building.objects.filter(active=True).order_by('label')

        if instance:
            self.fields['date'].value = instance.date

            if instance.pk:
                # can't change some fields if the slot already has immersions
                if instance.immersions.exists() or instance.group_immersions.exists():
                    self.fields['period'].disabled = True

                if instance.immersions.exists():
                    self.fields['allow_individual_registrations'].disabled = True
                    self.fields['allow_individual_registrations'].help_text = gettext(
                        "Read only - slot already has registrations"
                    )
                if instance.group_immersions.exists():
                    self.fields['allow_group_registrations'].disabled = True
                    self.fields['allow_group_registrations'].help_text = gettext(
                        "Read only - slot already has registrations"
                    )
                    self.fields['group_mode'].disabled = True

        self.fields["repeat"].widget = forms.DateInput(
            format='%d/%m/%Y',
            attrs={
                'placeholder': _('dd/mm/yyyy'),
                'class': 'datepicker form-control',
                'autocomplete': 'off'
            }
        )

        # registration and cancellation limit delays
        try:
            self.fields["registration_limit_delay"].initial = get_general_setting("SLOT_REGISTRATION_LIMIT")
        except (ValueError, NameError):
            self.fields["registration_limit_delay"].initial = 0

        try:
            self.fields["cancellation_limit_delay"].initial = get_general_setting("SLOT_CANCELLATION_LIMIT")
        except (ValueError, NameError):
            self.fields["cancellation_limit_delay"].initial = 0

        # Course Slot : limit place choices
        self.fields['place'].choices = Slot.PLACES[0:2]

    def clean_restrictions(self, cleaned_data):
        # Establishment resrtictions fields
        establishments_restrictions = cleaned_data.get('establishments_restrictions')
        allowed_establishments = cleaned_data.get('allowed_establishments')
        allowed_highschools = cleaned_data.get('allowed_highschools')

        # Level restrictions fields
        levels_restrictions = cleaned_data.get('levels_restrictions')
        allowed_highschool_levels = cleaned_data.get('allowed_highschool_levels')
        allowed_student_levels = cleaned_data.get('allowed_student_levels')
        allowed_post_bachelor_levels = cleaned_data.get('allowed_post_bachelor_levels')

        # Bachelor types restrictions fields
        bachelors_restrictions = cleaned_data.get('bachelors_restrictions')
        allowed_bachelor_types = cleaned_data.get('allowed_bachelor_types')
        allowed_bachelor_mentions = cleaned_data.get('allowed_bachelor_mentions')
        allowed_bachelor_teachings = cleaned_data.get('allowed_bachelor_teachings')

        # Controls
        if establishments_restrictions and not allowed_establishments and not allowed_highschools:
            cleaned_data["establishments_restrictions"] = False

        if levels_restrictions and not allowed_highschool_levels and not allowed_student_levels \
                and not allowed_post_bachelor_levels:
            cleaned_data["levels_restrictions"] = False

        if bachelors_restrictions and not any([
            allowed_bachelor_types, allowed_bachelor_mentions, allowed_bachelor_teachings]):
            cleaned_data["bachelors_restrictions"] = False

        return cleaned_data

    def clean_fields(self, cleaned_data):
        # Remote slot : remove unnecessary fields
        place = cleaned_data.get('place', Slot.FACE_TO_FACE)

        if place == Slot.REMOTE:
            for field in ['campus', 'building', 'room']:
                cleaned_data[field] = None

        elif place == Slot.OUTSIDE:
            for field in ['campus', 'building', 'url']:
                cleaned_data[field] = None

        elif place == Slot.FACE_TO_FACE:
            cleaned_data['url'] = None

        return cleaned_data

    def clean_registrations(self, cleaned_data):
        allow_individual_registrations = cleaned_data.get('allow_individual_registrations')
        allow_group_registrations = cleaned_data.get('allow_group_registrations')
        group_mode = cleaned_data.get('group_mode')
        n_places = cleaned_data.get('n_places', 0)
        n_group_places = cleaned_data.get('n_group_places', 0)
        published = cleaned_data.get('published', None)

        try:
            max_slot_places = int(get_general_setting('MAX_SLOT_PLACES'))
        except (ValueError, NameError):
            max_slot_places = 200

        # Groups settings
        try:
            enabled_groups = get_general_setting("ACTIVATE_COHORT")
        except (ValueError, NameError):
            enabled_groups = False

        if not enabled_groups:
            cleaned_data["group_mode"], group_mode = None, None
            cleaned_data["allow_group_registrations"], allow_group_registrations = False, False
            cleaned_data["allow_individual_registrations"], allow_individual_registrations = True, True
            cleaned_data["n_group_places"], n_group_places = None, None

        if enabled_groups and not any([allow_individual_registrations, allow_group_registrations]):
            raise forms.ValidationError(
                _("You must allow at least one of individual or group registrations")
            )

        if published:
            if (not enabled_groups or allow_individual_registrations) and (not n_places or n_places <= 0):
                self.add_error(
                    'n_places',
                    _("Please enter a valid number for 'n_places' field")
                )

            if (not enabled_groups or allow_individual_registrations) and n_places > max_slot_places:
                self.add_error(
                    'n_places',
                    _("The 'n_places' field must not exceed %s" % max_slot_places)
                )

            if (enabled_groups and allow_group_registrations and (not n_group_places or n_group_places <= 0)):
                self.add_error(
                    'n_group_places',
                    _("Please enter a valid number for 'n_group_places' field")
                )

        # Can't deactivate individual registrations if slot has one immersion
        if self.instance.pk:
            if Immersion.objects.filter(slot=self.instance) and not allow_individual_registrations:
                # if self.instance.immersions.exists() and not allow_individual_registrations:
                self.add_error(
                    'allow_individual_registrations',
                    _("The slot already has registered students, individual registrations can't be disabled")
                )

            # Can't deactivate group registrations if slot has one group
            if self.instance.group_immersions.exists() and not allow_group_registrations:
                self.add_error(
                    'allow_group_registrations',
                    _("The slot already has registered groups, groups registrations can't be disabled")
                )

            # Can't set n_places lower than actual immersions
            if (allow_individual_registrations and n_places
                    and n_places < self.instance.immersions.filter(cancellation_type__isnull=True).count()):
                self.add_error(
                    'n_places',
                    _("You can't set places value lower than actual individual immersions")
                )

            # Can't set n_group_places lower than actual group immersions
            if enabled_groups and allow_group_registrations and n_group_places:
                group_queryset = self.instance.group_immersions.aggregate(
                    students_count=Sum(
                        'students_count',
                        filter=Q(cancellation_type__isnull=True),
                        distinct=True
                    ),
                    guides_count=Sum(
                        'guides_count',
                        filter=Q(cancellation_type__isnull=True),
                        distinct=True
                    )
                )

                people_count = (group_queryset['students_count'] or 0) + (group_queryset['guides_count'] or 0)

                if people_count > n_group_places:
                    self.add_error(
                        'n_group_places',
                        _("You can't set group places value lower than actual registered group(s) people count")
                    )

        return cleaned_data

    def clean(self):
        cleaned_data = super().clean()

        structure = cleaned_data.get('structure')
        published = cleaned_data.get('published', None)
        place = cleaned_data.get('place')
        _date = cleaned_data.get('date')
        period = cleaned_data.get('period')
        start_time = cleaned_data.get('start_time', 0)

        cleaned_data = self.clean_restrictions(cleaned_data)
        cleaned_data = self.clean_fields(cleaned_data)
        cleaned_data = self.clean_registrations(cleaned_data)

        # Slot repetition
        if cleaned_data.get('repeat'):
            self.slot_dates = self.request.POST.getlist("slot_dates[]")

        # Invalid value for a Course slot
        if place == Slot.OUTSIDE:
            self.add_error("place", _("Invalid option for a course slot"))

        if published:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['course', 'course_type', 'date', 'period', 'start_time', 'end_time', 'speakers']

            if place == Slot.FACE_TO_FACE:
                if structure:
                    m_fields += ['campus', 'building']

                m_fields.append('room')
            elif place == Slot.REMOTE:
                m_fields.append('url')

            # Field level error
            for field in m_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _("This field is required"))

            if period and _date:
                try:
                    period = Period.from_date(pk=period.pk, date=_date)
                except Period.DoesNotExist:
                    raise forms.ValidationError(
                        _("Invalid date for selected period : please check periods settings")
                    )

            # Generic field error
            if not all(cleaned_data.get(e) for e in m_fields):
                raise forms.ValidationError(_('Required fields are not filled in'))

            if _date == timezone.localdate() and start_time <= timezone.now().time():
                self.add_error(
                    'start_time',
                    _("Slot is set for today : please enter a valid start_time")
                )

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            self.add_error(
                'start_time',
                _('Error: Start time must be set before end time')
            )

        return cleaned_data

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        if instance.course and not instance.course.published and instance.published:
            instance.course.published = True
            instance.course.save()
            messages.success(self.request, _("Course published"))

        if instance.course and instance.published :
            bounds = Slot.objects.filter(course=instance.course).aggregate(
                date_min=Min('date'),
                date_max=Max('date'),
            )

            instance.course.first_slot_date = bounds['date_min']
            instance.course.last_slot_date = bounds['date_max']

            if instance.course.start_date:
                if instance.date < instance.course.start_date.date():
                    messages.warning(
                        self.request,
                        _("The slot will be saved, but the course publication start date do not match the slot date. The course \
                         publication start date will be changed automatically. Remember to adjust it yourself so that \
                         registrations can proceed without problems.")
                    )
                if bounds['date_min'] and instance.course.start_date.date() > bounds['date_min']:
                    instance.course.start_date = bounds['date_min'] - timedelta(days=7)

            if instance.course.end_date:
                if instance.date > instance.course.end_date.date():
                    messages.warning(
                        self.request,
                        _("The slot will be saved, but the course publication end date do not match the slot date. The course \
                         publication end date will be changed automatically. Remember to adjust it yourself so that \
                         registrations can proceed without problems.")
                    )
                if bounds['date_max'] and instance.course.end_date.date() < bounds['date_max']:
                    instance.course.end_date = bounds['date_max']

            instance.course.save()

        if self.data.get("repeat"):
            # Careful with date formats, especially with unit tests
            try:
                repeat_limit_date = datetime.strptime(self.data.get("repeat"), "%d/%m/%Y").date()
            except:
                repeat_limit_date = datetime.strptime(self.data.get("repeat"), "%Y-%m-%d").date()

            new_dates = self.slot_dates

            try:
                university_year = UniversityYear.objects.get(active=True)
                new_slot_template = Slot.objects.get(pk=instance.pk)
            except (Slot.DoesNotExist, UniversityYear.DoesNotExist):
                # Nothing to do here but we should never get there
                pass
            else:
                # Store current slot related objects
                slot_speakers = [speaker for speaker in new_slot_template.speakers.all()]
                slot_allowed_establishments = [
                    e for e in new_slot_template.allowed_establishments.filter(is_host_establishment=True)
                ]
                slot_allowed_highschools = [h for h in new_slot_template.allowed_highschools.all()]
                slot_allowed_highschool_levels = [l for l in new_slot_template.allowed_highschool_levels.all()]
                slot_allowed_student_levels = [l for l in new_slot_template.allowed_student_levels.all()]
                slot_allowed_post_bachelor_levels = [l for l in new_slot_template.allowed_post_bachelor_levels.all()]
                slot_allowed_bachelor_types = [l for l in new_slot_template.allowed_bachelor_types.all()]
                slot_allowed_bachelor_mentions = [l for l in new_slot_template.allowed_bachelor_mentions.all()]
                slot_allowed_bachelor_teachings = [l for l in new_slot_template.allowed_bachelor_teachings.all()]

                for new_date in new_dates:
                    try:
                        parsed_date = datetime.strptime(new_date, "%d/%m/%Y").date()
                        period = instance.period
                        if not period.immersion_start_date <= parsed_date <= period.immersion_end_date:
                            continue
                    except (TypeError, ValueError):
                        pass
                    else:
                        # Duplicate slot only if new dates match the current period
                        conditions = [
                            parsed_date <= university_year.end_date,
                            parsed_date <= instance.period.immersion_end_date,
                            parsed_date <= repeat_limit_date
                        ]

                        if all(conditions):
                            new_slot_template.pk = None
                            new_slot_template.date = parsed_date
                            new_slot_template.save()
                            new_slot_template.speakers.add(*slot_speakers)
                            new_slot_template.allowed_establishments.add(*slot_allowed_establishments)
                            new_slot_template.allowed_highschools.add(*slot_allowed_highschools)
                            new_slot_template.allowed_highschool_levels.add(*slot_allowed_highschool_levels)
                            new_slot_template.allowed_student_levels.add(*slot_allowed_student_levels)
                            new_slot_template.allowed_post_bachelor_levels.add(*slot_allowed_post_bachelor_levels)
                            new_slot_template.allowed_bachelor_types.add(*slot_allowed_bachelor_types)
                            new_slot_template.allowed_bachelor_mentions.add(*slot_allowed_bachelor_mentions)
                            new_slot_template.allowed_bachelor_teachings.add(*slot_allowed_bachelor_teachings)

                            messages.success(self.request, _("Course slot \"%s\" created.") % new_slot_template)

        return instance

    class Meta:
        model = Slot
        fields = ('id', 'establishment', 'structure', 'highschool', 'event', 'training', 'course',
            'course_type', 'campus', 'building', 'room', 'url', 'date', 'start_time', 'end_time', 'n_places',
            'additional_information', 'published', 'period', 'establishments_restrictions', 'levels_restrictions',
            'bachelors_restrictions', 'allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels',
            'allowed_student_levels', 'allowed_post_bachelor_levels', 'allowed_bachelor_types',
            'allowed_bachelor_mentions', 'allowed_bachelor_teachings', 'speakers', 'repeat', 'registration_limit_delay',
            'cancellation_limit_delay', 'period', 'n_group_places', 'allow_individual_registrations',
            'allow_group_registrations', 'group_mode', 'public_group', 'place'
        )

        widgets = {
            'additional_information': forms.Textarea(attrs={'placeholder': _('Enter additional information'),}),
            'room': forms.TextInput(attrs={'placeholder': _('Enter the room name')}),
            'date': forms.DateInput(
                format='%d/%m/%Y', attrs={'placeholder': _('dd/mm/yyyy'), 'class': 'datepicker form-control'}
            ),
            'start_time': TimeInput(format='%H:%M'),
            'end_time': TimeInput(format='%H:%M'),
        }

        localized_fields = ('date', 'repeat')


class SlotMassUpdateForm(forms.Form):
    mass_choices = (
        ('keep', _('Keep each value')),
        ('update', _('Update all')),
    )

    course_type = forms.ModelChoiceField(queryset=CourseType.objects.filter(active=True), required=False)
    mass_course_type = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    campus = forms.ModelChoiceField(queryset=Campus.objects.filter(active=True), required=False)
    mass_campus = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    building = forms.ModelChoiceField(queryset=Building.objects.filter(active=True), required=False)
    mass_building = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    room = forms.CharField(max_length=128, required=False) # also known as 'meeting place'
    mass_room = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    start_time = forms.TimeField(required=False)
    mass_start_time = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    end_time = forms.TimeField(required=False)
    mass_end_time = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    registration_limit_delay = forms.IntegerField(required=False)
    mass_registration_limit_delay = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    cancellation_limit_delay = forms.IntegerField(required=False)
    mass_cancellation_limit_delay = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    speakers = forms.ModelMultipleChoiceField(queryset=ImmersionUser.objects.none(), required=False)
    mass_speakers = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    allow_individual_registrations = forms.BooleanField(required=False)
    mass_allow_individual_registrations = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    allow_group_registrations = forms.BooleanField(required=False)
    mass_allow_group_registrations = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    group_mode = forms.ChoiceField(choices=Slot.GROUP_MODES)
    mass_group_mode = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    n_places = forms.IntegerField(required=False)
    mass_n_places = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    n_group_places = forms.IntegerField(required=False)
    mass_n_group_places = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    public_group = forms.BooleanField(required=False)
    mass_public_group = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    additional_information = forms.CharField(required=False)
    mass_additional_information = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    establishments_restrictions = forms.BooleanField(required=False)
    mass_establishments_restrictions = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    levels_restrictions = forms.BooleanField(required=False)
    mass_levels_restrictions = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    bachelors_restrictions = forms.BooleanField(required=False)
    mass_bachelors_restrictions = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))
    allowed_establishments = forms.ModelMultipleChoiceField(queryset=Establishment.objects.filter(active=True), required=False)
    allowed_highschools = forms.ModelMultipleChoiceField(queryset=HighSchool.objects.filter(active=True), required=False)
    allowed_highschool_levels = forms.ModelMultipleChoiceField(queryset=HighSchoolLevel.objects.filter(active=True), required=False)
    allowed_student_levels = forms.ModelMultipleChoiceField(queryset=StudentLevel.objects.filter(active=True), required=False)
    allowed_post_bachelor_levels = forms.ModelMultipleChoiceField(queryset=PostBachelorLevel.objects.filter(active=True), required=False)
    allowed_bachelor_types = forms.ModelMultipleChoiceField(queryset=BachelorType.objects.filter(active=True), required=False)
    allowed_bachelor_mentions = forms.ModelMultipleChoiceField(queryset=BachelorMention.objects.filter(active=True), required=False)
    allowed_bachelor_teachings = forms.ModelMultipleChoiceField(queryset=GeneralBachelorTeaching.objects.filter(active=True), required=False)
    published = forms.BooleanField(required=False)
    mass_published = forms.CharField(widget=forms.RadioSelect(choices=mass_choices))

    def __init__(self, *args, **kwargs):
        establishment = kwargs.pop("establishment", None)
        speakers = kwargs.pop("speakers", None)

        super().__init__(*args, **kwargs)

        # set querysets if all selected slots share some values
        if speakers:
            self.fields["speakers"].queryset = ImmersionUser.objects.filter(pk__in=speakers)

        if establishment:
            self.fields["campus"].queryset = Campus.objects.filter(active=True, establishment_id=establishment)
        else:
            # Multiple establishments : can't update campus/building
            self.fields["campus"].disabled = True
            self.fields["building"].disabled = True

        # Widgets
        try:
            max_slot_places = int(get_general_setting('MAX_SLOT_PLACES'))
        except (ValueError, NameError):
            max_slot_places = 200

        self.fields['start_time'].widget = TimeInput(format='%H:%M')
        self.fields['end_time'].widget = TimeInput(format='%H:%M')

        self.fields['room'].widget = forms.TextInput(attrs={'placeholder': _('Enter the room name')})
        self.fields['n_places'].widget = forms.NumberInput(attrs={'min': 1, 'max': max_slot_places})
        self.fields['additional_information'].widget = forms.Textarea(attrs={'placeholder': _('Enter additional information'),})

        for elem in ['course_type', 'campus', 'building', 'room', 'start_time', 'end_time', 'n_group_places',
                     'n_places', 'additional_information', 'allowed_establishments', 'allowed_highschools',
                     'allowed_highschool_levels', 'allowed_student_levels', 'allowed_post_bachelor_levels',
                     'allowed_bachelor_types', 'allowed_bachelor_mentions', 'allowed_bachelor_teachings',
                     'registration_limit_delay', 'cancellation_limit_delay', 'group_mode', 'speakers']:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})


class OffOfferEventSlotForm(SlotForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["highschool"].queryset = HighSchool.agreed\
            .filter(events__isnull=False)\
            .distinct()\
            .order_by('city', 'label')

        allowed_establishments = Establishment.activated.user_establishments(self.request.user).filter(
            is_host_establishment=True
        )
        self.fields["establishment"].queryset = allowed_establishments.order_by('code', 'label')

        allowed_structs = self.request.user.get_authorized_structures()
        self.fields["structure"].queryset = allowed_structs.order_by('code', 'label')

        if not self.request.user.is_superuser:
            if self.request.user.is_high_school_manager():
                self.fields["highschool"].queryset = HighSchool.objects.filter(id=self.request.user.highschool.id)
                self.fields["highschool"].empty_label = None

            if self.request.user.is_structure_manager():
                self.fields["structure"].initial = self.fields["structure"].queryset.first()
                self.fields["structure"].empty_label = None
            else:
                self.fields["structure"].initial = None
                self.fields["structure"].empty_label = "---------"

        event = self.instance.event if self.instance and self.instance.event_id else None

        if event:
            self.fields["structure"].initial = event.structure.id if event.structure else None
            self.fields["highschool"].initial = event.highschool.id if event.highschool else None
            self.fields["establishment"].initial = event.establishment.id if event.establishment else None

        # Event Slot : no choices limit
        self.fields['place'].choices = Slot.PLACES

    def clean(self):
        cleaned_data = super(forms.ModelForm, self).clean()
        event = cleaned_data.get('event')
        published = cleaned_data.get('published', None)
        place = cleaned_data.get('place')
        period = cleaned_data.get('period', None)
        start_time = cleaned_data.get('start_time', None)
        _date = cleaned_data.get('date')

        cleaned_data = self.clean_restrictions(cleaned_data)
        cleaned_data = self.clean_fields(cleaned_data)
        cleaned_data = self.clean_registrations(cleaned_data)

        if published:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['event', 'date', 'period', 'start_time', 'end_time', 'speakers']

            if place in [Slot.FACE_TO_FACE, Slot.OUTSIDE]:
                m_fields.append("room")
            elif place == Slot.REMOTE:
                m_fields.append("url")


            # Field level error
            for field in m_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _("This field is required"))

            # Generic field error
            if not all(cleaned_data.get(e) for e in m_fields):
                raise forms.ValidationError(_('Required fields are not filled in'))

            # Period check
            try:
                period = Period.from_date(pk=period.pk, date=_date)
            except Period.DoesNotExist:
                raise forms.ValidationError(
                    _("Invalid date for selected period : please check periods settings")
                )

            if _date < timezone.localdate():
                self.add_error('date', _("You can't set a date in the past"))

            if _date == timezone.localdate() and start_time <= timezone.now().time():
                self.add_error(
                    'start_time',
                    _("Slot is set for today : please enter a valid start_time")
                )

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            self.add_error('start_time', _("Error: Start time must be set before end time"))

        if event and not event.published and published:
            event.published = True
            messages.success(self.request, _("Event published"))

        if event and published:
            bounds = Slot.objects.filter(event=event).aggregate(
                date_min=Min('date'),
                date_max=Max('date'),
            )

            event.first_slot_date = bounds['date_min']
            event.last_slot_date = bounds['date_max']

            if event.start_date:
                if _date < event.start_date.date():
                    messages.warning(
                        self.request,
                        _("The slot will be saved, but the event publication start date do not match the slot date. The event \
                         publication start date will be changed automatically. Remember to adjust it yourself so that \
                         registrations can proceed without problems.")
                    )
                if bounds['date_min'] and event.start_date.date() > bounds['date_min']:
                    event.start_date = bounds['date_min'] - timedelta(days=7)

            if event.end_date:
                if _date > event.end_date.date():
                    messages.warning(
                        self.request,
                        _("The slot will be saved, but the event publication end date do not match the slot date. The event \
                         publication end date will be changed automatically. Remember to adjust it yourself so that \
                         registrations can proceed without problems.")
                    )
                if bounds['date_max'] and event.end_date.date() < bounds['date_max']:
                    event.end_date = bounds['date_max']

            event.save()

        return cleaned_data


    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Keep this ?
        self.request.session['current_establishment_id'] = \
            instance.event.establishment.id if instance.event.establishment else None
        self.request.session['current_highschool_id'] = \
            instance.event.highschool.id if instance.event.highschool else None
        self.request.session['current_structure_id'] = \
            instance.event.structure.id if instance.event.structure else None

        if instance.event and not instance.event.published and instance.published:
            instance.event.published = True
            instance.event.save()
            messages.success(self.request, _("Event published"))

        return instance


class MyHighSchoolForm(HighSchoolForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for elem in [
            'address',
            'address2',
            'address3',
            'department',
            'city',
            'zip_code',
            'fax',
            'email',
            'phone_number',
            'head_teacher_name',
        ]:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        return super(forms.ModelForm, self).clean()

    class Meta:
        model = HighSchool
        fields = [
            'country',
            'address',
            'address2',
            'address3',
            'department',
            'city',
            'zip_code',
            'fax',
            'email',
            'phone_number',
            'head_teacher_name',
        ]


class HighSchoolStudentImmersionUserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs['class'] = 'form-control'
        self.fields['last_name'].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        if not first_name or first_name.strip() == '':
            raise forms.ValidationError({'first_name': _('This field must be filled')})
        if not last_name or last_name.strip() == '':
            raise forms.ValidationError({'last_name': _('This field must be filled')})

        return cleaned_data

    class Meta:
        model = ImmersionUser
        fields = ['first_name', 'last_name']


class ContactForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['subject'] = forms.CharField(label=_("Subject"), max_length=100, required=True)
        self.fields['body'] = forms.CharField(widget=CKEditorWidget())
        self.fields['subject'].widget.attrs['class'] = 'form-control'


class StructureForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['mailing_list'].widget.attrs['class'] = 'form-control'

    class Meta:
        model = Structure
        fields = [
            'mailing_list',
        ]


class TrainingFormHighSchool(TrainingForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields["structures"]

        for field_name in ["training_subdomains", "label", "highschool", "url"]:
            self.fields[field_name].widget.attrs.setdefault("class", "")
            self.fields[field_name].widget.attrs["class"] += " form-control"

        self.fields["highschool"].widget.attrs["required"] = ""

    def clean(self):
        cleaned_data = super(forms.ModelForm, self).clean()

        highschool = cleaned_data.get("highschool", None)

        if highschool is None:
            self.add_error("highschool", _("This field is required."))
            return cleaned_data

        return super().clean()


class OffOfferEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        for field_name in ["establishment", "structure", "highschool", "label", "description", "event_type"]:
            self.fields[field_name].widget.attrs.setdefault("class", "")
            self.fields[field_name].widget.attrs["class"] += " form-control"

        self.fields["highschool"].queryset = HighSchool.agreed.none()
        self.fields["establishment"].queryset = Establishment.activated.filter(is_host_establishment=True)
        self.fields["structure"].queryset = Structure.activated.all()
        self.fields["event_type"].queryset = OffOfferEventType.activated.all()

        if not self.request.user.is_superuser:
            # Keep this ?
            #if self.request.user.establishment:
            #    self.fields["establishment"].initial = self.request.user.establishment.id

            if self.request.user.is_master_establishment_manager() or self.request.user.is_operator():
                self.fields["highschool"].queryset = \
                    HighSchool.agreed.filter(postbac_immersion=True).order_by('city', 'label')

            if self.request.user.is_establishment_manager():
                self.fields["establishment"].empty_label = None
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(establishment=self.request.user.establishment)

            if self.request.user.is_structure_manager():
                self.fields["establishment"].empty_label = None
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].required = True
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(id__in=self.request.user.structures.all())

            if self.request.user.is_high_school_manager():
                self.fields["establishment"].queryset = Establishment.objects.none()
                self.fields["structure"].queryset = Structure.objects.none()
                self.fields["highschool"].queryset = \
                    HighSchool.agreed.filter(postbac_immersion=True, id=self.request.user.highschool.id)
                self.fields["highschool"].empty_label = None


        if self.instance and self.instance.establishment_id:
            self.fields["establishment"].queryset = Establishment.objects.filter(pk=self.instance.establishment.id)
            self.fields["establishment"].empty_label = None

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')

        if start and end and end < start:
            raise forms.ValidationError(_("The end date must be after the start date."))

        # Uniqueness
        filters = {
            'establishment': cleaned_data.get("establishment", None),
            'structure': cleaned_data.get("structure", None),
            'highschool': cleaned_data.get("highschool", None),
            'label': cleaned_data.get("label", None),
            'event_type': cleaned_data.get("event_type", None)
        }
        exclude_filters = {}

        if self.instance.id:
            exclude_filters = {'id': self.instance.id}

        if OffOfferEvent.objects.filter(**filters).exclude(**exclude_filters).exists():
            msg = _("An event with these values already exists")
            messages.error(self.request, msg)
            raise forms.ValidationError(msg)

        try:
            speakers = json.loads(self.data.get("speakers_list", "[]"))
        except Exception:
            speakers = []

        if not speakers:
            messages.error(self.request, _("Please add at least one speaker."))
            raise forms.ValidationError(_("Please add at least one speaker."))

        return cleaned_data

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        self.request.session['current_establishment_id'] = instance.establishment.id if instance.establishment else None
        self.request.session['current_highschool_id'] = instance.highschool.id if instance.highschool else None
        self.request.session['current_structure_id'] = instance.structure.id if instance.structure else None

        speakers_list = json.loads(self.data.get('speakers_list', []))

        current_speakers = [u for u in instance.speakers.all().values_list('username', flat=True)]
        new_speakers = [speaker.get('username') for speaker in speakers_list]

        # speakers to add
        for speaker in speakers_list:
            if isinstance(speaker, dict):
                send_creation_msg = False

                try:
                    speaker_user = ImmersionUser.objects.get(
                        Q(username=speaker['email']) | Q(email=speaker['email']))
                except ImmersionUser.DoesNotExist:
                    speaker_user = ImmersionUser.objects.create(
                        username=speaker['email'],
                        last_name=speaker['lastname'],
                        first_name=speaker['firstname'],
                            email=speaker['email'],
                        establishment=instance.establishment
                    )
                    messages.success(self.request, gettext("User '{}' created").format(speaker['email']))
                    if not speaker_user.establishment or not speaker_user.establishment.data_source_plugin:
                        speaker_user.set_recovery_string()

                    send_creation_msg = True

                try:
                    Group.objects.get(name='INTER').user_set.add(speaker_user)
                except Exception:
                    messages.error(
                        self.request, _("Couldn't add group 'INTER' to user '%s'" % speaker['email']),
                    )

                if send_creation_msg:
                    return_msg = speaker_user.send_message(self.request, 'CPT_CREATE')

                    if not return_msg:
                        messages.success(
                            self.request,
                            gettext("A confirmation email has been sent to {}").format(speaker['email']),
                        )
                        speaker_user.creation_email_sent = True
                        speaker_user.save()
                    else:
                        messages.warning(self.request, gettext("Couldn't send email : %s" % return_msg))

                if speaker_user:
                    instance.speakers.add(speaker_user)

        # speakers to remove
        remove_list = set(current_speakers) - set(new_speakers)
        for username in remove_list:
            try:
                user = ImmersionUser.objects.get(username=username)
                instance.speakers.remove(user)
            except ImmersionUser.DoesNotExist:
                pass

        return instance

    class Meta:
        model = OffOfferEvent
        fields = ('label', 'description', 'event_type', 'published', 'structure', 'establishment', 'highschool', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format="%Y-%m-%dT%H:%M"),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format="%Y-%m-%dT%H:%M"),
        }


class UserPreferencesForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, setting in ImmersionUser.USER_PREFERENCES.items():
            if setting['type'] == 'boolean':
                self.fields[name] = forms.BooleanField(label=setting['description'], required=False)
