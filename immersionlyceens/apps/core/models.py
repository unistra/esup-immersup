# pylint: disable=R0903,C0115,W0201,E1101,C0302
"""
Models classes file

pylint ignore:
- R0903: too few public methods, because it's models classes
- C0115: class docstring, because of Meta classes
- W0201: attr set outside init, because it's models classes
- E1101: method/attr not exists in class A. .objects exists but not listed
- C0302: too many lines. Nope, it's the right amount of lines :P
"""
import datetime
import logging
import os
import re
import uuid
from functools import partial
from os.path import dirname, join
from typing import Any, Optional

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Max, Q, Sum
from django.db.models.functions import Coalesce
from django.template.defaultfilters import date as _date, filesizeformat
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _, pgettext
from immersionlyceens.apps.core.managers import PostBacImmersionManager
from immersionlyceens.fields import UpperCharField
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.validators import JsonSchemaValidator

from .managers import (
    ActiveManager, CustomDeleteManager, EstablishmentQuerySet,
    HighSchoolAgreedManager, StructureQuerySet,
)

logger = logging.getLogger(__name__)



def get_file_path(instance, filename,):
    file_basename, extension = os.path.splitext(filename)
    year = datetime.datetime.now().strftime('%Y')
    return (
        os.path.join(settings.S3_FILEPATH if hasattr(settings, 'S3_FILEPATH') else '',
                     year,
                     f'{file_basename}{extension}')
        .lower()
        .replace(' ', '_')
    )


class Establishment(models.Model):
    """
    Establishment class : highest structure level
    """
    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=256, unique=True)
    short_label = models.CharField(_("Short label"), max_length=64, unique=True)
    address = models.CharField(_("Address"), max_length=255, blank=False, null=False)
    address2 = models.CharField(_("Address2"), max_length=255, blank=True, null=True)
    address3 = models.CharField(_("Address3"), max_length=255, blank=True, null=True)
    department = models.CharField(_("Department"), max_length=128, blank=False, null=False)
    city = UpperCharField(_("City"), max_length=255, blank=False, null=False)
    zip_code = models.CharField(_("Zip code"), max_length=128, blank=False, null=False)
    phone_number = models.CharField(_("Phone number"), max_length=20, null=False, blank=False)
    fax = models.CharField(_("Fax"), max_length=20, null=True, blank=True)
    badge_html_color = models.CharField(_("Badge color (HTML)"), max_length=7)
    email = models.EmailField(_('Email'))
    mailing_list = models.EmailField(_('Mailing list'), blank=True, null=True)
    active = models.BooleanField(_("Active"), blank=False, null=False, default=True)
    master = models.BooleanField(_("Master"), default=True)
    signed_charter = models.BooleanField(_("Signed charter"), default=False)
    data_source_plugin = models.CharField(_("Accounts source plugin"), max_length=256, null=True, blank=True,
        choices=settings.AVAILABLE_ACCOUNTS_PLUGINS,
    )
    data_source_settings = models.JSONField(_("Accounts source plugin settings"), null=True, blank=True)
    logo = models.ImageField(
        _("Logo"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )
    signature = models.ImageField(
        _("Signature"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )
    objects = models.Manager()  # default manager
    activated = ActiveManager.from_queryset(EstablishmentQuerySet)()

    def __str__(self):
        return "{} : {}{}".format(self.code, self.label, _(" (master)") if self.master else "")


    class Meta:
        verbose_name = _('Establishment')
        verbose_name_plural = _('Establishments')
        ordering = ['label', ]


class Structure(models.Model):
    """
    Structure class
    """

    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=128)
    mailing_list = models.EmailField(_('Mailing list address'), blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    objects = models.Manager()  # default manager
    activated = ActiveManager.from_queryset(StructureQuerySet)()  # returns only activated structures

    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.SET_NULL,
        blank=False, null=True, related_name='structures')

    def __str__(self):
        return f"{self.code} : {self.label}"


    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A structure with this code already exists'))

    class Meta:
        verbose_name = _('Structure')
        verbose_name_plural = _('Structures')
        ordering = ['label', ]


class HighSchool(models.Model):
    """
    HighSchool class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    address = models.CharField(_("Address"), max_length=255, blank=False, null=False)
    address2 = models.CharField(_("Address2"), max_length=255, blank=True, null=True)
    address3 = models.CharField(_("Address3"), max_length=255, blank=True, null=True)
    department = models.CharField(_("Department"), max_length=128, blank=False, null=False)
    city = UpperCharField(_("City"), max_length=255, blank=False, null=False)
    zip_code = models.CharField(_("Zip code"), max_length=128, blank=False, null=False)
    phone_number = models.CharField(_("Phone number"), max_length=20, null=False, blank=False)
    fax = models.CharField(_("Fax"), max_length=20, null=True, blank=True)
    email = models.EmailField(_('Email'))
    head_teacher_name = models.CharField(
        _("Head teacher name"), max_length=255, blank=False, null=False, help_text=_('civility last name first name'),
    )
    convention_start_date = models.DateField(_("Convention start date"), null=True, blank=True)
    convention_end_date = models.DateField(_("Convention end date"), null=True, blank=True)

    objects = models.Manager()  # default manager
    agreed = HighSchoolAgreedManager()  # returns only agreed Highschools

    postbac_immersion = models.BooleanField(_("Offer post-bachelor immersions"), default=False)
    immersions_proposal = PostBacImmersionManager()
    mailing_list = models.EmailField(_('Mailing list address'), blank=True, null=True)
    badge_html_color = models.CharField(_("Badge color (HTML)"), max_length=7)
    logo = models.ImageField(
        _("Logo"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )
    signature = models.ImageField(
        _("Signature"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )
    signed_charter = models.BooleanField(_("Signed charter"), default=False)

    def __str__(self):
        return f"{self.city} - {self.label}"

    class Meta:
        verbose_name = _('High school')
        unique_together = ('label', 'city')
        ordering = ['city', 'label', ]


def get_object_default_order(object_class):
    try:
        cls = apps.get_model('core', object_class)
        if cls.objects.all().count() == 0:
            return 1
        else:
            return cls.objects.all().aggregate(Max('order'))['order__max'] + 1
    except Exception as e:
        # Falling here because "Models aren't loaded yet"
        pass

    return None

class HighSchoolLevel(models.Model):
    """
    High school pupil levels
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    order = models.PositiveSmallIntegerField(_("Display order"), blank=False, null=True,
        default=partial(get_object_default_order, 'HighSchoolLevel')
    )
    is_post_bachelor = models.BooleanField(_("Is a post-bachelor level"), default=False)
    requires_bachelor_speciality = models.BooleanField(_("Requires bachelor speciality"), default=False)

    def __str__(self):
        return self.label

    def can_delete(self):
        return not self.high_school_student_record.exists()

    class Meta:
        verbose_name = _('High school level')
        verbose_name_plural = _('High school levels')
        ordering = ['order']


class PostBachelorLevel(models.Model):
    """
    Post bachelor student levels
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    order = models.PositiveSmallIntegerField(_("Display order"), blank=False, null=True,
        default=partial(get_object_default_order, 'PostBachelorLevel')
    )

    def __str__(self):
        return self.label

    def can_delete(self):
        return not self.high_school_student_record.exists()

    class Meta:
        verbose_name = _('Post bachelor level')
        verbose_name_plural = _('Post bachelor levels')
        ordering = ['order']


class StudentLevel(models.Model):
    """
    Student levels
    """
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    order = models.PositiveSmallIntegerField(_("Display order"), blank=False, null=True,
        default=partial(get_object_default_order, 'StudentLevel')
    )

    def __str__(self):
        return self.label

    def can_delete(self):
        return not self.student_record.exists()

    class Meta:
        verbose_name = _('Student level')
        verbose_name_plural = _('Student levels')
        ordering = ['order']


class ImmersionUser(AbstractUser):
    """
    Main user class
    """

    _user_filters = [
        lambda has_group, su: has_group or su,
        lambda has_group, su: has_group and not su,
    ]
    _groups = {
        'REF-TEC': 'operator',
        'REF-ETAB': 'establishment_manager',
        'REF-ETAB-MAITRE': 'master_establishment_manager',
        'REF-STR': 'structure_manager',
        'REF-LYC': 'high_school_manager',
        'ETU': 'student',
        'LYC': 'high_school_student',
        'INTER': 'speaker',
        'SRV-JUR': 'legal_department_staff',
        'VIS': 'visitor',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, name in self._groups.items():
            setattr(self, 'is_%s' % name, partial(self.has_groups, code, negated=False))

    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.SET_NULL,
        blank=True, null=True
    )

    structures = models.ManyToManyField(Structure, verbose_name=_("Structures"), blank=True, related_name='referents')

    highschool = models.ForeignKey(
        HighSchool,
        verbose_name=_('High school'),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="highschool_referent",
    )

    destruction_date = models.DateField(_("Account destruction date"), blank=True, null=True)

    validation_string = models.TextField(_("Account validation string"), blank=True, null=True, unique=True)

    recovery_string = models.TextField(_("Account password recovery string"), blank=True, null=True, unique=True)

    email = models.EmailField(_("Email"), blank=False, null=False, unique=True)

    def __str__(self):
        return "{} {}".format(self.last_name or _('(no last name)'), self.first_name or _('(no first name)'))

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
        return self._user_filters[negated](self.is_superuser, self.groups.filter(name__in=groups).exists())

    def has_course_rights(self, course_id):
        """
        Check if the user can update / delete a course
        :param course_id: Course id
        :return: boolean
        """
        if self.is_superuser or self.has_groups('REF-ETAB-MAITRE'):
            return True

        try:
            course = Course.objects.get(pk=course_id)
            course_structures = course.training.structures.all()
        except Course.DoesNotExist:
            return False

        valid_conditions = [
            self.is_establishment_manager() and course_structures & self.establishment.structures.all(),
            self.is_structure_manager() and course_structures & self.structures.all(),
            self.is_high_school_manager() and self.highschool and self.highschool == course.highschool
        ]

        if any(valid_conditions):
            return True

        return False

    def authorized_groups(self):
        # user_filter = {} if self.is_superuser else {'user__id': self.pk}
        user_filter = {'user__id': self.pk}
        return Group.objects.filter(**user_filter)

    def send_message(self, request, template_code, **kwargs):
        """
        Get a MailTemplate by its code, replace variables and send
        :param message_code: Code of message to send
        :return: True if message sent else False
        """
        try:
            template = MailTemplate.objects.get(code=template_code, active=True)
            logger.debug("Template found : %s" % template)
        except MailTemplate.DoesNotExist:
            msg = _("Email not sent : template %s not found or inactive" % template_code)
            logger.error(msg)
            return msg

        try:
            message_body = template.parse_vars(user=self, request=request, **kwargs)
            from immersionlyceens.libs.mails.variables_parser import Parser
            logger.debug("Message body : %s" % message_body)
            send_email(self.email, template.subject, message_body)
        except Exception as e:
            logger.exception(e)
            msg = _("Couldn't send email : %s" % e)
            return msg

        return None

    def validate_account(self):
        self.validation_string = None
        self.destruction_date = None
        self.save()

    def get_localized_destruction_date(self):
        return _date(self.destruction_date, "l j F Y")

    def get_cleaned_username(self):
        return self.get_username()
        # return self.get_username().replace(settings.USERNAME_PREFIX, '')

    def get_login_page(self):
        if self.is_high_school_manager() and self.highschool:
            return "/immersion/login/ref-lyc"
        else:
            return "/immersion/login"

    def is_valid(self):
        """
        :return: True if account is validated else False
        """
        return self.validation_string is None

    def get_high_school_student_record(self):
        try:
            return self.high_school_student_record
        except ObjectDoesNotExist:
            return None

    def get_student_record(self):
        try:
            return self.student_record
        except ObjectDoesNotExist:
            return None

    def get_visitor_record(self) -> Optional[Any]:
        try:
            return self.visitor_record
        except ObjectDoesNotExist:
            return None

    def get_authorized_structures(self):
        if self.is_superuser or self.is_master_establishment_manager() or self.is_operator():
            return Structure.activated.all()
        if self.is_establishment_manager() and self.establishment:
            return Structure.activated.filter(establishment=self.establishment)
        if self.is_structure_manager():
            return self.structures.all()

        return Structure.objects.none()

    def set_validation_string(self):
        """
        Generates and return a new validation string
        """
        self.validation_string = uuid.uuid4().hex
        self.save()
        return self.validation_string

    def set_recovery_string(self):
        """
        Generates and return a new password recovery string
        """
        self.recovery_string = uuid.uuid4().hex
        self.save()

    def remaining_registrations_count(self):
        """
        Based on the calendar mode and the current immersions registrations,
        returns a dictionnary with remaining registrations count for
        both semesters and year

        If there's no calendar or the current user is not a student, return 0
        for each period
        """
        current_semester_1_regs = 0
        current_semester_2_regs = 0
        current_year_regs = 0
        record = None

        remaining = {
            'semester1': 0,
            'semester2': 0,
            'annually': 0,
        }

        calendar = None

        # No calendar : no registration
        try:
            calendar = Calendar.objects.first()
        except Exception:
            return remaining

        # Not a student or no record yet : no registration
        if self.is_high_school_student():
            record = self.get_high_school_student_record()
        elif self.is_student():
            record = self.get_student_record()
        elif self.is_visitor():
            record = self.get_visitor_record()

        if not record or not record.is_valid():
            return remaining

        if calendar.calendar_mode == 'SEMESTER':
            current_semester_1_regs = self.immersions.filter(
                slot__date__gte=calendar.semester1_start_date,
                slot__date__lte=calendar.semester1_end_date,
                cancellation_type__isnull=True,
                slot__event__isnull=True,
                slot__visit__isnull=True,
            ).count()
            current_semester_2_regs = self.immersions.filter(
                slot__date__gte=calendar.semester2_start_date,
                slot__date__lte=calendar.semester2_end_date,
                cancellation_type__isnull=True,
                slot__event__isnull=True,
                slot__visit__isnull=True,
            ).count()
        else:
            current_year_regs = self.immersions.filter(
                slot__date__gte=calendar.year_start_date,
                slot__date__lte=calendar.year_end_date,
                cancellation_type__isnull=True,
                slot__event__isnull=True,
                slot__visit__isnull=True,
            ).count()

        return {
            'semester1': (record.allowed_first_semester_registrations or 0) - current_semester_1_regs,
            'semester2': (record.allowed_second_semester_registrations or 0) - current_semester_2_regs,
            'annually': (record.allowed_global_registrations or 0) - current_year_regs,
        }

    def set_increment_registrations_(self, type):
        """
        Updates student registrations remaining based on type parameter
        type values are annual/semester1/semester2
        """
        record = None

        if self.is_high_school_student():
            record = self.get_high_school_student_record()
        elif self.is_student():
            record = self.get_student_record()
        elif self.is_visitor():
            record = self.get_visitor_record()

        if not record or not record.is_valid():
            return

        if type == 'annual':
            record.allowed_global_registrations += 1

        elif type == 'semester1':
            record.allowed_first_semester_registrations += 1

        elif type == 'semester2':
            record.allowed_second_semester_registrations += 1
        else:
            return

        record.save()



    def can_register_slot(self, slot=None):
        errors = []

        # Returns True if no restrictions are found
        if not slot or not slot.establishments_restrictions and not slot.levels_restrictions:
            return True, errors

        if self.is_high_school_student():
            record = self.get_high_school_student_record()

            if not record or not record.is_valid():
                errors.append(_("High school record not found or not valid"))
                return False, errors

            high_school_conditions = [
                slot.allowed_highschools.exists(),
                record.highschool in slot.allowed_highschools.all()
            ]

            levels_conditions = [
                slot.allowed_highschool_levels.exists() and record.level in slot.allowed_highschool_levels.all(),
                slot.allowed_post_bachelor_levels.exists() and
                    record.post_bachelor_level in slot.allowed_post_bachelor_levels.all()
            ]

            if slot.establishments_restrictions and not all(high_school_conditions):
                errors.append(_('High schools restrictions in effect'))
            if slot.levels_restrictions and not any(levels_conditions):
                errors.append(_('High school or post bachelor levels restrictions in effect'))

            if errors:
                return False, errors

        if self.is_student():
            record = self.get_student_record()

            if not record:
                errors.append(_("Student record not found"))
                return False, errors

            establishment_conditions = [
                slot.allowed_establishments.exists(),
                record.home_institution()[0] in slot.allowed_establishments.values_list('label', flat=True)
            ]

            levels_conditions = [
                slot.allowed_student_levels.exists(),
                record.level in slot.allowed_student_levels.all()
            ]

            if slot.establishments_restrictions and not all(establishment_conditions):
                errors.append(_('Establishments restrictions in effect'))

            if slot.levels_restrictions and not all(levels_conditions):
                errors.append(_('Student levels restrictions in effect'))

            if errors:
                return False, errors

        # Restrictions checks for visitors
        if self.is_visitor():
            record = self.get_visitor_record()

            if not record or not record.is_valid():
                errors.append(_("Visitor record not found or not valid"))
                return False, errors

            # visitors can register to "open to all" slots
            if slot.levels_restrictions or slot.establishments_restrictions:
                errors.append(_('Slot restrictions in effect'))
                return False, errors

        return True, errors

    class Meta:
        verbose_name = _('User')
        ordering = ['last_name', 'first_name', ]


class TrainingDomain(models.Model):
    """
    Training domain class
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A training domain with this label already exists'))

    class Meta:
        verbose_name = _('Training domain')
        verbose_name_plural = _('Training domains')
        ordering = ['label', ]


class TrainingSubdomain(models.Model):
    """
    Training subdomain class
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    training_domain = models.ForeignKey(
        TrainingDomain,
        verbose_name=_("Training domain"),
        default=None,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name='Subdomains',
    )
    active = models.BooleanField(_("Active"), default=True)
    objects = models.Manager()  # default manager
    activated = ActiveManager()


    def __str__(self):
        domain = self.training_domain or _("No domain")
        return f"{domain} - {self.label}"


    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A training sub domain with this label already exists'))

    class Meta:
        verbose_name = _('Training sub domain')
        verbose_name_plural = _('Training sub domains')
        ordering = ['label', ]


class Training(models.Model):
    """
    Training class
    """

    label = models.CharField(_("Label"), max_length=128)
    training_subdomains = models.ManyToManyField(
        TrainingSubdomain, verbose_name=_("Training subdomains"), blank=False, related_name='Trainings',
    )
    structures = models.ManyToManyField(Structure, verbose_name=_("Structures"), blank=True, related_name='Trainings')
    url = models.URLField(_("Website address"), max_length=256, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    highschool = models.ForeignKey(HighSchool, verbose_name=_("High school"), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='trainings'
    )

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A training with this label already exists'))

    def is_highschool(self) -> bool:
        """Return True if highschool is set"""
        return self.highschool is not None

    def is_structure(self) -> bool:
        """Return True if structure is set"""
        return self.structures is not None and self.structures.count() > 0

    def can_delete(self):
        return not self.courses.all().exists()

    def distinct_establishments(self):
        return Establishment.objects.filter(structures__in=self.structures.all()).distinct()


    class Meta:
        verbose_name = _('Training')
        verbose_name_plural = _('Trainings')
        ordering = ['label', ]


class Campus(models.Model):
    """
    Campus class
    """

    label = models.CharField(_("Label"), max_length=255)
    active = models.BooleanField(_("Active"), default=True)

    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.SET_NULL,
        blank=False, null=True)


    def __str__(self):
        return f"{self.label} ({self.establishment.label if self.establishment else '-'})"

    class Meta:
        verbose_name = _('Campus')
        verbose_name_plural = _('Campus')
        ordering = ['label', ]


class BachelorMention(models.Model):
    """
    Bachelor degree mentions
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A bachelor mention with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Technological bachelor series')
        verbose_name_plural = pgettext('tbs_plural', 'Technological bachelor series')
        ordering = ['label', ]


class Building(models.Model):
    """
    Building class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    campus = models.ForeignKey(
        Campus, verbose_name=_("Campus"), default=None, on_delete=models.CASCADE, related_name="buildings",
    )
    url = models.URLField(_("Url"), max_length=200, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    def __str__(self):
        return self.label


    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A building with this label for the same campus already exists'))

    class Meta:
        verbose_name = _('Building')
        unique_together = ('campus', 'label')
        ordering = ['label', ]



class CancelType(models.Model):
    """
    Cancel type
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A cancel type with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Cancel type')
        verbose_name_plural = _('Cancel types')
        ordering = ['label', ]


class CourseType(models.Model):
    """
    Course type
    """

    label = models.CharField(_("Short label"), max_length=256, unique=True)
    full_label = models.CharField(_("Full label"), max_length=256, unique=True, null=False, blank=False)
    active = models.BooleanField(_("Active"), default=True)


    def __str__(self):
        """str"""
        return f"{self.full_label} ({self.label})"


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A course type with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Course type')
        verbose_name_plural = _('Course type')
        ordering = ['label', ]


class GeneralBachelorTeaching(models.Model):
    """
    General bachelor specialty teaching
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)


    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A specialty teaching with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('General bachelor specialty teaching')
        verbose_name_plural = _('General bachelor specialties teachings')
        ordering = ['label', ]


class PublicType(models.Model):
    """
    Public type
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    objects = models.Manager()  # default manager
    activated = ActiveManager()


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A public type with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Public type')
        verbose_name_plural = _('Public types')
        ordering = ['label', ]


class UniversityYear(models.Model):
    """
    University year
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=False)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))
    registration_start_date = models.DateField(_("Registration date"))
    purge_date = models.DateField(_("Purge date"), null=True)


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A university year with this label already exists'))


    def save(self, *args, **kwargs):
        if not UniversityYear.objects.filter(active=True).exists():
            self.active = True

        super().save(*args, **kwargs)


    def date_is_between(self, _date):
        return self.start_date <= _date <= self.end_date

    class Meta:
        """Meta class"""
        verbose_name = _('University year')
        verbose_name_plural = _('University years')
        ordering = ['label', ]


class Holiday(models.Model):
    """
    Holidays
    """
    label = models.CharField(_("Label"), max_length=256, unique=True)
    date = models.DateField(_("Date"))


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A holiday with this label already exists'))

    @classmethod
    def date_is_a_holiday(cls, _date):
        return Holiday.objects.filter(date=_date).exists()

    class Meta:
        """Meta class"""
        verbose_name = _('Holiday')
        verbose_name_plural = _('Holidays')
        ordering = ['label', ]


class Vacation(models.Model):
    """
    Vacations
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A vacation with this label already exists'))


    def date_is_between(self, _date):
        return self.start_date <= _date and _date <= self.end_date


    @classmethod
    def date_is_inside_a_vacation(cls, _date):
        """
        Returns True if _date is within a Vacation period
        """
        if not isinstance(_date, datetime.date):
            logger.error("'%s' is not an object of type 'datetime.date'", _date)
            return False

        return Vacation.objects.filter(start_date__lte=_date, end_date__gte=_date).exists()


    @classmethod
    def get_vacation_period(cls, _date):
        """
        Return the Vacation object _date is within, else None
        """
        if not isinstance(_date, datetime.date):
            logger.error("'%s' is not an object of type 'datetime.date'", _date)
            return None

        qs = Vacation.objects.filter(start_date__lte=_date, end_date__gte=_date)

        if qs.exists():
            return qs.first()
        else:
            return None


    class Meta:
        """Meta class"""
        verbose_name = _('Vacation')
        verbose_name_plural = _('Vacations')
        ordering = ['label', ]


class Calendar(models.Model):
    """
    Semesters or annual dates for current university year
    """

    CALENDAR_MODE = [
        ('YEAR', _('Year')),
        ('SEMESTER', _('Semester')),
    ]

    label = models.CharField(_("Label"), max_length=256, unique=True)
    calendar_mode = models.CharField(_("Calendar mode"), max_length=16, choices=CALENDAR_MODE, default="YEAR")

    year_start_date = models.DateField(_("Year start date"), null=True, blank=True)
    year_end_date = models.DateField(_("Year end date"), null=True, blank=True)
    year_registration_start_date = models.DateField(_("Year start registration date"), null=True, blank=True)
    year_nb_authorized_immersion = models.PositiveIntegerField(_("Number of authorized immersions per year"), default=4)

    semester1_start_date = models.DateField(_("Semester 1 start date"), null=True, blank=True)
    semester1_end_date = models.DateField(_("Semester 1 end date"), null=True, blank=True)
    semester1_registration_start_date = models.DateField(_("Semester 1 start registration date"), null=True, blank=True)
    semester2_start_date = models.DateField(_("Semester 2 start date"), null=True, blank=True)
    semester2_end_date = models.DateField(_("Semester 2 end date"), null=True, blank=True)
    semester2_registration_start_date = models.DateField(_("Semester 2 start registration date"), null=True, blank=True)
    nb_authorized_immersion_per_semester = models.PositiveIntegerField(
        _("Number of authorized immersions per semester"), default=2
    )

    global_evaluation_date = models.DateField(_("Global evaluation send date"), null=True, blank=True)


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A calendar with this label already exists'))


    def date_is_between(self, _date):
        if self.calendar_mode == 'YEAR':
            return self.year_start_date <= _date and _date <= self.year_end_date
        else:
            return (self.semester1_start_date <= _date <= self.semester1_end_date) or (
                self.semester2_start_date <= _date <= self.semester2_end_date
            )


    def which_semester(self, _date):
        if self.calendar_mode == 'SEMESTER':
            if self.semester1_start_date <= _date <= self.semester1_end_date:
                return 1
            elif self.semester2_start_date <= _date <= self.semester2_end_date:
                return 2
        return None


    def get_limit_dates(self, _date):
        sem = self.which_semester(_date)
        if sem == 1:
            return {
                'start': self.semester1_start_date,
                'end': self.semester1_end_date,
            }
        elif sem == 2:
            return {
                'start': self.semester2_start_date,
                'end': self.semester2_end_date,
            }
        else:
            return {
                'start': self.year_start_date,
                'end': self.year_end_date,
            }

    class Meta:
        """Meta class"""
        verbose_name = _('Calendar')
        verbose_name_plural = _('Calendars')
        ordering = ['label', ]


class Course(models.Model):
    """
    Course class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)

    training = models.ForeignKey(
        Training, verbose_name=_("Training"), null=False, blank=False, on_delete=models.CASCADE, related_name="courses",
    )

    structure = models.ForeignKey(
        Structure,
        verbose_name=_("Structure"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    highschool = models.ForeignKey(
        HighSchool,
        verbose_name=_("High school"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    published = models.BooleanField(_("Published"), default=True)

    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='courses')

    url = models.URLField(_("Website address"), max_length=1024, blank=True, null=True)


    def __str__(self):
        return self.label


    def get_structures_queryset(self):
        return self.training.structures.all()


    def free_seats(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: number of seats as the sum of seats of all slots under this course
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']


    def published_slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of published slots under this course
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        return self.slots.filter(**filters).count()


    def slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of slots under this course, published or not
        """
        if speaker_id:
            return self.slots.filter(speakers=speaker_id).count()
        else:
            return self.slots.all().count()


    def registrations_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: the number of non-cancelled registered students on all the slots
        under this course (past and future)
        """
        filters = {'slot__course': self, 'cancellation_type__isnull': True}

        if speaker_id:
            filters['slot__speakers'] = speaker_id

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()


    def get_alerts_count(self):
        return UserCourseAlert.objects.filter(course=self, email_sent=False).count()



    def get_etab_or_high_school(self):
        if not self.highschool:
            return self.structure
        else:
            return self.highschool

    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        # unique_together = ('training', 'label') # Obsolete and will soon be removed
        constraints = [
            models.UniqueConstraint(
                fields=['highschool', 'training', 'label'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_highschool_course'
            ),
            models.UniqueConstraint(
                fields=['structure', 'training', 'label'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_structure_course'
            )
        ]
        ordering = ['label', ]


class Visit(models.Model):
    """
    Visit class
    """

    purpose = models.CharField(_("Purpose"), max_length=256)
    published = models.BooleanField(_("Published"), default=True)

    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.CASCADE,
        blank=False, null=False, related_name='visits')

    structure = models.ForeignKey(Structure, verbose_name=_("Structure"), null=True, blank=True,
        on_delete=models.SET_NULL, related_name="visits",
    )

    highschool = models.ForeignKey(HighSchool, verbose_name=_('High school'), null=False, blank=False,
        on_delete=models.CASCADE, related_name="visits",
    )

    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='visits')

    def __str__(self):
        if not self.establishment_id:
            return super().__str__()

        if not self.structure:
            return f"{self.establishment.code} - {self.highschool} : {self.purpose}"
        else:
            return f"{self.establishment.code} ({self.structure.code}) - {self.highschool} : {self.purpose}"


    def can_delete(self):
        today = timezone.now().date()
        try:
            current_year = UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            return True

        return current_year.date_is_between(today) and not self.slots.all().exists()

    def free_seats(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: number of seats as the sum of seats of all slots under this visit
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']

    def published_slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of published slots under this visit
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        return self.slots.filter(**filters).count()

    def slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of slots under this visit, published or not
        """
        if speaker_id:
            return self.slots.filter(speakers=speaker_id).count()
        else:
            return self.slots.all().count()

    def registrations_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: the number of non-cancelled registered students on all the slots
        under this visit (past and future)
        """
        filters = {'slot__visit': self, 'cancellation_type__isnull': True}

        if speaker_id:
            filters['slot__speakers'] = speaker_id

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['establishment', 'structure', 'highschool', 'purpose'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_visit'
            ),
        ]
        verbose_name = _('Visit')
        verbose_name_plural = _('Visits')


class OffOfferEventType(models.Model):
    """Off offer event type"""

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    objects = models.Manager()
    activated = ActiveManager()

    def __str__(self) -> str:
        return f"{self.label}"

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as exc:
            raise ValidationError(_('An off offer event type with this label already exists')) from exc

    def can_delete(self) -> bool:
        """Check if you can delete an off offer event type"""
        return not OffOfferEvent.objects.filter(event_type=self).exists()

    class Meta:
        verbose_name = _('Off offer event type')
        verbose_name_plural = _('Off offer event types')
        ordering = ('label',)


class OffOfferEvent(models.Model):
    """
    Off-offer event class
    """

    label = models.CharField(_("Label"), max_length=256)
    description = models.CharField(_("Description"), max_length=256)
    published = models.BooleanField(_("Published"), default=True)

    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.CASCADE,
        blank=True, null=True, related_name='events')

    structure = models.ForeignKey(Structure, verbose_name=_("Structure"), null=True, blank=True,
        on_delete=models.SET_NULL, related_name="events",
    )

    highschool = models.ForeignKey(HighSchool, verbose_name=_('High school'), null=True, blank=True,
        on_delete=models.CASCADE, related_name="events",
    )

    event_type = models.ForeignKey(OffOfferEventType, verbose_name=_('Event type'), null=False, blank=False,
        on_delete=models.CASCADE, related_name="events",
    )

    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='events')

    def __str__(self):
        if self.establishment:
            event_str = self.establishment.short_label
            if self.structure:
                event_str += f" - {self.structure.code}"
        else:
            event_str = f"{self.highschool.city} - {self.highschool.label}"

        event_str += f" : {self.label}"

        return event_str


    def event_label(self):
        return f"{self.label} - {self.description}"


    def can_delete(self):
        today = timezone.now().date()
        try:
            current_year = UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            return True

        return current_year.date_is_between(today) and not self.slots.all().exists()

    def free_seats(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: number of seats as the sum of seats of all slots under this event
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']

    def published_slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of published slots under this event
        """
        filters = {'published': True}

        if speaker_id:
            filters['speakers'] = speaker_id

        return self.slots.filter(**filters).count()

    def slots_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        Return number of slots under this event, published or not
        """
        if speaker_id:
            return self.slots.filter(speakers=speaker_id).count()
        else:
            return self.slots.all().count()

    def registrations_count(self, speaker_id=None):
        """
        :speaker_id: optional : only consider slots attached to 'speaker'
        :return: the number of non-cancelled registered students on all the slots
        under this event (past and future)
        """
        filters = {'slot__event': self, 'cancellation_type__isnull': True}

        if speaker_id:
            filters['slot__speakers'] = speaker_id

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()

    def clean(self):
        if [self.establishment, self.highschool].count(None) != 1:
            raise ValidationError("You must select one of : Establishment or High school")

    def get_etab_or_high_school(self):
        if not self.highschool:
            return self.establishment
        else:
            return self.highschool

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['establishment', 'structure', 'label', 'event_type'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_establishment_event'
            ),
            models.UniqueConstraint(
                fields=['highschool', 'label', 'event_type'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_highschool_event'
            ),
        ]
        verbose_name = _('Off-offer event')
        verbose_name_plural = _('Off-offer events')


class MailTemplateVars(models.Model):
    code = models.CharField(_("Code"), max_length=64, blank=False, null=False, unique=True)
    description = models.CharField(_("Description"), max_length=128, blank=False, null=False, unique=True)

    def __str__(self):
        return f"{self.code} : {self.description}"

    class Meta:
        verbose_name = _('Template variable')
        verbose_name_plural = _('Template variables')
        ordering = ['code', ]


class MailTemplate(models.Model):
    """
    Mail templates with HTML content
    """

    code = models.CharField(_("Code"), max_length=128, blank=False, null=False, unique=True)
    label = models.CharField(_("Label"), max_length=128, blank=False, null=False, unique=True)
    description = models.CharField(_("Description"), max_length=512, blank=False, null=False)
    subject = models.CharField(_("Subject"), max_length=256, blank=False, null=False)
    body = models.TextField(_("Body"), blank=False, null=False)
    active = models.BooleanField(_("Active"), default=True)

    available_vars = models.ManyToManyField(
        MailTemplateVars, related_name='mail_templates', verbose_name=_("Available variables"),
    )

    def __str__(self):
        return f"{self.code} : {self.label}"


    def parse_vars(self, user, request, **kwargs):
        # Import parser here because it depends on core models
        from immersionlyceens.libs.mails.variables_parser import parser

        return parser(
            user=user, request=request, message_body=self.body, vars=[v for v in self.available_vars.all()], **kwargs,
        )

    class Meta:
        verbose_name = _('Mail template')
        verbose_name_plural = _('Mail templates')
        ordering = ['label', ]


class InformationText(models.Model):
    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    code = models.CharField(_("Code"), max_length=64, blank=False, null=False,)
    # 10K chars => MOA demand
    content = models.TextField(_('Content'), max_length=10000, blank=False, null=False)
    description = models.TextField(_('Description'), max_length=2000, blank=False, null=False, default='')
    active = models.BooleanField(_("Active"), default=True)


    def get_documents_id(self):
        find = re.compile(r'(?P<pub>\/dl\/pubdoc\/(?P<pk>\d+))')
        return list({e[1] for e in re.findall(find, self.content)})


    @classmethod
    def get_all_documents_id(cls):
        texts = InformationText.objects.all()
        l = []
        for text in texts:
            for _id in text.get_documents_id():
                l.append(int(_id))

        return list(set(l))


    @classmethod
    def update_documents_publishment(cls):
        texts_docs_id = cls.get_all_documents_id()

        PublicDocument.objects.filter(id__in=texts_docs_id).update(published=True)
        PublicDocument.objects.filter(~Q(id__in=texts_docs_id)).update(published=False)


    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save()
        self.__class__.update_documents_publishment()


    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        self.__class__.update_documents_publishment()


    def __str__(self):
        return self.label

    class Meta:
        verbose_name = _('Information text')
        verbose_name_plural = _('Information texts')
        ordering = ['label', ]


class AccompanyingDocument(models.Model):
    """
    AccompanyingDocument class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False, unique=True)
    public_type = models.ManyToManyField(
        PublicType, verbose_name=_("Public type"), blank=False, related_name="publictypes",
    )
    description = models.TextField(_("Description"), blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)
    objects = CustomDeleteManager()
    activated = ActiveManager()

    document = models.FileField(
        _("Document"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(settings.CONTENT_TYPES),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )


    def __str__(self):
        """str"""
        return self.label


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An accompanying document with this label already exists'))


    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from document Filefield"""
        self.document.storage.delete(self.document.name)
        super().delete()


    def get_types(self):
        # TODO: ???
        return ",".join([t.label for t in self.public_type.all()])

    get_types.short_description = _('Public type')

    class Meta:
        """Meta class"""
        verbose_name = _('Accompanying document')
        verbose_name_plural = _('Accompanying documents')
        ordering = ['label', ]


class PublicDocument(models.Model):
    """
    PublicDocument class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    document = models.FileField(
        _("Document"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                   % {
                        'authorized_types': ', '.join(settings.CONTENT_TYPES),
                        'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                   },
    )
    published = models.BooleanField(_("Published"), default=False)

    objects = CustomDeleteManager()

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A public document with this label already exists'))

    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from document Filefield"""
        self.document.storage.delete(self.document.name)
        super().delete()

    def get_all_texts_id(cls):
        texts = InformationText.objects.all()
        l = []
        for text in texts:
            for _id in text.get_documents_id():
                if int(_id) == cls.pk:
                    l.append(text.id)

        return list(set(l))

    class Meta:
        """Meta class"""
        verbose_name = _('Public document')
        verbose_name_plural = _('Public documents')
        ordering = ['label', ]


class EvaluationType(models.Model):
    """
    Evaluation type class
    """

    code = models.CharField(_("Code"), max_length=30, unique=True)
    label = models.CharField(_("Label"), max_length=128)


    def __str__(self):
        """str"""
        return f'{self.code} : {self.label}'


    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An evaluation type with this code already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Evaluation type')
        verbose_name_plural = _('Evaluation types')
        ordering = ['label', ]


class EvaluationFormLink(models.Model):
    """
    Evaluation form links class
    """

    evaluation_type = models.OneToOneField(
        EvaluationType,
        verbose_name=_("Evaluation type"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="evaluationtypes",
        primary_key=True,
    )

    url = models.URLField(_("Link"), max_length=256, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=False)

    def __str__(self):
        """str"""
        return f'{self.evaluation_type.label} : {self.url}'


    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An evaluation form link with this evaluation type already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Evaluation form link')
        verbose_name_plural = _('Evaluation forms links')
        ordering = ['evaluation_type', ]


class Slot(models.Model):
    """
    Slot class
    """

    course = models.ForeignKey(
        Course, verbose_name=_("Course"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )
    course_type = models.ForeignKey(
        CourseType,
        verbose_name=_("Course type"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="slots",
    )

    visit = models.ForeignKey(
        Visit, verbose_name=_("Visit"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )

    event = models.ForeignKey(
        OffOfferEvent, verbose_name=_("Off offer event"), null=True, blank=True, on_delete=models.CASCADE,
        related_name="slots",
    )

    campus = models.ForeignKey(
        Campus, verbose_name=_("Campus"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )
    building = models.ForeignKey(
        Building, verbose_name=_("Building"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )
    room = models.CharField(_("Room"), max_length=128, blank=True, null=True)

    date = models.DateField(_('Date'), blank=True, null=True)
    start_time = models.TimeField(_('Start time'), blank=True, null=True)
    end_time = models.TimeField(_('End time'), blank=True, null=True)

    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='slots', blank=True)

    n_places = models.PositiveIntegerField(_('Number of places'))
    additional_information = models.CharField(_('Additional information'), max_length=128, null=True, blank=True)

    url = models.URLField(_("Website address"), max_length=512, blank=True, null=True)

    published = models.BooleanField(_("Published"), default=True, null=False)

    face_to_face = models.BooleanField(_("Face to face"), default=True, null=False, blank=True)

    establishments_restrictions = models.BooleanField(
        _("Use establishments restrictions"), default=False, null=False, blank=True
    )

    levels_restrictions = models.BooleanField(
        _("Use levels restrictions"), default=False, null=False, blank=True
    )

    allowed_establishments = models.ManyToManyField(
        Establishment, verbose_name=_("Allowed establishments"), related_name='+', blank=True
    )

    allowed_highschools = models.ManyToManyField(
        HighSchool, verbose_name=_("Allowed high schools"), related_name='+', blank=True
    )

    # new fields
    allowed_highschool_levels = models.ManyToManyField(
        HighSchoolLevel, verbose_name=_("Allowed high school levels"), related_name='+', blank=True
    )
    allowed_student_levels = models.ManyToManyField(
        StudentLevel, verbose_name=_("Allowed student levels"), related_name='+', blank=True
    )
    allowed_post_bachelor_levels = models.ManyToManyField(
        PostBachelorLevel, verbose_name=_("Allowed post bachelor levels"), related_name='+', blank=True
    )

    def get_establishment(self):
        """
        Get the slot establishment depending of the slot type (visit, course, event)
        """
        if self.course_id and self.course.structure_id:
            return self.course.structure.establishment
        elif self.visit_id and self.visit.establishment_id:
            return self.visit.establishment
        elif self.event_id and self.event.establishment_id:
            return self.event.establishment

        return None

    def get_structure(self):
        """
        Get the slot structure depending of the slot type (visit, course, event)
        """
        if self.course_id and self.course.structure_id:
            return self.course.structure
        elif self.visit_id and self.visit.structure_id:
            return self.visit.structure
        elif self.event_id and self.event.structure_id:
            return self.event.structure

        return None

    def get_highschool(self):
        """
        Get the slot high school depending of the slot type (visit, course, event)
        """
        if self.course_id and self.course.highschool_id:
            return self.course.highschool
        elif self.visit_id and self.visit.highschool_id:
            return self.visit.highschool
        elif self.event_id and self.event.highschool_id:
            return self.event.highschool

        return None


    def available_seats(self):
        """
        :return: number of available seats for instance slot
        """
        # TODO: check if we need to filter published slots only ???
        s = self.n_places - Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()
        return 0 if s < 0 else s


    def registered_students(self):
        """
        :return: number of registered students for instance slot
        """
        # TODO: check if we need to filter published slots only ???
        return Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()


    def clean(self):
        if [self.course, self.visit, self.event].count(None) != 2:
            raise ValidationError("You must select one of : Course, Visit or Event")

    def __str__(self):
        slot_type = _("No type yet")
        date = self.date or _("date unknown")
        start_time = self.start_time or _("start time unknown")
        end_time = self.end_time or _("end time unknown")

        if self.visit:
            slot_type = _(f"Visit - {self.visit.highschool}")
        elif self.course:
            slot_type = _(f"Course - {self.course_type} {self.course.label}")
        elif self.event:
            slot_type = _(f"Event - {self.event.label}")

        return f"{slot_type} : {date} : {start_time}-{end_time}"


    def get_allowed_highschool_levels(self):
        return [level.label for level in self.allowed_highschool_levels.all()]

    def get_allowed_students_levels(self):
        return [level.label for level in self.allowed_student_levels.all()]

    def get_allowed_post_bachelor_levels(self):
        return [level.label for level in self.allowed_post_bachelor_levels.all()]

    def get_label(self):
        """
        Returns course label, event label or visit purpose
        """
        if self.is_course():
            return self.course.label
        if self.is_visit():
            return self.visit.purpose
        if self.is_event():
            return self.event.label

        return _("Unknown")

    def is_course(self):
        """
        Returns True if slot is a course slot else False
        """
        return True if self.course else False

    def is_visit(self):
        """
        Returns True if slot is a visit slot else False
        """
        return True if self.visit else False

    def is_event(self):
        """
        Returns True if slot is an event slot else False
        """
        return True if self.event else False

    def get_type(self):
        """
        returns:
        'course' if slot is a course slot
        'visit' if slot is a visit slot
        'event' if slot is an event slot
        """
        if self.is_course():
            return 'course'
        if self.is_visit():
            return 'visit'
        if self.is_event():
            return 'event'

    def can_show_url(self):
        # Showing remote course url if today date >= NB_DAYS_SLOT_REMINDER
        today = datetime.datetime.today().date()
        default_value = 4

        # Default settings value
        try:
            days = settings.DEFAULT_NB_DAYS_SLOT_REMINDER
        except AttributeError:
            days = default_value

        # Configured value
        try:
            days = int(get_general_setting('NB_DAYS_SLOT_REMINDER'))
        except (ValueError, NameError):
            pass

        # If configured value is invalid
        if days <= 0:
            days = default_value

        return self.date >= today - datetime.timedelta(days=days)


    class Meta:
        verbose_name = _('Slot')
        verbose_name_plural = _('Slots')


class Immersion(models.Model):
    """
    Student registration to a slot
    """

    ATT_STATUS = [
        (0, _('Not entered')),
        (1, _('Present')),
        (2, _('Absent')),
    ]

    student = models.ForeignKey(
        ImmersionUser,
        verbose_name=_("Student"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="immersions",
    )

    slot = models.ForeignKey(
        Slot, verbose_name=_("Slot"), null=False, blank=False, on_delete=models.CASCADE, related_name="immersions",
    )

    cancellation_type = models.ForeignKey(
        CancelType,
        verbose_name=_("Cancellation type"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="immersions",
    )

    attendance_status = models.SmallIntegerField(_("Attendance status"), default=0, choices=ATT_STATUS)
    survey_email_sent = models.BooleanField(_("Survey notification status"), default=False)

    def get_attendance_status(self) -> str:
        """
        get attendance status
        :return: status
        """
        try:
            return self.ATT_STATUS[self.attendance_status][1]
        except KeyError:
            return ''

    class Meta:
        verbose_name = _('Immersion')
        verbose_name_plural = _('Immersions')


class GeneralSettings(models.Model):
    setting = models.CharField(_("Setting name"), max_length=128, unique=True)
    parameters = models.JSONField(_("Setting configuration"),
        blank=False,
        default=dict,
        validators=[JsonSchemaValidator(join(dirname(__file__), 'schemas', 'general_settings.json'))]
    )

    def __str__(self) -> str:
        return str(self.setting)

    class Meta:
        verbose_name = _('General setting')
        verbose_name_plural = _('General settings')
        ordering = ['setting', ]


class UserCourseAlert(models.Model):
    """
    Store alerts on free slots added by users
    """

    email = models.EmailField(_('Recipient'), blank=False, null=False)
    email_sent = models.BooleanField(_("Alert sent status"), default=False, blank=False, null=False)
    alert_date = models.DateField(_("Date"), auto_now_add=True)
    course = course = models.ForeignKey(
        Course, verbose_name=_("Course"), null=False, blank=False, on_delete=models.CASCADE, related_name="alerts",
    )

    class Meta:
        unique_together = ('email', 'course')
        verbose_name = _('Course free slot alert')
        verbose_name_plural = _('Course free slot alerts')
        ordering = ['-alert_date', ]


class HigherEducationInstitution(models.Model):
    """
    Database of french higher education schools (based on UAI codes)
    """

    uai_code = models.CharField(_("UAI Code"), max_length=20, primary_key=True, null=False)
    label = models.CharField(_("Label"), max_length=512, null=True, blank=True)
    city = models.CharField(_("City"), max_length=64, null=True, blank=True)
    department = models.CharField(_("Department"), max_length=64, null=True, blank=True)
    zip_code = models.CharField(_("Zip code"), max_length=10, null=True, blank=True)
    country = models.CharField(_("Country"), max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = _('Higher education institution')
        verbose_name_plural = _('Higher education institutions')
        ordering = ['label', ]


class AnnualStatistics(models.Model):
    """
    Data kept over years
    """
    year = models.CharField(_("Year label"), primary_key=True, max_length=256, null=False)
    platform_registrations = models.SmallIntegerField(_("Platform registrations count"), default=0)
    one_immersion_registrations = models.SmallIntegerField(
        _("Students registered to at least one immersion count"), default=0)
    multiple_immersions_registrations = models.SmallIntegerField(
        _("Students registered to more than one immersion count"), default=0)
    participants_one_immersion = models.SmallIntegerField(
        _("Participants in at least one immersion count"), default=0)
    participants_multiple_immersions = models.SmallIntegerField(
        _("Participants in multiple immersions count"), default=0)
    immersion_registrations = models.SmallIntegerField(_("Immersion registrations count"), default=0)
    seats_count = models.SmallIntegerField(_("Global seats count"), default=0)
    structures_count = models.SmallIntegerField(_("Participating structures count"), default=0)
    trainings_one_slot_count = models.SmallIntegerField(_("Trainings offering at least one slot count"), default=0)
    courses_one_slot_count = models.SmallIntegerField(_("Courses offering at least one slot count"), default=0)
    total_slots_count = models.SmallIntegerField(_("Total slots count"), default=0)
    approved_highschools = models.SmallIntegerField(_("Approved highschools count"), default=0)
    highschools_without_students = models.SmallIntegerField(_("Highschools with no students"), default=0)

    class Meta:
        verbose_name = _('Annual statistics')
        verbose_name_plural = _('Annual statistics')
        ordering = ['-year']


class CertificateLogo(models.Model):

    """
    CertificateLogo class (singleton)
    """

    logo = models.ImageField(
        _("Logo"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )

    objects = CustomDeleteManager()

    @classmethod
    def object(cls):
        """get only allowed object"""
        return cls._default_manager.all().first()

    # Singleton !
    def save(self, *args, **kwargs):
        """Save a singleton"""
        self.id = 1
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from logo Filefield"""
        self.logo.storage.delete(self.logo.name)
        super().delete()


    def __str__(self):
        """str"""
        return 'logo'

    class Meta:
        """Meta class"""
        verbose_name = _('Logo for attendance certificate')
        verbose_name_plural = _('Logo for attendance certificate')


class CertificateSignature(models.Model):
    """
    CertificateSignature class (singleton)
    """

    signature = models.ImageField(
        _("Signature"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )

    objects = CustomDeleteManager()

    @classmethod
    def object(cls):
        """get all objects"""
        return cls._default_manager.all().first()


    # Singleton !
    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)


    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from signature Filefield"""
        self.signature.storage.delete(self.signature.name)
        super().delete()


    def __str__(self):
        """str"""
        return 'signature'

    class Meta:
        """Meta class"""
        verbose_name = _('Signature for attendance certificate')
        verbose_name_plural = _('Signature for attendance certificate')

