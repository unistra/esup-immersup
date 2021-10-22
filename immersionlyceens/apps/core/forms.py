from datetime import datetime

from django import forms
from django.conf import settings
from django.forms.widgets import DateInput, TimeInput
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget

from ..immersion.forms import StudentRecordForm
from .admin_forms import HighSchoolForm
from .models import (
    Building, Calendar, Campus, Structure, Course, CourseType, Establishment,
    HighSchool, ImmersionUser, Slot, Training, UniversityYear,
)


class CourseForm(forms.ModelForm):
    establishment = forms.ModelChoiceField(queryset=Establishment.objects.none(), required=False)
    highschool = forms.ModelChoiceField(queryset=Establishment.objects.none(), required=False)

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

            self.fields["structure"].queryset = Structure.objects.none()

            allowed_structs = self.request.user.get_authorized_structures()
            self.fields["structure"].queryset = allowed_structs.order_by('code', 'label')

            if allowed_establishments.count() == 1:
                self.fields["establishment"].initial = allowed_establishments.first().id

            if allowed_structs.count() == 1:
                self.fields["structure"].initial = allowed_structs.first().id

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
            allowed_structs = self.request.user.get_authorized_structures()
            training = cleaned_data['training']
            course_structs = training.structures.all()

            if not (course_structs & allowed_structs).exists():
                raise forms.ValidationError(_("You don't have enough privileges to update this course"))

        return cleaned_data

    class Meta:
        model = Course
        fields = ('id', 'label', 'url', 'published', 'training', 'structure', 'establishment')


class SlotForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)

        # self.fields["training"].queryset = self.fields["training"].queryset.filter(active=True)

        for elem in [
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
        pub = cleaned_data.get('published', None)

        cals = Calendar.objects.all()
        cal = None
        if cals.count() > 0:
            cal = cals[0]
        if not cal:
            raise forms.ValidationError(_('Error: A calendar is required to set a slot.'))

        pub = cleaned_data.get('published')
        if pub is not None:
            if pub:
                # Mandatory fields
                if not all(
                    cleaned_data.get(e)
                    for e in ['course', 'course_type', 'campus', 'building', 'room', 'date', 'start_time', 'end_time',]
                ):
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
