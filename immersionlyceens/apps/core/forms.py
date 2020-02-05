from datetime import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django.forms.widgets import DateInput

from .models import (Course, Component, Training, ImmersionUser, UniversityYear)

class CourseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["training"].queryset = self.fields["training"].queryset.filter(active=True)

        if self.instance.id and self.request:
            # Check user rights
            allowed_comps = Component.activated.user_cmps(self.request.user)
            training = self.instance.training
            course_comps = training.components.all()

            if not (course_comps & allowed_comps).exists():
                for field in self.fields:
                    self.fields[field].disabled = True

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
            allowed_comps = Component.activated.user_cmps(self.request.user)
            training = cleaned_data['training']
            course_comps = training.components.all()

            if not (course_comps & allowed_comps).exists():
                raise forms.ValidationError(
                    _("You don't have enough privileges to update this course"))

        return cleaned_data

    class Meta:
        model = Course
        fields = ('id', 'label', 'url', 'published', 'training')