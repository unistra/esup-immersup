from datetime import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django.forms.widgets import DateInput

from .models import (Course, Component, Training, ImmersionUser, UniversityYear, Slot)

class CourseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["training"].queryset = self.fields["training"].queryset.filter(active=True)

        if self.request:
            allowed_comps = Component.activated.user_cmps(self.request.user, 'SCUIO-IP')
            self.fields["component"].queryset = allowed_comps.order_by('code', 'label')

            if self.instance.id and not self.request.user.has_course_rights(self.instance.id):
                for field in self.fields:
                    self.fields[field].disabled = True
        else:
            self.fields["component"].queryset = self.fields["component"].queryset.order_by('code', 'label')

    def clean(self):
        cleaned_data = super().clean()

        try:
            active_year = UniversityYear.objects.get(active=True)
        except UniversityYear.MultipleObjectsReturned:
            raise forms.ValidationError(
                _("Error : multiple active university years"))
        except UniversityYear.DoesNotExist:
            raise forms.ValidationError(
                _("Error : can't find any active university year"))

        if active_year.start_date and active_year.end_date:
            if not (active_year.start_date <= datetime.today().date() <= active_year.end_date):
                raise forms.ValidationError(
                    _("Error : a course can only be created between start and end of the active university year"))
        else:
            raise forms.ValidationError(
                _("Error : dates of active university year improperly configured"))

        # Check user rights
        if self.request:
            allowed_comps = Component.activated.user_cmps(self.request.user, 'SCUIO-IP')
            training = cleaned_data['training']
            course_comps = training.components.all()

            if not (course_comps & allowed_comps).exists():
                raise forms.ValidationError(
                    _("You don't have enough privileges to update this course"))

        return cleaned_data

    class Meta:
        model = Course
        fields = ('id', 'label', 'url', 'published', 'training')


class SlotForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)

        # self.fields["training"].queryset = self.fields["training"].queryset.filter(active=True)

        for elem in ['course', 'course_type', 'campus', 'building',
                  'room', 'date', 'start_time', 'end_time', 'n_places',
                  'additional_information', 'published',]:
            self.fields[elem].widget.attrs.update({'class': 'form-control'})

        if instance:
            self.fields['date'].value = instance.date

    class Meta:
        model = Slot
        fields = ('id', 'course', 'course_type', 'campus', 'building',
                  'room', 'date', 'start_time', 'end_time', 'n_places',
                  'additional_information', 'published',)
        widgets = {
            'additional_information': forms.Textarea(attrs={
                'placeholder': _('Input additional information'),
            }),
            'n_places': forms.NumberInput(attrs={'min': 0, 'max': 200, 'value': 0}),
            'room': forms.TextInput(attrs={'placeholder': _('Input the room name')}),
            'date': forms.DateInput(format='%m/%d/%Y', attrs={'placeholder': _('dd/mm/yyyy')}),
        }

        fields = ('id', 'course', 'course_type', 'campus', 'building',
                  'room', 'date', 'start_time', 'end_time', 'n_places',
                  'additional_information', 'published',)