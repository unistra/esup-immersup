from datetime import datetime

from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import (
    BachelorMention, Building, Campus, CancelType, Component,
    CourseType, GeneralBachelorTeaching, Training, TrainingDomain,
    TrainingSubdomain, CourseType, PublicType,
    UniversityYear, Holiday, Vacation, Calendar)

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


class HolidayForm(forms.ModelForm):
    """
    University Year form class
    """
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
        model = Holiday
        fields = '__all__'


class VacationForm(forms.ModelForm):
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

        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(
                _("Start date greater than end date")
            )

        return cleaned_data

    class Meta:
        model = Vacation
        fields = '__all__'


class CalendarForm(forms.ModelForm):
    """
    University Year form class
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        calendar_mode = cleaned_data.get('calendar_mode')

        year_start_date = cleaned_data.get('year_start_date')
        year_end_date = cleaned_data.get('year_end_date')
        year_registration_start_date = cleaned_data.get('year_registration_start_date')

        s1_start_date = cleaned_data.get('semester1_start_date')
        s1_end_date = cleaned_data.get('semester1_end_date')
        s1_registration_start_date = cleaned_data.get('semester1_registration_start_date')
        s2_start_date = cleaned_data.get('semester2_start_date')
        s2_end_date = cleaned_data.get('semester2_end_date')
        s2_registration_start_date = cleaned_data.get('semester2_registration_start_date')
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

        # YEAR MODE
        print(calendar_mode)
        if calendar_mode and calendar_mode.lower() == Calendar.CALENDAR_MODE[0][0].lower():
            if not year_start_date or not year_end_date or not year_registration_start_date:
                raise forms.ValidationError(
                    _("Mandatory fields not filled in")
                )
        # SEMESTER MODE
        elif calendar_mode and calendar_mode.lower() == Calendar.CALENDAR_MODE[1][0].lower():
            if not s1_start_date or not s1_end_date or not s1_registration_start_date \
                    or not s2_start_date or not s2_end_date or not s2_registration_start_date:
                raise forms.ValidationError(
                    _("Mandatory fields not filled in")
                )

        # start < end
        if year_start_date and year_end_date and year_start_date >= year_end_date:
            raise forms.ValidationError(
                _("Start date greater than end date")
            )
        # start1 < end1
        if s1_start_date and s1_end_date and s1_start_date >= s1_end_date:
            raise forms.ValidationError(
                _("Semester 1 start date greater than semester 1 end date")
            )
        # start2 < end2
        if s2_start_date and s2_end_date and s2_start_date >= s2_end_date:
            raise forms.ValidationError(
                _("Semester 2 start date greater than semester 2 end date")
            )
        # end1 < start2
        if s1_end_date and s2_start_date and s1_end_date >= s2_start_date:
            raise forms.ValidationError(
                _("Semester 1 ends after the begining of semester 2")
            )
        # <==>   start1 < end1 < start2 < end2

        return cleaned_data

    class Meta:
        model = Calendar
        fields = '__all__'


# Vacation
# Calendar

