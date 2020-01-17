from datetime import datetime

from django import forms
from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _

from .models import (BachelorMention, Building, Campus, CancelType, Component,
                     CourseType, GeneralBachelorTeaching, HighSchool,
                     ImmersionUser, PublicType, Training, TrainingDomain,
                     TrainingSubdomain, UniversityYear)
from .utils import get_cities, get_zipcodes


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
        self.fields['campus'].queryset = Campus.objects.order_by('label')

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


class GeneralBachelorTeachingForm(forms.ModelForm):
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
        model = GeneralBachelorTeaching
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
        model = PublicType
        fields = '__all__'


class UniversityYearForm(forms.ModelForm):
    """
    University Year form class
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_start_date = cleaned_data.get('registration_start_date')
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

        if start_date and start_date <= datetime.today().date():
            raise forms.ValidationError(
                _("Start date can't be today or earlier")
            )
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(
                _("Start date greater than end date")
            )
        if registration_start_date and end_date and registration_start_date >= end_date:
            raise forms.ValidationError(
                _("Start of registration date greater than end date")
            )

        return cleaned_data

    class Meta:
        model = UniversityYear
        fields = '__all__'


class ImmersionUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].required = False
        self.fields["password2"].required = False

    class Meta(UserCreationForm.Meta):
        model = ImmersionUser
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
            choices=zip_choices,
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
                _("You don't have the required privileges")
            )

        return cleaned_data

    class Meta:
        model = HighSchool
        fields = '__all__'
