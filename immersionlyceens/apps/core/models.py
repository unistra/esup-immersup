import logging
from functools import partial

from django.db import models

from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractUser

from django.conf import settings

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

