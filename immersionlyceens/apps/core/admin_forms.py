from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import (
    BachelorMention, Building, Campus, TrainingDomain,
    TrainingSubdomain
)

class BachelorMentionForm(forms.ModelForm):
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
        model = BachelorMention
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


class TrainingDomainForm(forms.ModelForm):
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
        model = TrainingDomain
        fields = '__all__'


class TrainingSubdomainForm(forms.ModelForm):
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
        model = TrainingSubdomain
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
