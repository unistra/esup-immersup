from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import (
    BachelorMention, Building, Campus, CancelType, Component,
    Training, TrainingDomain, TrainingSubdomain,
    CourseType)

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
                _("You don't have the required privileges")
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
                _("You don't have the required privileges")
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = Campus
        fields = '__all__'


class CancelTypeForm(forms.ModelForm):
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = CancelType
        fields = '__all__'


class CourseTypeForm(forms.ModelForm):
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = CourseType
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
                _("You don't have the required privileges")
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
                _("You don't have the required privileges")
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = Building
        fields = '__all__'


class TrainingForm(forms.ModelForm):
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = Training
        fields = '__all__'


class ComponentForm(forms.ModelForm):
    """
    Component form class
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Disable code field if it already exists
        if self.initial:
            self.fields["code"].disabled = True

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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = Component
        fields = '__all__'


class PublicTypeForm(forms.ModelForm):
    """
    public type form class
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Disable code field if it already exists
        if self.initial:
            self.fields["code"].disabled = True

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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = Component
        fields = '__all__'
