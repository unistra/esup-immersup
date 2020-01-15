import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import pgettext
from django.utils.translation import ugettext_lazy as _
from immersionlyceens.fields import UpperCharField

from .utils import get_cities, get_departments

logger = logging.getLogger(__name__)


class ImmersionUser(AbstractUser):
    _user_filters = [
        lambda has_group, su: has_group or su,
        lambda has_group, su: has_group and not su
    ]
    _groups = {
        'SCUIO-IP': 'scuio_ip_manager',
        'REF-CMP': 'component_manager',
        'REF-LYC': 'high_school_manager',
        'ETU': 'student',
        'ENS-CH': 'teacher',
        'SRV-JUR': 'legal_department_staff',
    }

    class Meta:
        verbose_name = _('User')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, name in self._groups.items():
            setattr(self, 'is_%s' % name,
                    partial(self.has_groups, code, negated=False))

    def has_groups(self, *groups, negated=False):
        return self._user_filters[negated](
            self.is_superuser, self.groups.filter(name__in=groups).exists())

    def authorized_groups(self):
        user_filter = {} if self.is_superuser else {'user__id': self.pk}
        return Group.objects.filter(**user_filter)


class CourseDomain(models.Model):
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Course domain')
        verbose_name_plural = _('Course domains')

    def __str__(self):
        return self.label


class Campus(models.Model):
    label = models.CharField(_("Label"), max_length=255, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Campus')
        verbose_name_plural = _('Campus')

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super(Campus, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A campus with this label exists'))


class BachelorMention(models.Model):
    """
    bachelor degree mentions
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""
        verbose_name = _('Bachelor mention')
        verbose_name_plural = _('Bachelor mentions')

    def __str__(self):
        """str"""
        return self.label


class Building(models.Model):
    label = models.CharField(
        _("Label"), max_length=255, blank=False, null=False)
    campus = models.ForeignKey(
        Campus, verbose_name=("Campus"), default=None, 
        on_delete=models.CASCADE, related_name="buildings")
    url = models.URLField(_("Url"), max_length=200, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Building')
        unique_together = ('campus', 'label')

    def __str__(self):
        # TODO: Should we display campus label as well (????)
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super(Building, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A building with this label for the same campus exists'))


class HighSchool(models.Model):

    class Meta:
        verbose_name = _('High school')
        unique_together = ('label', 'city')

    label = models.CharField(
        _("Label"), max_length=255, blank=False, null=False)
    address = models.CharField(
        _("Address"), max_length=255, blank=False, null=False)
    address2 = models.CharField(
        _("Address2"), max_length=255, blank=True, null=True)
    address3 = models.CharField(
        _("Address3"), max_length=255, blank=True, null=True)
    department = models.CharField(
        _("Department"), max_length=128, blank=False, null=False,
        choices=get_departments())
    city = UpperCharField(
        _("City"), max_length=255, blank=False, null=False,
        choices=get_cities())
    zip_code = models.CharField(
        _("Zip Code"), max_length=128, blank=False, null=False)
    phone_number = models.CharField(
        _("Phone number"), max_length=20, null=False, blank=False)
    fax = models.CharField(
        _("Fax"), max_length=20, null=True, blank=True)
    email = models.EmailField(_('Email'))
    head_teacher_name = models.CharField(
        _("Head teacher name"),
        max_length=255,
        blank=False,
        null=False,
        help_text=_('civility last name first name')
    )
    referent_name = models.CharField(
        _('Referent name'), max_length=255, blank=False, null=False, 
        help_text=_('last name first name'))
    referent_phone_number = models.CharField(
        _("Referent phone number"), max_length=20, blank=False, null=False)
    referent_email = models.EmailField(_('Referent email'))
    convention_start_date = models.DateField(
        _("Convention start date"), null=True, blank=True)
    convention_end_date = models.DateField(
        _("Convention end date"), null=True, blank=True)
