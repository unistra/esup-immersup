import json

from datetime import datetime
from typing import Dict, Any

from django import forms
from django.contrib import messages
from django.contrib.auth.models import Group
from django.conf import settings
from django.forms.widgets import DateInput, TimeInput
from django.utils.translation import gettext, ngettext, gettext_lazy as _
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget
from rest_framework.exceptions import ValidationError

from ..immersion.forms import StudentRecordForm
from .admin_forms import HighSchoolForm, TrainingForm
from .models import (
    Building, Calendar, Campus, Structure, Course, CourseType, Establishment,
    HighSchool, ImmersionUser, Slot, Training, UniversityYear, Visit
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
            elif self.request.user.is_master_establishment_manager():
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)

        course = self.instance.course if self.instance and self.instance.course_id else None

        for elem in [
            'establishment',
            'highschool',
            'structure',
            'training',
            'course',
            'course_type',
            'campus',
            'building',
            'room',
            'start_time',
            'end_time',
            'n_places',
            'additional_information',
            #'published',
        ]:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

        can_choose_establishment = any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_structure_manager()
        ])

        if can_choose_establishment:
            allowed_establishments = Establishment.activated.user_establishments(self.request.user)
            self.fields["establishment"].queryset = allowed_establishments.order_by('code', 'label')
        else:
            allowed_establishments = Establishment.objects.none()

        if allowed_establishments.count() == 1:
            self.fields["establishment"].initial = allowed_establishments.first().id
            self.fields["establishment"].empty_label = None

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
        elif self.request.user.is_master_establishment_manager():
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

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        structure = cleaned_data.get('structure')
        highschool = cleaned_data.get('highschool')
        pub = cleaned_data.get('published', None)

        cals = Calendar.objects.all()

        if cals.exists():
            cal = cals.first()
        else:
            raise forms.ValidationError(_('Error: A calendar is required to set a slot.'))

        if pub is True:
            # Mandatory fields, depending on high school / structure slot
            m_fields = ['course', 'course_type', 'room', 'date', 'start_time', 'end_time']

            if structure:
                m_fields += ['campus', 'building']

            if not all(cleaned_data.get(e) for e in m_fields):
                raise forms.ValidationError(_('Required fields are not filled in'))

        _date = cleaned_data.get('date')
        if _date and not cal.date_is_between(_date):
            raise forms.ValidationError(
                {'date': _('Error: The date must be between the dates of the current calendar')}
            )

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({'start_time': _('Error: Start time must be set before end time')})

        if course and not course.published and pub:
            course.published = True
            course.save()

        return cleaned_data

    class Meta:
        model = Slot
        fields = (
            'id',
            'establishment',
            'structure',
            'highschool',
            'training',
            'course',
            'course_type',
            'campus',
            'building',
            'room',
            'date',
            'start_time',
            'end_time',
            'n_places',
            'additional_information',
            'published',
        )
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

        localized_fields = ('date',)


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
            self.fields["establishment"].initial = self.request.user.establishment.id

            if self.request.user.is_establishment_manager():
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(establishment=self.request.user.establishment)

            if self.request.user.is_structure_manager():
                self.fields["establishment"].queryset = \
                    Establishment.objects.filter(pk=self.request.user.establishment.id)
                self.fields["structure"].queryset = \
                    self.fields["structure"].queryset.filter(establishment=self.request.user.establishment)


    def clean(self):
        cleaned_data = super().clean()
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
                try:
                    speaker_user = ImmersionUser.objects.get(username=speaker['username'])
                except ImmersionUser.DoesNotExist:
                    speaker_user = ImmersionUser.objects.create(
                        username=speaker['username'],
                        last_name=speaker['lastname'],
                        first_name=speaker['firstname'],
                        email=speaker['email'],
                        establishment=instance.establishment
                    )
                    messages.success(self.request, gettext("User '{}' created").format(speaker['username']))
                    return_msg = speaker_user.send_message(self.request, 'CPT_CREATE_INTER')

                    if not return_msg:
                        messages.success(
                            self.request,
                            gettext("A confirmation email has been sent to {}").format(speaker['email']),
                        )
                    else:
                        messages.warning(self.request, return_msg)

                try:
                    Group.objects.get(name='INTER').user_set.add(speaker_user)
                except Exception:
                    messages.error(
                        self.request, _("Couldn't add group 'INTER' to user '%s'" % speaker['username']),
                    )

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