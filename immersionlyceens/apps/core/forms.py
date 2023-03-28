import json
from datetime import datetime
from typing import Any, Dict

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.widgets import DateInput, TimeInput
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _, ngettext
from django_countries.fields import CountryField
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget
from rest_framework.exceptions import ValidationError

from ...libs.utils import get_general_setting
from ..immersion.forms import StudentRecordForm
from ..immersion.models import HighSchoolStudentRecord, StudentRecord
from .admin_forms import HighSchoolForm, TrainingForm
from .models import (
    Building, Campus, Course, CourseType, Establishment, HighSchool,
    HighSchoolLevel, ImmersionUser, OffOfferEvent, OffOfferEventType,
    Period, PostBachelorLevel, Slot, Structure, StudentLevel, Training,
    UniversityYear, Visit
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
                allowed_establishments = Establishment.activated.user_establishments(self.request.user)
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
        fields = ('id', 'label', 'url', 'published', 'training', 'structure', 'establishment', 'highschool')


class SlotForm(forms.ModelForm):
    establishment = forms.ModelChoiceField(queryset=Establishment.objects.none(), required=False)
    structure = forms.ModelChoiceField(queryset=Structure.objects.all(), required=False)
    training = forms.ModelChoiceField(queryset=Training.objects.all(), required=False)
    highschool = forms.ModelChoiceField(queryset=HighSchool.agreed.filter(postbac_immersion=True), required=False)
    repeat = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)

        try:
            getattr(self, "slot_dates")
        except AttributeError:
            self.slot_dates = []

        course = self.instance.course if self.instance and self.instance.course_id else None

        for elem in ['establishment', 'highschool', 'structure', 'visit', 'event', 'training', 'course', 'course_type',
            'campus', 'building', 'room', 'start_time', 'end_time', 'n_places', 'additional_information', 'url',
            'allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels', 'allowed_student_levels',
            'allowed_post_bachelor_levels', 'registration_limit_delay', 'cancellation_limit_delay']:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

        # Disable autocomplete for date fields
        self.fields['date'].widget.attrs.update({'autocomplete': 'off'})

        can_choose_establishment = any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator(),
            self.request.user.is_structure_manager()
        ])

        self.fields["allowed_highschools"].queryset = HighSchool.agreed.order_by('city', 'label')
        self.fields["allowed_highschool_levels"].queryset = HighSchoolLevel.objects.filter(active=True).order_by('order')
        self.fields["allowed_student_levels"].queryset = StudentLevel.objects.filter(active=True).order_by('order')
        self.fields["allowed_post_bachelor_levels"].queryset = PostBachelorLevel.objects.filter(active=True).order_by('order')

        if can_choose_establishment:
            allowed_establishments = Establishment.activated.user_establishments(self.request.user)
            self.fields["establishment"].queryset = allowed_establishments.order_by('code', 'label')
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

    def clean_restrictions(self, cleaned_data):
        establishments_restrictions = cleaned_data.get('establishments_restrictions')
        levels_restrictions = cleaned_data.get('levels_restrictions')
        allowed_establishments = cleaned_data.get('allowed_establishments')
        allowed_highschools = cleaned_data.get('allowed_highschools')
        allowed_highschool_levels = cleaned_data.get('allowed_highschool_levels')
        allowed_student_levels = cleaned_data.get('allowed_student_levels')
        allowed_post_bachelor_levels = cleaned_data.get('allowed_post_bachelor_levels')

        if establishments_restrictions and not allowed_establishments and not allowed_highschools:
            cleaned_data["establishments_restrictions"] = False

        if levels_restrictions and not allowed_highschool_levels and not allowed_student_levels \
                and not allowed_post_bachelor_levels:
            cleaned_data["levels_restrictions"] = False

        return cleaned_data


    def clean_fields(self, cleaned_data):
        # Remote slot : remove unnecessary fields
        if not cleaned_data.get('face_to_face', True):
            for field in ['campus', 'building', 'room']:
                cleaned_data[field] = None
        else:
            cleaned_data['url'] = None

        return cleaned_data


    def clean(self):
        cleaned_data = super().clean()
        structure = cleaned_data.get('structure')
        published = cleaned_data.get('published', None)
        n_places = cleaned_data.get('n_places', 0)
        face_to_face = cleaned_data.get('face_to_face', True)
        _date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time', 0)

        cleaned_data = self.clean_restrictions(cleaned_data)
        cleaned_data = self.clean_fields(cleaned_data)

        # Slot repetition
        if cleaned_data.get('repeat'):
            self.slot_dates = self.request.POST.getlist("slot_dates")

        if published:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['course', 'course_type', 'date', 'start_time', 'end_time', 'speakers']

            if face_to_face:
                if structure:
                    m_fields += ['campus', 'building']

                m_fields.append('room')

            # Field level error
            for field in m_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _("This field is required"))

            # Generic field error
            if not all(cleaned_data.get(e) for e in m_fields):
                raise forms.ValidationError(_('Required fields are not filled in'))

            if _date == timezone.localdate() and start_time <= timezone.now().time():
                raise forms.ValidationError(
                    {'start_time': _("Slot is set for today : please enter a valid start_time")}
                )

            if not n_places or n_places <= 0:
                msg = _("Please enter a valid number for 'n_places' field")
                raise forms.ValidationError({'n_places': msg})

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({'start_time': _('Error: Start time must be set before end time')})

        return cleaned_data

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        if instance.course and not instance.course.published and instance.published:
            instance.course.published = True
            instance.course.save()
            messages.success(self.request, _("Course published"))

        if self.data.get("repeat"):
            new_dates = self.data.getlist("slot_dates[]")

            try:
                university_year = UniversityYear.objects.get(active=True)
                new_slot_template = Slot.objects.get(pk=instance.pk)
                slot_speakers = [speaker for speaker in new_slot_template.speakers.all()]
                slot_allowed_establishments = [e for e in new_slot_template.allowed_establishments.all()]
                slot_allowed_highschools = [h for h in new_slot_template.allowed_highschools.all()]
                slot_allowed_highschool_levels = [l for l in new_slot_template.allowed_highschool_levels.all()]
                slot_allowed_student_levels = [l for l in new_slot_template.allowed_student_levels.all()]
                slot_allowed_post_bachelor_levels = [l for l in new_slot_template.allowed_post_bachelor_levels.all()]

                for new_date in new_dates:
                    parsed_date = datetime.strptime(new_date, "%d/%m/%Y").date()
                    period = Period.from_date(parsed_date)

                    if parsed_date <= university_year.end_date and period:
                        new_slot_template.pk = None
                        new_slot_template.date = parsed_date
                        new_slot_template.save()
                        new_slot_template.speakers.add(*slot_speakers)
                        new_slot_template.allowed_establishments.add(*slot_allowed_establishments)
                        new_slot_template.allowed_highschools.add(*slot_allowed_highschools)
                        new_slot_template.allowed_highschool_levels.add(*slot_allowed_highschool_levels)
                        new_slot_template.allowed_student_levels.add(*slot_allowed_student_levels)
                        new_slot_template.allowed_post_bachelor_levels.add(*slot_allowed_post_bachelor_levels)
                        messages.success(self.request, _("Course slot \"%s\" created.") % new_slot_template)
            except Period.MultipleObjectsReturned:
                raise
            except (Slot.DoesNotExist, UniversityYear.DoesNotExist):
                pass

        return instance


    class Meta:
        model = Slot
        fields = ('id', 'establishment', 'structure', 'highschool', 'visit', 'event', 'training', 'course',
            'course_type', 'campus', 'building', 'room', 'url', 'date', 'start_time', 'end_time', 'n_places',
            'additional_information', 'published', 'face_to_face', 'establishments_restrictions', 'levels_restrictions',
            'allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels', 'allowed_student_levels',
            'allowed_post_bachelor_levels', 'speakers', 'repeat', 'registration_limit_delay',
            'cancellation_limit_delay')
        widgets = {
            'additional_information': forms.Textarea(attrs={'placeholder': _('Enter additional information'),}),
            'n_places': forms.NumberInput(attrs={'min': 1, 'max': 200, 'value': 0}),
            'room': forms.TextInput(attrs={'placeholder': _('Enter the room name')}),
            'date': forms.DateInput(
                format='%d/%m/%Y', attrs={'placeholder': _('dd/mm/yyyy'), 'class': 'datepicker form-control'}
            ),
            'start_time': TimeInput(format='%H:%M'),
            'end_time': TimeInput(format='%H:%M'),
        }

        localized_fields = ('date', 'repeat')


class VisitSlotForm(SlotForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["highschool"].queryset = HighSchool.agreed\
            .filter(visits__isnull=False)\
            .distinct()\
            .order_by('city', 'label')

        self.fields["room"].widget.attrs["placeholder"] = _("Please enter the building and room name")

        allowed_establishments = Establishment.activated.user_establishments(self.request.user)
        self.fields["establishment"].queryset = allowed_establishments.order_by('code', 'label')

        allowed_structs = self.request.user.get_authorized_structures()
        self.fields["structure"].queryset = allowed_structs.order_by('code', 'label')

        if self.request.user.is_structure_manager():
            self.fields["structure"].initial = self.fields["structure"].queryset.first()
            self.fields["structure"].empty_label = None
        else:
            self.fields["structure"].initial = None
            self.fields["structure"].empty_label = "---------"

        visit = self.instance.visit if self.instance and self.instance.visit_id else None

        if visit:
            self.fields["structure"].initial = visit.structure.id if visit.structure else None
            self.fields["highschool"].initial = visit.highschool.id
            self.fields["establishment"].initial = visit.establishment.id


    def clean(self):
        cleaned_data = super(forms.ModelForm, self).clean()
        visit = cleaned_data.get('visit')
        published = cleaned_data.get('published', None)
        face_to_face = cleaned_data.get('face_to_face', None)
        start_time = cleaned_data.get('start_time', None)
        n_places = cleaned_data.get('n_places', None)
        _date = cleaned_data.get('date')

        cleaned_data = self.clean_restrictions(cleaned_data)
        cleaned_data = self.clean_fields(cleaned_data)

        if published is True:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['visit', 'date', 'start_time', 'end_time', 'speakers']

            if face_to_face:
                m_fields.append("room")
            else:
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
                period = Period.from_date(date=_date)
            except Period.MultipleObjectsReturned:
                raise forms.ValidationError(
                    _("Multiple periods found for date '%s' : please check your periods settings") % _date
                )

            if not period:
                raise forms.ValidationError(
                    {'date': _("No available period found for slot date '%s', please create one first") % _date}
                )

            if not (period.immersion_start_date <= _date <= period.immersion_end_date):
                raise forms.ValidationError(
                    {'date': _("Slot date must be between period immersion start and end dates")}
                )

            if _date < timezone.localdate():
                raise forms.ValidationError(
                    {'date': _("You can't set a date in the past")}
                )

            if _date == timezone.localdate() and start_time <= timezone.now().time():
                raise forms.ValidationError(
                    {'start_time': _("Slot is set for today : please enter a valid start_time")}
                )

            if not n_places or n_places <= 0:
                raise forms.ValidationError(
                    {'n_places': _("Please enter a valid number for 'n_places' field")}
                )

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({'start_time': _('Error: Start time must be set before end time')})

        if visit and not visit.published and published:
            visit.published = True
            visit.save()
            messages.success(self.request, _("Visit published"))

        return cleaned_data


    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Keep this ?
        self.request.session['current_establishment_id'] = instance.visit.establishment.id
        self.request.session['current_structure_id'] = instance.visit.structure.id if instance.visit.structure else None

        if instance.visit and not instance.visit.published and instance.published:
            instance.visit.published = True
            instance.visit.save()
            messages.success(self.request, _("Visit published"))

        return instance


class OffOfferEventSlotForm(SlotForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["highschool"].queryset = HighSchool.agreed\
            .filter(events__isnull=False)\
            .distinct()\
            .order_by('city', 'label')

        allowed_establishments = Establishment.activated.user_establishments(self.request.user)
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


    def clean(self):
        cleaned_data = super(forms.ModelForm, self).clean()
        event = cleaned_data.get('event')
        published = cleaned_data.get('published', None)
        face_to_face = cleaned_data.get('face_to_face', None)
        start_time = cleaned_data.get('start_time', None)
        n_places = cleaned_data.get('n_places', None)
        _date = cleaned_data.get('date')

        cleaned_data = self.clean_restrictions(cleaned_data)
        cleaned_data = self.clean_fields(cleaned_data)

        if published is True:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['event', 'date', 'start_time', 'end_time', 'speakers']

            if face_to_face:
                m_fields.append("room")
            else:
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
                period = Period.from_date(date=_date)
            except Period.MultipleObjectsReturned:
                raise forms.ValidationError(
                    _("Multiple periods found for date '%s' : please check your periods settings") % _date
                )

            if not period:
                raise forms.ValidationError(
                    {'date': _("No available period found for slot date '%s', please create one first") % _date}
                )

            if not (period.immersion_start_date <= _date <= period.immersion_end_date):
                raise forms.ValidationError(
                    {'date': _("Slot date must be between period immersion start and end dates")}
                )

            if _date < timezone.localdate():
                self.add_error('date', _("You can't set a date in the past"))

            if _date == timezone.localdate() and start_time <= timezone.now().time():
                self.add_error('start_time', _("Slot is set for today : please enter a valid start_time"))

            if not n_places or n_places <= 0:
                msg = _("Please enter a valid number for 'n_places' field")
                self.add_error('n_places', msg)

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({'start_time': _('Error: Start time must be set before end time')})

        if event and not event.published and published:
            event.published = True
            event.save()
            messages.success(self.request, _("Event published"))

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
            'label',
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
            'postbac_immersion',
            'mailing_list'

        ]:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = HighSchool
        fields = [
            'label',
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
            'postbac_immersion',
            'mailing_list'
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

        self.fields['body'] = forms.CharField(
            widget=SummernoteInplaceWidget(
                attrs={'summernote': {'width': '100%', 'height': '200px', 'rows': 6, 'airMode': False,}}
            )
        )

        #
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



class VisitForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        for field_name in ["establishment", "structure", "highschool", "purpose"]:
            self.fields[field_name].widget.attrs.setdefault("class", "")
            self.fields[field_name].widget.attrs["class"] += " form-control"

        self.fields["highschool"].queryset = HighSchool.agreed.order_by("city", "label")
        self.fields["establishment"].queryset = Establishment.activated.all()
        self.fields["establishment"].empty_label = None
        self.fields["structure"].queryset = Structure.activated.all()

        if not self.request.user.is_superuser:
            if self.request.user.establishment:
                self.fields["establishment"].initial = self.request.user.establishment.id

            if self.request.user.is_establishment_manager():
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(establishment=self.request.user.establishment)

            if self.request.user.is_structure_manager():
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].required = True
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(id__in=self.request.user.structures.all())

        if self.instance and self.instance.establishment_id:
            self.fields["establishment"].queryset = Establishment.objects.filter(pk=self.instance.establishment.id)


    def clean(self):
        cleaned_data = super().clean()

        # Uniqueness
        filters = {
            'establishment' : cleaned_data.get("establishment", None),
            'structure' : cleaned_data.get("structure", None),
            'highschool' : cleaned_data.get("highschool", None),
            'purpose' : cleaned_data.get("purpose", None)
        }
        exclude_filters = {}

        if self.instance.id:
            exclude_filters = {'id': self.instance.id}

        if Visit.objects.filter(**filters).exclude(**exclude_filters).exists():
            msg = _("A visit with these values already exists")
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

        self.request.session['current_establishment_id'] = instance.establishment.id
        self.request.session['current_structure_id'] = instance.structure.id if instance.structure else None

        speakers_list = json.loads(self.data.get('speakers_list', []))

        current_speakers = [u for u in instance.speakers.all().values_list('username', flat=True)]
        new_speakers = [speaker.get('username') for speaker in speakers_list]

        # speakers to add
        for speaker in speakers_list:
            if isinstance(speaker, dict):
                send_creation_msg = False

                try:
                    speaker_user = ImmersionUser.objects.get(Q(username=speaker['email'])|Q(email=speaker['email']))
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
                        speaker_user.creation_email_sent=True
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
        model = Visit
        fields = ('purpose', 'published', 'structure', 'establishment', 'highschool')


class OffOfferEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        for field_name in ["establishment", "structure", "highschool", "label", "description", "event_type"]:
            self.fields[field_name].widget.attrs.setdefault("class", "")
            self.fields[field_name].widget.attrs["class"] += " form-control"

        self.fields["highschool"].queryset = HighSchool.agreed.none()
        self.fields["establishment"].queryset = Establishment.activated.all()
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
        fields = ('label', 'description', 'event_type', 'published', 'structure', 'establishment', 'highschool')
