import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import pgettext
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class ImmersionUser(AbstractUser):
    """
    Main user class
    """
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
        """
        :param groups: group names to check
        :param negated: boolean
        :return:
        - if negated is False, return True if User is superuser or to one of
        groups, else False
        - if negated is True, return True if User is NOT superuser and belongs
        to one of groups, else False
        """
        return self._user_filters[negated](
            self.is_superuser, self.groups.filter(name__in=groups).exists())

    def authorized_groups(self):
        user_filter = {} if self.is_superuser else {'user__id': self.pk}
        return Group.objects.filter(**user_filter)


class TrainingDomain(models.Model):
    """
    Training domain class
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Training domain')
        verbose_name_plural = _('Training domains')

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A training domain with this label already exists'))


class TrainingSubdomain(models.Model):
    """
    Training subdomain class
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    training_domain = models.ForeignKey(TrainingDomain,
        verbose_name=_("Training domain"), default=None, blank=False,
        null=False, on_delete=models.CASCADE, related_name='Subdomains')
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Training sub domain')
        verbose_name_plural = _('Training sub domains')

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A training sub domain with this label already exists'))


class Component(models.Model):
    """
    Component class
    """
    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=128)
    url = models.URLField(_("Website address"), max_length=256,
        blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Component')
        verbose_name_plural = _('Components')

    def __str__(self):
        return "%s : %s" % (self.code, self.label)

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A component with this code already exists'))


class Training(models.Model):
    """
    Training class
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    training_subdomains = models.ManyToManyField(TrainingSubdomain,
        verbose_name=_("Training subdomains"), blank=False, related_name='Trainings')
    components = models.ManyToManyField(Component, verbose_name=_("Components"),
        blank=False, related_name='Trainings')
    url = models.URLField(_("Website address"), max_length=256,
        blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Training')
        verbose_name_plural = _('Trainings')

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A training with this label already exists'))


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
            raise ValidationError(
                _('A campus with this label already exists'))


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

    def validate_unique(self, exclude=None):
        try:
            super(BachelorMention, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A bachelor mention with this label already exists'))


        
class Building(models.Model):
    label = models.CharField(
        _("Label"), max_length=255, blank=False, null=False)
    campus = models.ForeignKey(Campus, verbose_name=("Campus"),
        default=None, on_delete=models.CASCADE, related_name="buildings")
    url = models.URLField(_("Url"), max_length=200, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name= _('Building')
        unique_together= ('campus', 'label')

    def __str__(self):
        # TODO: Should we display campus label as well (????)
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super(Building, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A building with this label for the same campus already exists'))


class CancelType(models.Model):
    """
    Cancel type
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""
        verbose_name = _('Cancel type')
        verbose_name_plural = _('Cancel types')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(CancelType, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A cancel type with this label already exists'))


class CourseType(models.Model):
    """Course type"""

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""
        verbose_name = _('Course type')
        verbose_name_plural = _('Course type')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(CourseType, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A course type with this label already exists'))


class GeneralBachelorTeaching(models.Model):
    """
    General bachelor specialty teaching
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""
        verbose_name = _('General bachelor specialty teaching')
        verbose_name_plural = _('General bachelor specialties teaching')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(
                _('A specialty teaching with this label already exists'))
