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

from hijack.signals import hijack_started, hijack_ended

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Max, Q, Sum
from django.db.models.functions import Coalesce
from django.dispatch import receiver
from django.template.defaultfilters import date as _date, filesizeformat
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext, gettext_lazy as _, pgettext
from django_countries.fields import CountryField

from immersionlyceens.apps.core.managers import PostBacImmersionManager
from immersionlyceens.fields import UpperCharField
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.validators import JsonSchemaValidator

from ...libs.utils import get_general_setting
from .managers import (
    ActiveManager, CustomDeleteManager, EstablishmentQuerySet,
    HighSchoolAgreedManager, StructureQuerySet,
)

# from ordered_model.models import OrderedModel

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

def validate_slot_date(date: datetime.date):
    """
    :param date: the slot date to validate
    :return: Raises ValidationError Exception or nothing
    """
    # Past
    if date < timezone.localdate():
        raise ValidationError(
            _("You can't set a date in the past")
        )


class HigherEducationInstitution(models.Model):
    """
    Database of french higher education schools (based on UAI codes)
    @TODO : merge with UAI model ?
    """

    uai_code = models.CharField(_("UAI Code"), max_length=20, primary_key=True, null=False)
    label = models.CharField(_("Label"), max_length=512, null=True, blank=True)
    city = models.CharField(_("City"), max_length=64, null=True, blank=True)
    department = models.CharField(_("Department"), max_length=64, null=True, blank=True)
    zip_code = models.CharField(_("Zip code"), max_length=10, null=True, blank=True)
    country = models.CharField(_("Country"), max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.city} - {self.label} - {self.uai_code}"

    class Meta:
        verbose_name = _('Higher education institution')
        verbose_name_plural = _('Higher education institutions')
        ordering = ['city', 'label', ]


class UAI(models.Model):
    """
    UAI codes for establishments, mainly used for high schools
    """

    code = models.CharField(_("UAI Code"), max_length=20, primary_key=True, null=False)
    label = models.CharField(_("Label"), max_length=512, null=True, blank=True)
    city = models.CharField(_("City"), max_length=128, null=True, blank=True)
    academy = models.CharField(_("City"), max_length=128, null=True, blank=True)

    def __str__(self):
        academy = f"ac. {self.academy}" if self.academy else ""
        return " - ".join([self.city, academy, self.code, self.label])

    class Meta:
        verbose_name = _('Establishment with UAI')
        verbose_name_plural = _('Establishments with UAI')
        ordering = ['city', 'label', ]

class Establishment(models.Model):
    """
    Establishment class : highest structure level
    """
    code = models.CharField(_("Code"), max_length=16, unique=True)

    uai_reference = models.OneToOneField(
        HigherEducationInstitution,
        verbose_name=_('UAI reference'),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="establishment",
        unique=True,
    )

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
    is_host_establishment = models.BooleanField(_("Is host establishment"), default=True)
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
    certificate_header = models.TextField(_("Certificate header"), blank=True, null=True)
    certificate_footer = models.TextField(_("Certificate footer"), blank=True, null=True)
    objects = models.Manager()  # default manager
    activated = ActiveManager.from_queryset(EstablishmentQuerySet)()

    def __str__(self):
        return "{} : {}{}".format(self.code, self.label, _(" (master)") if self.master else "")

    def provides_accounts(self):
        return self.data_source_plugin is not None

    class Meta:
        verbose_name = _('Higher education establishment')
        verbose_name_plural = _('Higher education establishments')
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

    establishment = models.ForeignKey(
        Establishment,
        verbose_name=_("Establishment"),
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='structures'
    )

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
    Can also be used to enter secondary (middle) schools
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)

    country = CountryField(_("Country"), blank_label=gettext('select a country'), blank=True, null=True)
    address = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    address2 = models.CharField(_("Address2"), max_length=255, blank=True, null=True)
    address3 = models.CharField(_("Address3"), max_length=255, blank=True, null=True)
    department = models.CharField(_("Department"), max_length=128, blank=True, null=True)
    city = UpperCharField(_("City"), max_length=255, blank=True, null=True)
    zip_code = models.CharField(_("Zip code"), max_length=128, blank=True, null=True)
    phone_number = models.CharField(_("Phone number"), max_length=20, null=True, blank=True)
    fax = models.CharField(_("Fax"), max_length=20, null=True, blank=True)

    email = models.EmailField(_('Email'), null=True, blank=True)

    head_teacher_name = models.CharField(
        _("Head teacher name"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('civility last name first name'),
    )
    convention_start_date = models.DateField(_("Convention start date"), null=True, blank=True)
    convention_end_date = models.DateField(_("Convention end date"), null=True, blank=True)
    postbac_immersion = models.BooleanField(_("Offer post-bachelor immersions"), default=False)

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
    certificate_header = models.TextField(_("Certificate header"), blank=True, null=True)
    certificate_footer = models.TextField(_("Certificate footer"), blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)
    with_convention = models.BooleanField(_("Has a convention"), default=True)
    uses_student_federation = models.BooleanField(_("Uses EduConnect student federation"), default=False)
    uses_agent_federation = models.BooleanField(_("Uses agent identity federation"), default=False)

    allow_individual_immersions = models.BooleanField(
        _("Allow individual immersions"),
        help_text=_("If unchecked, allow only group immersions by the school manager"),
        default=True
    )

    uai_codes = models.ManyToManyField(UAI, verbose_name=_("UAI Code"), blank=True, related_name='highschools')

    objects = models.Manager()  # default manager
    agreed = HighSchoolAgreedManager()  # returns only agreed Highschools
    immersions_proposal = PostBacImmersionManager()

    def __str__(self):
        city = self.city or "(" + gettext("No city") + ")"
        return f"{city} - {self.label}"

    class Meta:
        verbose_name = _('High school / Secondary school')
        verbose_name_plural = _('High schools / Secondary schools')
        constraints = [
            models.UniqueConstraint(
                fields=['label', 'city'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_highschool'
            ),
        ]
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
        'CONS-STR': 'structure_consultant',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, name in self._groups.items():
            # setattr(self, 'is_%s' % name, partial(self.has_groups, code, negated=False))
            setattr(self, 'is_%s' % name, partial(lambda x:self.groups.filter(name__in=[x]).exists(), code))

        for code, name in self._groups.items():
            setattr(self, 'is_only_%s' % name, partial(self.has_single_group, code))

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
        related_name="users",
    )

    destruction_date = models.DateField(_("Account destruction date"), blank=True, null=True)
    validation_string = models.TextField(_("Account validation string"), blank=True, null=True, unique=True)
    recovery_string = models.TextField(_("Account password recovery string"), blank=True, null=True, unique=True)
    email = models.EmailField(_("Email"), blank=False, null=False, unique=True)
    creation_email_sent = models.BooleanField(_("Creation email sent"), blank=True, null=True, default=False)

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

    def has_single_group(self, group):
        """
        :param group: group name to check
        :return: True if User belongs to (and only) group, else False
        """
        return all([
            self.groups.filter(name=group).exists(),
            self.groups.count() == 1
        ])

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

    def is_local_account(self) -> bool:
        """
        Determine is
        :return:
        """
        if self.is_superuser:
            return False
        if (self.is_visitor() or self.is_high_school_student() or self.is_high_school_manager())\
            and not self.uses_federation():
            return True
        elif self.is_speaker() and self.highschool:
            return True
        elif self.is_structure_manager() or self.is_establishment_manager() \
            or self.is_legal_department_staff() or self.is_speaker() or self.is_structure_consultant():
            if self.establishment is not None and self.establishment.data_source_plugin is None:
                return True
        return False

    def authorized_groups(self):
        # user_filter = {} if self.is_superuser else {'user__id': self.pk}
        user_filter = {'user__id': self.pk}
        return Group.objects.filter(**user_filter)

    def send_message(self, request, template_code, copies=None, recipient='user', **kwargs):
        """
        Get a MailTemplate by its code, replace variables and send
        :param message_code: Code of message to send
        :return: True if message sent else False
        """
        try:
            template = MailTemplate.objects.get(code=template_code, active=True)
            logger.debug("Template found : %s" % template)
        except MailTemplate.DoesNotExist:
            msg = gettext("Email not sent : template %s not found or inactive" % template_code)
            logger.error(msg)
            return msg

        # Multiple recipients ?
        other_recipients = copies if copies and isinstance(copies, list) else []

        try:
            message_body = template.parse_vars(user=self, request=request, recipient=recipient, **kwargs)
            from immersionlyceens.libs.mails.variables_parser import Parser
            logger.debug("Message body : %s" % message_body)
            send_email(self.email, template.subject, message_body, copies=other_recipients)
        except Exception as e:
            logger.exception(e)
            msg = gettext("Couldn't send email : %s" % e)
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

    def get_login_page(self):
        redirect_url: str = "/immersion/login"
        if self.is_visitor():
            redirect_url = "/immersion/login/vis"
        elif self.is_high_school_student():
            redirect_url = "/immersion/login"
        elif self.is_high_school_manager():
            redirect_url = "/immersion/login/ref-lyc"
        elif self.is_speaker() and self.highschool is not None:
            redirect_url = "/immersion/login/speaker"
        elif self.is_speaker() or self.is_establishment_manager() or self.is_structure_manager() \
             or self.is_structure_consultant() or self.is_legal_department_staff():
            if self.establishment is not None and self.establishment.data_source_plugin is None:
                redirect_url = "/immersion/login/speaker"
        return redirect_url

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

    def get_student_establishment(self):
        """
        Match student record establishment with core Establishment class
        :return: Establishment object if found, else None
        """
        record = self.get_student_record()

        if record and record.uai_code:
            try:
                return Establishment.objects.get(uai_reference=record.uai_code)
            except Establishment.DoesNotExist:
                pass

        return None

    def get_high_school(self):
        """
        Get pupil high school
        :return: High school object if found, else None
        """
        record = self.get_high_school_student_record()
        return record.highschool if record else None

    def get_high_school_or_student_establishment(self):
        if self.is_visitor():
            return _('Visitor')
        else:
            return self.get_high_school() or self.get_student_establishment()

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
        if self.is_structure_manager() or self.is_structure_consultant:
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
        Returns a dictionary with remaining registrations count for each period
        If the current user is not a student, return 0 for each period

        It does NOT check the training quota per period
        """
        from immersionlyceens.apps.immersion.models import (
            HighSchoolStudentRecordQuota, StudentRecordQuota,
            VisitorRecordQuota,
        )

        record = None
        remaining = { period.pk: 0 for period in Period.objects.all() }

        # Not a student or no record yet : no registration
        if self.is_high_school_student():
            record = self.get_high_school_student_record()
        elif self.is_student():
            record = self.get_student_record()
        elif self.is_visitor():
            record = self.get_visitor_record()

        if not record or not record.is_valid():
            return remaining

        for period in Period.objects.all():
            registrations = self.immersions.filter(
                slot__date__gte=period.immersion_start_date,
                slot__date__lte=period.immersion_end_date,
                cancellation_type__isnull=True,
                slot__event__isnull=True,
            ).count()

            # Default period quota or student record quota
            # FIXME : what if custom_quota.allowed_immersions < period.allowed_immersions ?
            try:
                custom_quota = record.quota.get(period=period)
                allowed_immersions = custom_quota.allowed_immersions
            except (HighSchoolStudentRecordQuota.DoesNotExist, StudentRecordQuota.DoesNotExist,
                    VisitorRecordQuota.DoesNotExist) as e:
                logger.debug("%s : record not found" % self)
                allowed_immersions = period.allowed_immersions

            remaining[period.pk] = allowed_immersions - registrations

        return remaining

    def set_increment_registrations_(self, period):
        from immersionlyceens.apps.immersion.models import (
            HighSchoolStudentRecordQuota, StudentRecordQuota,
            VisitorRecordQuota,
        )
        """
        Updates student remaining registrations based on period
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

        try:
            quota = record.quota.get(period=period)
            quota.allowed_immersions += 1
            quota.save()
        except (HighSchoolStudentRecordQuota.DoesNotExist, StudentRecordQuota.DoesNotExist,
                VisitorRecordQuota.DoesNotExist) as e:
            # Not found : something to do ?
            pass

        return


    def can_register_slot(self, slot=None):
        """
        Slot registration check : validate only User vs Slot restrictions here,
        - NOT slot registration delay
        - NOT registrations quotas
        """
        errors = []

        slot_has_restrictions = any([
            slot.establishments_restrictions,
            slot.levels_restrictions,
            slot.bachelors_restrictions
        ])

        # Returns True if no restrictions are found
        if not slot or not slot_has_restrictions:
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

            bachelor_restrictions = [
                slot.allowed_bachelor_types.exists() and record.bachelor_type in slot.allowed_bachelor_types.all(),
                any([
                    not record.bachelor_type or not any([
                        record.bachelor_type.professional,
                        record.bachelor_type.general,
                        record.bachelor_type.technological
                    ]),
                    record.bachelor_type and record.bachelor_type.professional,
                    slot.allowed_bachelor_types.filter(technological=True).exists()
                    and (not slot.allowed_bachelor_mentions.exists() or
                         record.technological_bachelor_mention in slot.allowed_bachelor_mentions.all()),
                    slot.allowed_bachelor_types.filter(general=True).exists()
                    and (not slot.allowed_bachelor_teachings.exists() or
                         slot.allowed_bachelor_teachings.all().intersection(
                             record.general_bachelor_teachings.all()).exists())
                ])
            ]

            if slot.establishments_restrictions and not all(high_school_conditions):
                errors.append(_('High schools restrictions in effect'))
            if slot.levels_restrictions and not any(levels_conditions):
                errors.append(_('High school or post bachelor levels restrictions in effect'))
            if slot.bachelors_restrictions and not all(bachelor_restrictions):
                errors.append(_('Bachelors restrictions in effect'))

            if errors:
                return False, errors

        if self.is_student():
            establishment = self.get_student_establishment()
            record = self.get_student_record()

            if not record:
                errors.append(_("Student record not found"))
                return False, errors

            # record.home_institution()[0] in slot.allowed_establishments.values_list('label', flat=True)
            establishment_conditions = [
                slot.allowed_establishments.exists(),
                establishment and establishment in slot.allowed_establishments.all()
            ]

            levels_conditions = [
                slot.allowed_student_levels.exists(),
                record.level in slot.allowed_student_levels.all()
            ]

            if slot.establishments_restrictions and not all(establishment_conditions):
                errors.append(_('Establishments restrictions in effect'))

            if slot.levels_restrictions and not all(levels_conditions):
                errors.append(_('Student levels restrictions in effect'))

            if slot.bachelors_restrictions:
                errors.append(_('Bachelors restrictions in effect'))

            if errors:
                return False, errors

        # Restrictions checks for visitors
        if self.is_visitor():
            record = self.get_visitor_record()

            if not record or not record.is_valid():
                errors.append(_("Visitor record not found or not valid"))

            # visitors can register to "open to all" slots
            if any([slot.levels_restrictions, slot.establishments_restrictions, slot.bachelors_restrictions]):
                errors.append(_('Slot restrictions in effect'))

            if errors:
                return False, errors

        return True, errors


    def linked_users(self):
        """
        :return: a list of users linked to self (including self)
        Returns only [self] if there's no linked user
        """
        if not self.usergroup.exists():
            return [self]

        return [user for group in self.usergroup.all() for user in group.immersionusers.all()]


    def accept_to_share_immersions(self):
        """
        Get high school student decision to share his immersions data with his high school
        :return: boolean (student choice) if found, else True
        """
        try:
            request_agreement = GeneralSettings.get_setting("REQUEST_FOR_STUDENT_AGREEMENT")
        except:
            request_agreement = False

        # Setting disabled : return True
        if not request_agreement:
            return True

        record = self.get_high_school_student_record()
        return record.allow_high_school_consultation if record else True


    def has_obsolete_attestations(self):
        today = timezone.localdate()
        record = self.get_high_school_student_record() or self.get_visitor_record()

        if not record:
            return False

        return record.attestation.filter(
            mandatory=True,
            archive=False,
            requires_validity_date=True,
            validity_date__lt=today
        ).exists()

    def uses_federation(self):
        """
        For high school students, high school managers and speakers,
        if federations are enabled, check if the user has to use
        a federation to authenticate
        :return: boolean
        """

        if not any([self.is_high_school_manager(), self.is_speaker(), self.is_high_school_student()]):
            return False

        student_federation_enabled = get_general_setting('ACTIVATE_EDUCONNECT')
        agent_federation_enabled = get_general_setting('ACTIVATE_FEDERATION_AGENT')

        if (self.is_high_school_manager() or self.is_speaker()) and agent_federation_enabled:
            return self.highschool and self.highschool.uses_agent_federation

        if self.is_high_school_student() and student_federation_enabled:
            return (hasattr(self, 'high_school_student_record')
                    and self.high_school_student_record.highschool
                    and self.high_school_student_record.highschool.uses_student_federation)

        return False


    class Meta:
        verbose_name = _('User')
        ordering = ['last_name', 'first_name', ]


class ImmersionUserGroup(models.Model):
    """
    Accounts fusion
    """
    immersionusers = models.ManyToManyField(
        ImmersionUser, verbose_name=_("Group members"), related_name='usergroup',
    )

    def __str__(self):
        return f"{self._meta.verbose_name}: {', '.join(self.immersionusers.values_list('email', flat=True))}"

    class Meta:
        verbose_name = _('User group')
        verbose_name_plural = _('User groups')
        ordering = ['pk', ]


class PendingUserGroup(models.Model):
    """
    Accounts links waiting to be confirmed
    """
    creation_date = models.DateTimeField(_("Date"), auto_now_add=True)

    immersionuser1 = models.ForeignKey(
        ImmersionUser, verbose_name=_("User") + " 1", on_delete=models.CASCADE, blank=False, null=False, related_name="+"
    )

    immersionuser2 = models.ForeignKey(
        ImmersionUser, verbose_name=_("User") + " 2", on_delete=models.CASCADE, blank=False, null=False, related_name="+"
    )

    validation_string = models.TextField(_("Accounts link validation string"), blank=False, null=False, unique=True)


    def set_validation_string(self):
        """
        Generates and return a new validation string
        """
        self.validation_string = uuid.uuid4().hex
        self.save()
        return self.validation_string


    class Meta:
        verbose_name = _('Pending accounts link')
        verbose_name_plural = _('Pending accounts link')
        ordering = ['pk', ]


class Profile(models.Model):
    """
    User profiles
    Has to be more precise than just groups
    """
    code = models.CharField(_("Code"), max_length=20, unique=True)
    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    def __str__(self):
        return f"{self.code} : {self.label}"

    class Meta:
        verbose_name = _('User profile')
        verbose_name_plural = _('User profiles')
        ordering = ['label', ]


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

    def count_subdomain_slots(self):
        today = datetime.datetime.today()
        slots_count = Slot.objects.filter(
            course__training__training_subdomains=self,
            published=True,
            event__isnull=True,
            allow_group_registrations=False
        ).prefetch_related('course__training__training_subdomains__training_domain') \
        .filter(
            Q(date__isnull=True)
            | Q(date__gte=today.date())
            | Q(date=today.date(), end_time__gte=today.time())
        ).count()

        return slots_count

    def count_group_public_subdomain_slots(self):
        today = datetime.datetime.today()
        slots_count = (
            Slot.objects.filter(
                course__training__training_subdomains=self,
                published=True,
                event__isnull=True,
                allow_group_registrations=True,
                public_group=True
            )
            .prefetch_related('course__training__training_subdomains__training_domain')
            .filter(Q(date__isnull=True) | Q(date__gte=today.date()) | Q(date=today.date(), end_time__gte=today.time()))
            .count()
        )

        return slots_count

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
    url = models.URLField(_("Website address"), max_length=1024, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    highschool = models.ForeignKey(HighSchool, verbose_name=_("High school"), blank=True, null=True,
        on_delete=models.SET_NULL, related_name='trainings'
    )

    allowed_immersions = models.PositiveIntegerField(
        _('Allowed immersions per student, per period'), null=True, blank=True
    )

    def __str__(self):
        return self.label

    def is_highschool(self) -> bool:
        """Return True if highschool is set"""
        return self.highschool is not None

    def is_structure(self) -> bool:
        """Return True if structure is set"""
        return self.structures is not None and self.structures.count() > 0

    """
    def can_delete(self):
        return not self.courses.all().exists()
    """

    def distinct_establishments(self):
        return Establishment.objects.filter(structures__in=self.structures.all()).distinct()


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()

            # Advanced test
            if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
                excludes = {}

                if self.pk:
                    excludes = {'id': self.pk}

                qs = Training.objects.filter(
                       structures__isnull=True,
                       highschool__id=self.highschool_id,
                       label__unaccent__iexact=self.label
                ).exclude(**excludes)

                if qs.exists():
                    raise ValidationError(
                        _("A Training object with the same high school and label already exists")
                    )

        except ValidationError as e:
            raise

    class Meta:
        verbose_name = _('Training')
        verbose_name_plural = _('Trainings')
        constraints = [
            models.UniqueConstraint(
                fields=['highschool', 'label'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_highschool_training'
            ),
        ]
        ordering = ['label', ]


class Campus(models.Model):
    """
    Campus class
    """

    label = models.CharField(_("Label"), max_length=255)
    active = models.BooleanField(_("Active"), default=True)
    department = models.CharField(_("Department"), max_length=128, blank=False, null=False)
    city = UpperCharField(_("City"), max_length=255, blank=False, null=False)
    zip_code = models.CharField(_("Zip code"), max_length=128, blank=False, null=False)
    establishment = models.ForeignKey(Establishment, verbose_name=_("Establishment"), on_delete=models.SET_NULL,
        blank=False, null=True)

    def __str__(self):
        campus_str = self.label

        if self.city:
            campus_str += f" ({self.city.title()})"

        return campus_str

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()

            # Advanced test
            if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
                excludes = {}

                if self.pk:
                    excludes = {'id': self.pk}

                qs = Campus.objects.filter(
                       establishment__id=self.establishment.id,
                       label__unaccent__iexact=self.label
                ).exclude(**excludes)

                if qs.exists():
                    raise ValidationError(
                        _("A Campus object with the same establishment and label already exists")
                    )

        except ValidationError as e:
            raise

    class Meta:
        verbose_name = _('Campus')
        verbose_name_plural = _('Campus')
        constraints = [
            models.UniqueConstraint(
                fields=['label', 'establishment'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_campus'
            ),
        ]
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


class BachelorType(models.Model):
    """
    Bachelor type
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    pre_bachelor_level = models.BooleanField(_("Is pre-bachelor level"), default=False)
    general = models.BooleanField(_("Is general type"), default=False)
    technological = models.BooleanField(_("Is technological type"), default=False)
    professional = models.BooleanField(_("Is professional type"), default=False)

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A bachelor type with this label already exists'))

    class Meta:
        """Meta class"""
        verbose_name = _('Bachelor type')
        verbose_name_plural = _('Bachelor types')
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
        constraints = [
            models.UniqueConstraint(
                fields=['label', 'campus'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_building'
            ),
        ]
        ordering = ['label', ]


class CancelType(models.Model):
    """
    Cancel type
    """

    code = models.CharField(_("Code"), max_length=8, null=True, blank=True, unique=True)
    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    system = models.BooleanField(_("Reserved for System"), default=False)
    managers = models.BooleanField(_("Reserved for Managers"), default=False)

    students = models.BooleanField(_("Usable for individual registrations"), default=True)
    groups = models.BooleanField(_("Usable for groups registrations"), default=False)

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A cancel type with this label already exists'))

    def usable_for_students(self):
        """
        Type can be used for a single student registration
        """
        return self.active and self.students

    def usable_for_groups(self):
        """
        Type can be used for a group registration
        """
        return self.active and self.groups

    def usable_by_student(self):
        """
        Type can be selected by a student
        """
        return self.active and not self.managers

    def usable_by_manager(self):
        """
        Type can be selected by a manager
        """
        return self.active and not self.system

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
        verbose_name_plural = _('Course types')
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

    @classmethod
    def get_active(cls):
        try:
            return UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            return None
        except UniversityYear.MultipleObjectsReturned as e:
            raise Exception(_("Error : multiple active university years")) from e

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
        return self.start_date <= _date <= self.end_date


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


class Period(models.Model):
    """
    Period class. Replaces the semesters
    """
    REGISTRATION_END_DATE_PERIOD = 0
    REGISTRATION_END_DATE_SLOT = 1

    REGISTRATION_END_DATE_CHOICES = [
        (REGISTRATION_END_DATE_PERIOD, _("Use this period settings")),
        (REGISTRATION_END_DATE_SLOT, _("Use slots settings"))
    ]

    label = models.CharField(_("Label"), max_length=256, unique=True, null=False, blank=False)
    registration_start_date = models.DateTimeField(
        pgettext("period", "Registration start date"),
        null=False,
        blank=False
    )
    registration_end_date = models.DateTimeField(
        pgettext("period", "Registration end date"),
        null=True,
        blank=True
    )

    registration_end_date_policy = models.SmallIntegerField(
        _("Registration end date and delay policy"),
        null=False,
        blank=False,
        default=REGISTRATION_END_DATE_SLOT,
        choices=REGISTRATION_END_DATE_CHOICES
    )

    immersion_start_date = models.DateField(_("Immersions start date"), null=False, blank=False)
    immersion_end_date = models.DateField(_("Immersions end date"), null=False, blank=False)

    cancellation_limit_delay = models.PositiveSmallIntegerField(
        _('Cancellation limit delay'),
        null=True,
        blank=True,
        default=0,
        help_text=_("Will be relative to each slot of this period")
    )

    allowed_immersions = models.PositiveIntegerField(
        _('Allowed immersions per student'), null=False, blank=False, default=1,
    )

    @classmethod
    def from_date(cls, pk:models.BigAutoField, date:datetime.date):
        """
        :param pk: period primary key.
        :param date: the date.
        :return: the period that matches start_date < date < end_date
        """

        try:
            return Period.objects.get(pk=pk, immersion_start_date__lte=date, immersion_end_date__gte=date)
        except Period.DoesNotExist as e:
            raise

    def __str__(self):
        return _("Period '%(label)s' : %(begin_date)s - %(end_date)s") % {
            'label': self.label,
            'begin_date': date_format(self.immersion_start_date),
            'end_date' :date_format(self.immersion_end_date)
        }

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()

            # Advanced test
            if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
                excludes = {}

                if self.pk:
                    excludes = {'id': self.pk}

                if Period.objects.filter(label__unaccent__iexact=self.label).exclude(**excludes).exists():
                    raise ValidationError(
                        _("A Period object with the same label already exists")
                    )
        except ValidationError as e:
            raise

    def save(self, *args, **kwargs):
        """
        When updating registration_end_date, if registration policy is REGISTRATION_END_DATE_PERIOD,
        update all related slots registration limit date
        """
        current_registration_end_date = None

        if self.pk:
            current_registration_end_date = Period.objects.get(pk=self.pk).registration_end_date

        super().save(*args, **kwargs)

        # registration_end_date updated : update the slots
        if self.registration_end_date_policy == self.REGISTRATION_END_DATE_PERIOD \
           and self.registration_end_date != current_registration_end_date:
            for slot in self.slots.all():
                slot.save()

    class Meta:
        verbose_name = _('Period')
        verbose_name_plural = _('Periods')
        ordering = ['immersion_start_date', ]


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
    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='courses', blank=True)
    url = models.URLField(_("Website address"), max_length=1024, blank=True, null=True)

    def __str__(self):
        return self.label

    def get_structures_queryset(self):
        return self.training.structures.all()

    def free_seats(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        :return: number of seats as the sum of seats of all slots under this course
        """
        filters = {'published': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['speakers__in'] = speakers

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']

    def published_slots_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        Return number of published slots under this course
        """
        filters = {'published': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['speakers__in'] = speakers

        return self.slots.filter(**filters).count()

    def is_deletable(self):
        """
        Return True if the course can be deleted
        """
        return not self.slots.exists()

    def managed_by(self):
        if self.structure:
            return f"{self.structure.establishment.code} - {self.structure.code}"
        elif self.highschool:
            return f"{self.highschool.city} - {self.highschool.label}"

    def slots_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        Return number of slots under this course, published or not
        """
        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            return self.slots.filter(speakers__in=speakers).count()
        else:
            return self.slots.all().count()

    def registrations_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        :return: the number of non-cancelled registered students on all the slots
        under this course (past and future)
        """
        filters = {'slot__course': self, 'cancellation_type__isnull': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['slot__speakers__in'] = speakers

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()

    def get_alerts_count(self):
        return UserCourseAlert.objects.filter(course=self, email_sent=False).count()


    def get_etab_or_high_school(self):
        if not self.highschool:
            return self.structure.establishment.label
        else:
            return f'{self.highschool.label} - {self.highschool.city}'


    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()

            # Advanced test
            if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
                excludes = {}

                if self.pk:
                    excludes = {'id': self.pk}

                qs = Course.objects.filter(
                    Q(training__id=self.training_id,
                      structure__id=self.structure_id,
                      highschool__isnull=True,
                      label__unaccent__iexact=self.label)
                    |Q(training__id=self.training_id,
                       structure__isnull=True,
                       highschool__id=self.highschool_id,
                       label__unaccent__iexact=self.label)
                ).exclude(**excludes)

                if qs.exists():
                    raise ValidationError(
                        _("A Course object with the same structure/high school, training and label already exists")
                    )
        except ValidationError as e:
            raise

    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
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

    def free_seats(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        :return: number of seats as the sum of seats of all slots under this event
        """
        filters = {'published': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['speakers__in'] = speakers

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']

    def published_slots_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        Return number of published slots under this event
        """
        filters = {'published': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['speakers__in'] = speakers

        return self.slots.filter(**filters).count()

    def slots_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        Return number of slots under this event, published or not
        """
        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            return self.slots.filter(speakers__in=speakers).count()
        else:
            return self.slots.all().count()

    def registrations_count(self, speakers=None):
        """
        :speakers: optional : only consider slots attached to 'speakers'
        :return: the number of non-cancelled registered students on all the slots
        under this event (past and future)
        """
        filters = {'slot__event': self, 'cancellation_type__isnull': True}

        if speakers:
            if not isinstance(speakers, list):
                speakers = [speakers]

            filters['slot__speakers__in'] = speakers

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()

    def clean(self):
        if [self.establishment, self.highschool].count(None) != 1:
            raise ValidationError("You must select one of : Establishment or High school")

    def get_etab_or_high_school(self):
        if not self.highschool:
            return self.establishment
        else:
            return self.highschool

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()

            # Advanced test
            if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
                excludes = {}
                if self.pk:
                    excludes = {'id': self.pk}

                qs = OffOfferEvent.objects.filter(
                    Q(establishment__id=self.establishment_id,
                      structure__id=self.structure_id,
                      highschool__isnull=True,
                      event_type__id=self.event_type_id,
                      label__unaccent__iexact=self.label)
                    |Q(establishment__isnull=True,
                       structure__isnull=True,
                       highschool__id=self.highschool_id,
                       event_type__id=self.event_type_id,
                       label__unaccent__iexact=self.label)
                ).exclude(**excludes)

                if qs.exists():
                    raise ValidationError(
                        _("An off offer event with the same attachments and label already exists")
                    )
        except ValidationError as e:
            raise

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
            user=user,
            request=request,
            message_body=self.body,
            vars=[v for v in self.available_vars.all()], **kwargs,
        )

    def parse_vars_faker(self, user, request, **kwargs):
        from immersionlyceens.libs.mails.variables_parser import parser_faker
        return parser_faker(
            user=user,
            request=request,
            message_body=self.body,
            available_vars=[v for v in self.available_vars.all()],
            **kwargs,
        )

    def parse_var_faker_from_string(self, user, body, request, context_params, **kwargs):
        from immersionlyceens.libs.mails.variables_parser import parser_faker
        return parser_faker(
            context_params=context_params,
            user=user,
            request=request,
            message_body=body,
            available_vars=[v for v in self.available_vars.all()],
            **kwargs,
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


class AttestationDocument(models.Model):
    """
    AttestationDocument class
    Documents users have to provide on their records
    """
    label = models.CharField(_("Label"), max_length=255, blank=False, null=False, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    order = models.PositiveSmallIntegerField(_("Display order"), blank=False, null=True, unique=True,
        default=partial(get_object_default_order, 'AttestationDocument')
    )
    for_minors = models.BooleanField(_("Attestation reserved for minors"), default=True)
    mandatory = models.BooleanField(_("Mandatory"), default=True)
    requires_validity_date = models.BooleanField(_("Requires a validity date"), default=True)
    template = models.FileField(
        _("Template"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(settings.CONTENT_TYPES),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )

    profiles = models.ManyToManyField(
        Profile,
        verbose_name=_("Profiles"),
        related_name='attestations',
        blank=True,
        limit_choices_to={'code__in': ["LYC_W_CONV", "LYC_WO_CONV", "VIS"]}
    )

    objects = models.Manager() # default manager
    activated = ActiveManager() # manager for active elements only

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An attestation with this label already exists'))

    def delete(self, using=None, keep_parents=False):
        """
        Delete file uploaded from document Filefield if not empty
        """
        if bool(self.template):
            try:
                self.template.storage.delete(self.template.name)
            except Exception as e:
                logger.error(f"Cannot delete {self.template.name} : {e}")

        super().delete()

    class Meta:
        verbose_name = _('Attestation document')
        verbose_name_plural = _('Attestation documents')
        ordering = ['order', ]


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

    # Groups options
    ONE_GROUP = 0
    BY_PLACES = 1

    GROUP_MODES = [
        (ONE_GROUP, _("One group")),
        (BY_PLACES, _("By number of places")),
    ]

    # Place options
    FACE_TO_FACE = 0 # default
    REMOTE = 1
    OUTSIDE = 2 # Outside of host establishment

    PLACES = [
        (FACE_TO_FACE, _("Face to face")),
        (REMOTE, _("Remote")),
        (OUTSIDE, _("Outside of host establishment")),
    ]

    period = models.ForeignKey(
        Period, verbose_name=_("Period"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )

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

    date = models.DateField(_('Date'), blank=True, null=True, validators=[validate_slot_date])
    start_time = models.TimeField(_('Start time'), blank=True, null=True)
    end_time = models.TimeField(_('End time'), blank=True, null=True)

    speakers = models.ManyToManyField(ImmersionUser, verbose_name=_("Speakers"), related_name='slots', blank=True)

    n_places = models.PositiveIntegerField(_('Number of individual places'), null=True, blank=True)
    n_group_places = models.PositiveIntegerField(_('Number of places for groups'), null=True, blank=True)

    additional_information = models.TextField(_('Additional information'), null=True, blank=True)

    url = models.URLField(_("Website address"), max_length=512, blank=True, null=True)

    published = models.BooleanField(_("Published"), default=True, null=False)

    place = models.SmallIntegerField(
        _("Place"),
        default=0,
        choices=PLACES,
        null=False,
        blank=True
    )

    establishments_restrictions = models.BooleanField(
        _("Use establishments restrictions"), default=False, null=False, blank=True
    )

    levels_restrictions = models.BooleanField(
        _("Use levels restrictions"), default=False, null=False, blank=True
    )

    bachelors_restrictions = models.BooleanField(
        _("Use bachelors restrictions"), default=False, null=False, blank=True
    )

    # Allowed establishments / high schools
    allowed_establishments = models.ManyToManyField(
        Establishment, verbose_name=_("Allowed establishments"), related_name='+', blank=True
    )

    allowed_highschools = models.ManyToManyField(
        HighSchool, verbose_name=_("Allowed high schools"), related_name='+', blank=True
    )

    # Allowed levels
    allowed_highschool_levels = models.ManyToManyField(
        HighSchoolLevel, verbose_name=_("Allowed high school levels"), related_name='+', blank=True
    )
    allowed_student_levels = models.ManyToManyField(
        StudentLevel, verbose_name=_("Allowed student levels"), related_name='+', blank=True
    )
    allowed_post_bachelor_levels = models.ManyToManyField(
        PostBachelorLevel, verbose_name=_("Allowed post bachelor levels"), related_name='+', blank=True
    )

    # Allowed bachelor types
    allowed_bachelor_types = models.ManyToManyField(
        BachelorType, verbose_name=_("Allowed bachelor types"), related_name='+', blank=True
    )
    allowed_bachelor_mentions = models.ManyToManyField(
        BachelorMention, verbose_name=_("Allowed bachelor mentions"), related_name='+', blank=True
    )
    allowed_bachelor_teachings = models.ManyToManyField(
        GeneralBachelorTeaching, verbose_name=_("Allowed bachelor teachings"), related_name='+', blank=True
    )

    registration_limit_delay = models.PositiveSmallIntegerField(
        _('Registration limit delay'), null=True, blank=True, default=0
    )
    cancellation_limit_delay = models.PositiveSmallIntegerField(
        _('Cancellation limit delay'), null=True, blank=True, default=0
    )

    registration_limit_date = models.DateTimeField(_('Registration limit'), blank=True, null=True)
    cancellation_limit_date = models.DateTimeField(_('Cancellation limit'), blank=True, null=True)

    reminder_notification_sent = models.BooleanField(
        _("Slot reminder notification sent"), default=False, null=False, blank=True
    )

    allow_individual_registrations = models.BooleanField(
        _("Allow individual registrations"), default=True, null=False, blank=False
    )
    allow_group_registrations = models.BooleanField(
        _("Allow group registrations"), default=False, null=False, blank=False
    )

    group_mode = models.SmallIntegerField(
        _("Group management mode"),
        default=0,
        choices=GROUP_MODES,
        null=True,
        blank=True
    )

    public_group = models.BooleanField(
        _("Public group registrations"),
        default=False,
        null=False,
        blank=False
    )

    def get_establishment(self):
        """
        Get the slot establishment depending on the slot type (course, event)
        """
        if self.course_id and self.course.structure_id:
            return self.course.structure.establishment
        elif self.event_id and self.event.establishment_id:
            return self.event.establishment

        return None

    def get_structure(self):
        """
        Get the slot structure depending on the slot type (course, event)
        """
        if self.course_id and self.course.structure_id:
            return self.course.structure
        elif self.event_id and self.event.structure_id:
            return self.event.structure

        return None

    def get_highschool(self):
        """
        Get the slot high school depending on the slot type (course, event)
        """
        if self.course_id and self.course.highschool_id:
            return self.course.highschool
        elif self.event_id and self.event.highschool_id:
            return self.event.highschool

        return None

    def available_seats(self):
        """
        :return: number of available seats for instance slot
        """
        # TODO: check if we need to filter published slots only ???

        s = int(self.n_places) - Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count() if self.n_places else 0
        return 0 if s < 0 else s

    def registered_students(self):
        """
        :return: number of registered students for instance slot
        """
        # TODO: check if we need to filter published slots only ???
        return Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()

    def registered_groups(self):
        """
        :return: number of registered students for instance slot
        """
        # TODO: check if we need to filter published slots only ???
        return ImmersionGroupRecord.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()

    def registered_groups_people_count(self):
        """
        :return: number of registered students for instance slot
        """
        # TODO: check if we need to filter published slots only ???
        group_queryset = (ImmersionGroupRecord.objects
            .filter(slot=self.pk, cancellation_type__isnull=True)
            .aggregate(
                students=Sum('students_count'),
                guides=Sum('guides_count')
            )
        )

        return {
            'students': group_queryset.get('students', 0) or 0,
            'guides': group_queryset.get('guides', 0) or 0
        }

    def clean(self):
        if [self.course, self.event].count(None) != 1:
            raise ValidationError("You must select one of : Course or Event")

    def __str__(self):
        date = _("date unknown")
        start_time = _("start time unknown")
        end_time = _("end time unknown")
        slot_type = _("No type yet")

        if self.date:
            date = date_format(self.date, format='l d F Y', use_l10n=True)

        if self.start_time:
            start_time = self.start_time.isoformat(timespec='minutes')

        if self.end_time:
            end_time = self.end_time.isoformat(timespec='minutes')

        if self.course:
            slot_type = _("Course - %(type)s %(label)s") % {
                'type': self.course_type,
                'label': self.course.label
            }
        elif self.event:
            slot_type = _("Event - %s") % self.event.label

        return f"{slot_type} : {date} : {start_time}-{end_time}"


    def get_allowed_highschool_levels(self):
        return [level.label for level in self.allowed_highschool_levels.all()]


    def get_allowed_students_levels(self):
        return [level.label for level in self.allowed_student_levels.all()]


    def get_allowed_post_bachelor_levels(self):
        return [level.label for level in self.allowed_post_bachelor_levels.all()]


    def get_allowed_bachelor_types(self):
        return [type.label for type in self.allowed_bachelor_types.all()]


    def get_allowed_bachelor_mentions(self):
        return [mention.label for mention in self.allowed_bachelor_mentions.all()]


    def get_allowed_bachelor_teachings(self):
        return [teach.label for teach in self.allowed_bachelor_teachings.all()]


    def get_label(self):
        """
        Returns course or event label
        """
        if self.is_course():
            return self.course.label
        if self.is_event():
            return self.event.label

        return _("Unknown")

    def is_course(self):
        """
        Returns True if slot is a course slot else False
        """
        return True if self.course else False

    def is_event(self):
        """
        Returns True if slot is an event slot else False
        """
        return True if self.event else False

    def get_type(self):
        """
        returns:
        'course' if slot is a course slot
        'event' if slot is an event slot
        """
        if self.is_course():
            return 'course'
        if self.is_event():
            return 'event'

    def can_show_url(self):
        # Showing remote course url if today date >= NB_DAYS_SLOT_REMINDER
        today = datetime.datetime.today()
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

        if today.date() < self.date and self.date < (today + datetime.timedelta(days=days)).date():
            return True
        if self.date == today.date() and today.time() < self.end_time:
            return True
        else:
            return False

    def is_registration_limit_date_due(self):
        return self.registration_limit_date < timezone.now()

    def is_cancellation_limit_date_due(self):
        return self.cancellation_limit_date < timezone.now()

    def save(self, *args, **kwargs):
        """
        Parse registration and cancellation dates based on :
          - period registration policy & period registrations end date
          - slot date and delays
        """

        # period is only mandatory when slot is published
        if self.period:
            if self.period.registration_end_date_policy == Period.REGISTRATION_END_DATE_PERIOD:
                # Period date
                self.registration_limit_date = self.period.registration_end_date

                if timezone.is_naive(self.registration_limit_date):
                    self.registration_limit_date = timezone.make_aware(self.registration_limit_date)

                # Cancellation limit date
                if self.date and self.start_time:
                    self.cancellation_limit_date = datetime.datetime.combine(self.date, self.start_time)

                    if timezone.is_naive(self.cancellation_limit_date):
                        self.cancellation_limit_date = timezone.make_aware(self.cancellation_limit_date)

                    if self.period.cancellation_limit_delay and self.period.cancellation_limit_delay > 0:
                        self.cancellation_limit_date -= datetime.timedelta(hours=self.period.cancellation_limit_delay)

            elif self.date and self.start_time:
                # Slot date
                self.registration_limit_date = datetime.datetime.combine(self.date, self.start_time)
                if timezone.is_naive(self.registration_limit_date):
                    self.registration_limit_date = timezone.make_aware(self.registration_limit_date)
                if self.registration_limit_delay and self.registration_limit_delay > 0:
                    self.registration_limit_date -= datetime.timedelta(hours=self.registration_limit_delay)

                # Cancellation limit date
                if self.date and self.start_time:
                    self.cancellation_limit_date = datetime.datetime.combine(self.date, self.start_time)

                    if timezone.is_naive(self.cancellation_limit_date):
                        self.cancellation_limit_date = timezone.make_aware(self.cancellation_limit_date)

                    if self.cancellation_limit_delay and self.cancellation_limit_delay > 0:
                        self.cancellation_limit_date -= datetime.timedelta(hours=self.cancellation_limit_delay)
        else:
            self.registration_limit_date = None
            self.cancellation_limit_date = None

        return super().save(*args, **kwargs)


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
        on_delete=models.PROTECT,
        related_name="immersions",
    )

    attendance_status = models.SmallIntegerField(_("Attendance status"), default=0, choices=ATT_STATUS)
    survey_email_sent = models.BooleanField(_("Survey notification status"), default=False)

    registration_date = models.DateTimeField(_("Registration date"), auto_now_add=True)
    cancellation_date = models.DateTimeField(_("Cancellation date"), null=True, blank=True)

    def get_attendance_status(self) -> str:
        """
        get attendance status
        :return: status
        """
        try:
            return self.ATT_STATUS[self.attendance_status][1]
        except KeyError:
            return ''

    def __str__(self):
        return f"{self.student} - {self.slot}"

    class Meta:
        verbose_name = _('Immersion')
        verbose_name_plural = _('Immersions')


class ImmersionGroupRecord(models.Model):
    """
    Group registration to a slot
    """
    ATT_STATUS = [
        (0, _('Not entered')),
        (1, _('Present')),
        (2, _('Absent')),
    ]

    ALLOWED_TYPES = {
        'pdf': "application/pdf",
        'doc': "application/msword",
        'docx': "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        'odt': "application/vnd.oasis.opendocument.text",
        'xls': "application/vnd.ms-excel",
        'xlsx': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    registration_date = models.DateTimeField(_("Registration date"), auto_now_add=True)
    last_updated = models.DateTimeField(_("Last updated date"), auto_now=True)

    slot = models.ForeignKey(
        Slot,
        verbose_name=_("Slot"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="group_immersions",
    )

    cancellation_date = models.DateTimeField(_("Cancellation date"), null=True, blank=True)

    cancellation_type = models.ForeignKey(
        CancelType,
        verbose_name=_("Cancellation type"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="group_immersions",
    )

    # FIXME: useful ?
    survey_email_sent = models.BooleanField(_("Survey notification status"), default=False)

    highschool = models.ForeignKey(
        HighSchool,
        verbose_name=_("High school"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="group_immersions",
    )

    students_count = models.SmallIntegerField(_("Registered students count"), null=False, blank=False)
    guides_count = models.SmallIntegerField(_("Student guides count"), null=False, blank=False)

    file = models.FileField(
        _("File"),
        upload_to=get_file_path,
        blank=True,
        null=True,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
          % {
              'authorized_types': ', '.join(ALLOWED_TYPES.keys()),
              'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
          },
    )

    attendance_status = models.SmallIntegerField(_("Attendance status"), default=0, choices=ATT_STATUS)
    comments = models.TextField(_('Comments'), blank=True, null=True)
    emails = models.TextField(_('Emails'), blank=True, null=True)

    def __str__(self):
        return f"{self.highschool} - {self.slot}"

    def get_attendance_status(self) -> str:
        """
        get attendance status
        :return: status
        """
        try:
            return self.ATT_STATUS[self.attendance_status][1]
        except KeyError:
            return ''

    def send_message(self, request, template):
        """
        Get group high school referents and contacts,
        then send the message to the first referent and all others in CC
        """
        user = request.user if request else None
        error = False

        high_school_managers = ImmersionUser.objects.filter(groups__name='REF-LYC', highschool_id=self.highschool.id)
        main_manager = user if user and user.is_high_school_manager() else high_school_managers.first()
        contacts = self.emails.split(',')
        recipients = list(
            set(contacts).union(set(hsm.email for hsm in high_school_managers if hsm.email != main_manager.email))
        )

        # Send a confirmation message to highschool managers and all contacts
        ret = main_manager.send_message(request, template, slot=self.slot, recipient='group', copies=recipients)
        if not ret:
            msg = _(
                "Registration successfully added, confirmation email sent to high school managers and contacts")
        else:
            msg = _("Registration successfully added, confirmation email NOT sent : %s") % ret
            error = True

        return msg, error

    class Meta:
        verbose_name = _('Group immersion')
        verbose_name_plural = _('Group immersions')

class GeneralSettings(models.Model):
    """
    Global application settings
    """
    TECHNICAL = 0
    FUNCTIONAL = 1

    TYPES = [
        (TECHNICAL, _('Technical')),
        (FUNCTIONAL, _('Functional')),
    ]

    setting = models.CharField(_("Setting name"), max_length=128, unique=True)
    parameters = models.JSONField(_("Setting configuration"),
        blank=False,
        default=dict,
        validators=[JsonSchemaValidator(join(dirname(__file__), 'schemas', 'general_settings.json'))]
    )
    setting_type = models.SmallIntegerField(_("Setting type"), choices=TYPES, default=0, blank=True, null=True)

    @classmethod
    def get_setting(cls, name:str):
        try:
            return cls.objects.get(setting__iexact=name).parameters["value"]
        except (cls.DoesNotExist, KeyError) as e:
            raise Exception(
                _("General setting '%s' is missing or incorrect. Please check your settings.") % name
            ) from e

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
    course = models.ForeignKey(
        Course, verbose_name=_("Course"), null=False, blank=False, on_delete=models.CASCADE, related_name="alerts",
    )

    class Meta:
        unique_together = ('email', 'course')
        verbose_name = _('Course free slot alert')
        verbose_name_plural = _('Course free slot alerts')
        ordering = ['-alert_date', ]


class AnnualStatistics(models.Model):
    """
    Data kept over years
    """
    year = models.CharField(_("Year label"), primary_key=True, max_length=256, null=False)
    platform_registrations = models.SmallIntegerField(_("Platform registrations count"), default=0)
    one_immersion_registrations = models.SmallIntegerField(
        _("Students registered to at least one course immersion count"), default=0)
    multiple_immersions_registrations = models.SmallIntegerField(
        _("Students registered to more than one course immersion count"), default=0)
    no_course_immersions_registrations = models.SmallIntegerField(
        _("Students without any course immersion registration"), default=0)
    immersion_registrations = models.SmallIntegerField(_("Course immersions registrations count"), default=0)
    immersion_participations = models.SmallIntegerField(_("Course immersions participations count"), default=0)
    immersion_participation_ratio = models.FloatField(_("Course immersions participations ratio"), default=0)
    participants_one_immersion = models.SmallIntegerField(
        _("Participants in at least one immersion count"), default=0)
    participants_multiple_immersions = models.SmallIntegerField(
        _("Participants in multiple immersions count"), default=0)
    structures_count = models.SmallIntegerField(_("Participating structures count"), default=0)
    active_trainings_count = models.SmallIntegerField(_("Active trainings count"), default=0)
    trainings_one_slot_count = models.SmallIntegerField(_("Trainings offering at least one slot count"), default=0)
    active_courses_count = models.SmallIntegerField(_("Active courses count"), default=0)
    courses_one_slot_count = models.SmallIntegerField(_("Courses offering at least one slot count"), default=0)
    total_slots_count = models.SmallIntegerField(_("Total slots count"), default=0)
    seats_count = models.SmallIntegerField(_("Global seats count"), default=0)
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
    ALLOWED_TYPES = {
        'png': "image/png",
        'jpeg': "image/jpeg",
        'jpg': "image/jpeg",
        'gif': "image/gif",
    }

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

    def __str__(self):
        return gettext("Attendance certificate logo")

    # Singleton !
    def save(self, *args, **kwargs):
        self.id = 1
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from logo Filefield"""
        self.logo.storage.delete(self.logo.name)
        super().delete()

    class Meta:
        """Meta class"""
        verbose_name = _('Logo for attendance certificate')
        verbose_name_plural = _('Logo for attendance certificate')


class CertificateSignature(models.Model):
    """
    CertificateSignature class (singleton)
    """

    ALLOWED_TYPES = {
        'png': "image/png",
        'jpeg': "image/jpeg",
        'jpg': "image/jpeg",
        'gif': "image/gif",
    }

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


class CustomThemeFile(models.Model):
    """
    Any file used to pimp immersup theme
    """
    ALLOWED_TYPES = {
        'png': "image/png",
        'jpeg': "image/jpeg",
        'jpg': "image/jpeg",
        'ico': "image/vnd.microsoft.icon",
        'css': "text/css",
        'js': "text/javascript",
    }

    FILE_TYPE = [
        ('JS', _('Js')),
        ('CSS', _('Css')),
        ('IMG', _('Image')),
        ('FAVICON', _('Favicon'))
    ]

    type = models.CharField(_("File type"), max_length=7, choices=FILE_TYPE, default="CSS")
    file = models.FileField(
        _("File"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(['png', 'jpeg', 'jpg', 'ico', 'css', 'js']),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )

    objects = CustomDeleteManager()

    @classmethod
    def object(cls):
        """get only allowed object"""
        return cls._default_manager.all().first()

    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded"""
        self.file.storage.delete(self.file.name)
        super().delete()


    def __str__(self):
        """str"""
        return gettext("file : %(name)s (%(type)s)" % {
            'name': self.file.name,
            'type': self.type
        })

    class Meta:
        """Meta class"""
        verbose_name = _('Custom theme file')
        verbose_name_plural = _('Custom theme files')


class FaqEntry(models.Model):
    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    order = models.PositiveSmallIntegerField(_("Display order"), blank=False, null=True,
        default=partial(get_object_default_order, 'FaqEntry')
    )
    question = models.TextField(_('Question'), max_length=2000, blank=False, null=False)
    answer = models.TextField(_('Answer'), max_length=10000, blank=False, null=False)
    active = models.BooleanField(_("Active"), default=True)
    objects = models.Manager()
    activated = ActiveManager()

    def __str__(self):
        return self.label

    class Meta:
        """Meta class"""
        verbose_name = _('Faq entry')
        verbose_name_plural = _('Faq entries')
        ordering = ['order']


class RefStructuresNotificationsSettings(models.Model):
    user = models.OneToOneField(
        ImmersionUser,
        verbose_name=_('Structure Manager'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="ref_structure_notifications_settings"
    )

    structures = models.ManyToManyField(
        Structure, verbose_name=_("Structures"), related_name='source_structures', blank=True
    )

    def __str__(self):
        return f"{self.user} ({', '.join(self.structures.values_list('label', flat=True))})"


class ScheduledTask(models.Model):
    command_name = models.CharField(_("Django command name"), max_length=128, unique=True)
    description = models.CharField(_("Description"), max_length=256)
    active = models.BooleanField(_("Active"), blank=False, null=False, default=True)
    date = models.DateField(_("Execution Date"), blank=True, null=True)
    time = models.TimeField(_("Execution time"), auto_now=False, auto_now_add=False, blank=False, null=False)
    frequency = models.SmallIntegerField(_("Frequency (in hours)"), blank=True, null=True)
    monday = models.BooleanField(_("Monday"), blank=True, null=False, default=False)
    tuesday = models.BooleanField(_("Tuesday"), blank=True, null=False, default=False)
    wednesday = models.BooleanField(_("Wednesday"), blank=True, null=False, default=False)
    thursday = models.BooleanField(_("Thursday"), blank=True, null=False, default=False)
    friday = models.BooleanField(_("Friday"), blank=True, null=False, default=False)
    saturday = models.BooleanField(_("Saturday"), blank=True, null=False, default=False)
    sunday = models.BooleanField(_("Sunday"), blank=True, null=False, default=False)

    def __str__(self):
        return self.command_name

    class Meta:
        verbose_name = _('Scheduled task')
        verbose_name_plural = _('Scheduled tasks')


class ScheduledTaskLog(models.Model):
    """
    Logs for Scheduled tasks
    """
    task = models.ForeignKey(ScheduledTask, verbose_name=_("Task"), on_delete=models.CASCADE,
        blank=False, null=False, related_name='logs')

    execution_date = models.DateTimeField(_("Date"), auto_now_add=True)
    success = models.BooleanField(_("Success"), blank=True, null=True, default=True)
    message = models.TextField(_('Message'), blank=True, null=True)

    class Meta:
        verbose_name = _('Scheduled task log')
        verbose_name_plural = _('Scheduled task logs')
        ordering = ['-execution_date', ]


class History(models.Model):
    """
    Store various events like account creations or login, logout, failures, ...
    """
    action = models.CharField(_("Action"), max_length=128)
    ip = models.GenericIPAddressField(_("IP"), null=True)
    username = models.CharField(_("Username"), max_length=256, null=True)
    user = models.CharField(_("User"), max_length=256, null=True)
    hijacked = models.CharField(_("Hijacked user"), max_length=256, null=True)
    date = models.DateTimeField(_("Date"), auto_now_add=True)

    def __str__(self):
        identity = ", ".join(list(filter(lambda x:x, [self.username, self.user])))
        return f"{self.date} - {identity} - {self.action}"

    class Meta:
        verbose_name = _('History')
        verbose_name_plural = _('History')

class MefStat(models.Model):
    """
    Mef Stat 4 nomenclature for high school students levels from EduConnect
    """
    code = models.CharField(_("Code"), primary_key=True, null=False, blank=False)
    label = models.CharField(_("Label"), max_length=256, null=False)
    level = models.ForeignKey(
        HighSchoolLevel,
        verbose_name=_("Level"),
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='mefstat'
    )

    def __str__(self):
        return f"{self.code} - {self.label}"

    class Meta:
        verbose_name = _('MefStat - High school level')
        verbose_name_plural = _('MefStat - High school levels')


####### SIGNALS #########
@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')

    History.objects.create(
        action=_("User logged in"),
        ip=ip,
        username=user.username if user else None,
        user=f"{user.last_name} {user.first_name}" if user else None,
    )

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    History.objects.create(
        action=_("User logged out"),
        ip=ip,
        username=user.username if user else None,
        user=f"{user.last_name} {user.first_name}" if user else None,
    )


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, request, **kwargs):
    username = credentials.get('username', None)
    ip = None
    user = None

    try:
        ip = request.META.get('REMOTE_ADDR')
    except AttributeError:
        pass

    if username:
        try:
            user = ImmersionUser.objects.get(username=username.lower().strip())
        except ImmersionUser.DoesNotExist:
            pass

    History.objects.create(
        action=_("User login failed"),
        ip=ip,
        username=username,
        user=f"{user.last_name} {user.first_name}" if user else None,
    )

def user_hijack_start(sender, hijacker, hijacked, request, **kwargs):
    ip = None

    try:
        ip = request.META.get('REMOTE_ADDR')
    except AttributeError:
        pass

    History.objects.create(
        action=_("Hijack start"),
        ip=ip,
        username=hijacker.username if hijacker else None,
        user=f"{hijacker.last_name} {hijacker.first_name}" if hijacker else None,
        hijacked=hijacked
    )

def user_hijack_end(sender, hijacker, hijacked, request, **kwargs):
    ip = None

    try:
        ip = request.META.get('REMOTE_ADDR')
    except AttributeError:
        pass

    History.objects.create(
        action=_("Hijack end"),
        ip=ip,
        username=hijacker.username if hijacker else None,
        user=f"{hijacker.last_name} {hijacker.first_name}" if hijacker else None,
        hijacked=hijacked
    )

hijack_started.connect(user_hijack_start)
hijack_ended.connect(user_hijack_end)
