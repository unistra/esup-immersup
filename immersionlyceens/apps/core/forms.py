from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from django.forms.widgets import DateInput
import datetime

from .models import (Course)

class CourseForm(forms.ModelForm):

    class Meta:
        model = Course
        fields = ('id', 'training', 'label', 'url', 'published',
                  'teachers')