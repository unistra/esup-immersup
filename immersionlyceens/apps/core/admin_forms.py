from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Building, Campus, CourseDomain, HighSchool
from .utils import get_cities, get_zipcodes


class CourseDomainForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request =  kwargs.pop('request', None)
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
            raise forms.ValidationError(
                _("Valid user required")
            )


        return cleaned_data

    class Meta:
        model = CourseDomain
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
            raise forms.ValidationError(
                _("Valid user required")
            )

        return cleaned_data

    class Meta:
        model = Campus
        fields = '__all__'


class BuildingForm(forms.ModelForm):
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
            raise forms.ValidationError(
                _("Valid user required")
            )

        return cleaned_data

    class Meta:
        model = Building
        fields = '__all__'


class HighSchoolForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        
        if instance.department:
            dep_choices = get_cities(instance.department)
        else:
            dep_choices = ''

        if instance.city:
            zip_choices = get_zipcodes(instance.department, instance.city)
        else:
            zip_choices = ''
 
        self.fields['city'] = forms.TypedChoiceField(
            label=_("City"),
            widget=forms.Select(),
            choices=dep_choices,
            required=True
        )
        self.fields['zip_code'] = forms.TypedChoiceField(
            label=_("Zip code"),
            widget=forms.Select(),
            choices= zip_choices,
            required=True
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
            raise forms.ValidationError(
                _("Valid user required")
            )

        return cleaned_data


    class Meta:
        model = HighSchool
        fields = '__all__'
