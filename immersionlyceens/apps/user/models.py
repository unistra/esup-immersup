from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils.translation import gettext, gettext_lazy as _, pgettext

from immersionlyceens.apps.core.models import ImmersionUser, ImmersionUserGroup


class HighSchoolStudent(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('High school student')
        verbose_name_plural = _('High school students')
        proxy = True


class Student(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        proxy = True


class Visitor(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Visitor')
        verbose_name_plural = _('Visitors')
        proxy = True


class Speaker(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Speaker')
        verbose_name_plural = _('Speakers')
        proxy = True


class Operator(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Operator')
        verbose_name_plural = _('Operators')
        proxy = True


class EstablishmentManager(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Establishment manager')
        verbose_name_plural = _('Establishment managers')
        proxy = True


class MasterEstablishmentManager(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Master establishment manager')
        verbose_name_plural = _('Master establishment managers')
        proxy = True


class HighSchoolManager(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('High school manager')
        verbose_name_plural = _('High school managers')
        proxy = True


class StructureManager(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Structure manager')
        verbose_name_plural = _('Structure managers')
        proxy = True


class LegalDepartmentStaff(ImmersionUser):
    class Meta:
        app_label = 'user'
        verbose_name = _('Legal department staff')
        verbose_name_plural = _('Legal department staffs')
        proxy = True


class UserGroup(ImmersionUserGroup):
    class Meta:
        app_label = 'user'
        verbose_name = _('User group')
        verbose_name_plural = _('User groups')
        ordering = ['pk', ]
        proxy = True
