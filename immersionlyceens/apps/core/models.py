import datetime
import enum
import logging
import re
import uuid
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.template.defaultfilters import date as _date
from django.utils.translation import pgettext, ugettext_lazy as _

from immersionlyceens.fields import UpperCharField
from immersionlyceens.libs.geoapi.utils import get_cities, get_departments
from immersionlyceens.libs.mails.utils import send_email

from .managers import ActiveManager, ComponentQuerySet, CustomDeleteManager, HighSchoolAgreedManager

logger = logging.getLogger(__name__)


class Component(models.Model):
    """
    Component class
    """

    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=128)
    mailing_list = models.EmailField(_('Mailing list address'), blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    objects = models.Manager()  # default manager
    activated = ActiveManager.from_queryset(ComponentQuerySet)()  # returns only activated structures

    class Meta:
        verbose_name = _('Structure')
        verbose_name_plural = _('Structures')

    def __str__(self):
        return "%s : %s" % (self.code, self.label)

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A structure with this code already exists'))


class HighSchool(models.Model):
    """
    HighSchool class
    """

    class Meta:
        verbose_name = _('High school')
        unique_together = ('label', 'city')

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

    def __str__(self):
        return "%s - %s" % (self.city, self.label)


class ImmersionUser(AbstractUser):
    """
    Main user class
    """

    _user_filters = [
        lambda has_group, su: has_group or su,
        lambda has_group, su: has_group and not su,
    ]
    _groups = {
        'REF-ETAB': 'ref_etab_manager',
        'REF-STR': 'structure_manager',
        'REF-LYC': 'high_school_manager',
        'ETU': 'student',
        'LYC': 'high_school_student',
        'ENS-CH': 'teacher',
        'SRV-JUR': 'legal_department_staff',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, name in self._groups.items():
            setattr(self, 'is_%s' % name, partial(self.has_groups, code, negated=False))

    components = models.ManyToManyField(Component, verbose_name=_("Structures"), blank=True, related_name='referents')
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

    def __str__(self):
        return "%s %s" % (self.last_name or _('(no last name)'), self.first_name or _('(no first name)'))

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
        if self.is_superuser or self.has_groups('REF-STR', 'REF-ETAB'):
            return True

        try:
            course = Course.objects.get(pk=course_id)
            course_structures = course.training.components.all()

            if course_structures & self.components.all():
                return True

        except Course.DoesNotExist:
            return False

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
            logger.debug("Message body : %s" % message_body)
            send_email(self.email, template.subject, message_body)
        except Exception as e:
            logger.exception(e)
            msg = _("Error while sending mail : %s" % e)
            return msg

        return None

    def validate_account(self):
        self.validation_string = None
        self.destruction_date = None
        self.save()

    def get_localized_destruction_date(self):
        return _date(self.destruction_date, "l j F Y")

    def get_cleaned_username(self):
        return self.get_username().replace(settings.USERNAME_PREFIX, '')

    def get_login_page(self):
        if self.is_high_school_manager and self.highschool:
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

        if not record or not record.is_valid():
            return remaining

        if calendar.calendar_mode == 'SEMESTER':
            current_semester_1_regs = self.immersions.filter(
                slot__date__gte=calendar.semester1_start_date,
                slot__date__lte=calendar.semester1_end_date,
                cancellation_type__isnull=True,
            ).count()
            current_semester_2_regs = self.immersions.filter(
                slot__date__gte=calendar.semester2_start_date,
                slot__date__lte=calendar.semester2_end_date,
                cancellation_type__isnull=True,
            ).count()
        else:
            current_year_regs = self.immersions.filter(
                slot__date__gte=calendar.year_start_date,
                slot__date__lte=calendar.year_end_date,
                cancellation_type__isnull=True,
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

        if self.is_high_school_student():
            record = self.get_high_school_student_record()
        elif self.is_student():
            record = self.get_student_record()

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

    class Meta:
        verbose_name = _('User')


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
            raise ValidationError(_('A training domain with this label already exists'))


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

    class Meta:
        verbose_name = _('Training sub domain')
        verbose_name_plural = _('Training sub domains')

    def __str__(self):
        domain = self.training_domain or _("No domain")
        return "%s - %s" % (domain, self.label)

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A training sub domain with this label already exists'))


class Training(models.Model):
    """
    Training class
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    training_subdomains = models.ManyToManyField(
        TrainingSubdomain, verbose_name=_("Training subdomains"), blank=False, related_name='Trainings',
    )
    components = models.ManyToManyField(Component, verbose_name=_("Structures"), blank=False, related_name='Trainings')
    url = models.URLField(_("Website address"), max_length=256, blank=True, null=True)
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
            raise ValidationError(_('A training with this label already exists'))


class Campus(models.Model):
    """
    Campus class
    """

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
            raise ValidationError(_('A campus with this label already exists'))


class BachelorMention(models.Model):
    """
    Bachelor degree mentions
    """

    label = models.CharField(_("Label"), max_length=128, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""

        verbose_name = _('Technological bachelor series')
        verbose_name_plural = pgettext('tbs_plural', 'Technological bachelor series')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super(BachelorMention, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A bachelor mention with this label already exists'))


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

    class Meta:
        verbose_name = _('Building')
        unique_together = ('campus', 'label')

    def __str__(self):
        return self.label

    def validate_unique(self, exclude=None):
        try:
            super(Building, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A building with this label for the same campus already exists'))


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
            raise ValidationError(_('A cancel type with this label already exists'))


class CourseType(models.Model):
    """
    Course type
    """

    label = models.CharField(_("Short label"), max_length=256, unique=True)
    full_label = models.CharField(_("Full label"), max_length=256, unique=True, null=False, blank=False)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""

        verbose_name = _('Course type')
        verbose_name_plural = _('Course type')

    def __str__(self):
        """str"""  # from .utils import get_cities, get_departments
        return "%s (%s)" % (self.full_label, self.label)

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(CourseType, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A course type with this label already exists'))


class GeneralBachelorTeaching(models.Model):
    """
    General bachelor specialty teaching
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""

        verbose_name = _('General bachelor specialty teaching')
        verbose_name_plural = _('General bachelor specialties teachings')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A specialty teaching with this label already exists'))


class PublicType(models.Model):
    """
    Public type
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    objects = models.Manager()  # default manager
    activated = ActiveManager()

    class Meta:
        """Meta class"""

        verbose_name = _('Public type')
        verbose_name_plural = _('Public types')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(PublicType, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A public type with this label already exists'))


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

    class Meta:
        """Meta class"""

        verbose_name = _('University year')
        verbose_name_plural = _('University years')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(UniversityYear, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A university year with this label already exists'))

    def save(self, *args, **kwargs):
        if not UniversityYear.objects.filter(active=True).exists():
            self.active = True

        super(UniversityYear, self).save(*args, **kwargs)

    def date_is_between(self, _date):
        return self.start_date <= _date <= self.end_date


class Holiday(models.Model):
    """
    Holidays
    """
    label = models.CharField(_("Label"), max_length=256, unique=True)
    date = models.DateField(_("Date"))

    class Meta:
        """Meta class"""
        verbose_name = _('Holiday')
        verbose_name_plural = _('Holidays')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(Holiday, self).validate_unique()
        except ValidationError as e:
            raise ValidationError(_('A holiday with this label already exists'))

    @classmethod
    def date_is_a_holiday(cls, _date):
        return Holiday.objects.filter(date=_date).exists()


class Vacation(models.Model):
    """
    Vacations
    """

    label = models.CharField(_("Label"), max_length=256, unique=True)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))

    class Meta:
        """Meta class"""

        verbose_name = _('Vacation')
        verbose_name_plural = _('Vacations')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(Vacation, self).validate_unique()
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

    class Meta:
        """Meta class"""

        verbose_name = _('Calendar')
        verbose_name_plural = _('Calendars')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(Calendar, self).validate_unique()
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


class Course(models.Model):
    """
    Course class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)

    training = models.ForeignKey(
        Training, verbose_name=_("Training"), null=False, blank=False, on_delete=models.CASCADE, related_name="courses",
    )

    component = models.ForeignKey(
        Component,
        verbose_name=_("Structure"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    published = models.BooleanField(_("Published"), default=True)

    teachers = models.ManyToManyField(ImmersionUser, verbose_name=_("Teachers"), related_name='courses')

    url = models.URLField(_("Website address"), max_length=1024, blank=True, null=True)

    def __str__(self):
        return self.label

    def get_components_queryset(self):
        return self.training.components.all()

    def free_seats(self, teacher_id=None):
        """
        :teacher_id: optional : only consider slots attached to 'teacher'
        :return: number of seats as the sum of seats of all slots under this course
        """
        filters = {'published': True}

        if teacher_id:
            filters['teachers'] = teacher_id

        d = self.slots.filter(**filters).aggregate(total_seats=Coalesce(Sum('n_places'), 0))

        return d['total_seats']

    def published_slots_count(self, teacher_id=None):
        """
        :teacher_id: optional : only consider slots attached to 'teacher'
        Return number of published slots under this course
        """
        filters = {'published': True}

        if teacher_id:
            filters['teachers'] = teacher_id

        return self.slots.filter(**filters).count()

    def slots_count(self, teacher_id=None):
        """
        :teacher_id: optional : only consider slots attached to 'teacher'
        Return number of slots under this course, published or not
        """
        if teacher_id:
            return self.slots.filter(teachers=teacher_id).count()
        else:
            return self.slots.all().count()

    def registrations_count(self, teacher_id=None):
        """
        :teacher_id: optional : only consider slots attached to 'teacher'
        :return: the number of non-cancelled registered students on all the slots
        under this course (past and future)
        """
        filters = {'slot__course': self, 'cancellation_type__isnull': True}

        if teacher_id:
            filters['slot__teachers'] = teacher_id

        return Immersion.objects.prefetch_related('slot').filter(**filters).count()

    def get_alerts_count(self):
        return UserCourseAlert.objects.filter(course=self, email_sent=False).count()

    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        unique_together = ('training', 'label')


class MailTemplateVars(models.Model):
    code = models.CharField(_("Code"), max_length=64, blank=False, null=False, unique=True)
    description = models.CharField(_("Description"), max_length=128, blank=False, null=False, unique=True)

    def __str__(self):
        return "%s : %s" % (self.code, self.description)

    class Meta:
        verbose_name = _('Template variable')
        verbose_name_plural = _('Template variables')


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
        MailTemplateVars, related_name='mail_templates', verbose_name=_("Available variables"), blank=False,
    )

    def __str__(self):
        return "%s : %s" % (self.code, self.label)

    def parse_vars(self, user, request, **kwargs):
        # Import parser here because it depends on core models
        from immersionlyceens.libs.mails.variables_parser import parser

        return parser(
            user=user, request=request, message_body=self.body, vars=[v for v in self.available_vars.all()], **kwargs,
        )

    class Meta:
        verbose_name = _('Mail template')
        verbose_name_plural = _('Mail templates')


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
        upload_to='uploads/accompanyingdocs/%Y',
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)')
        % {'authorized_types': ','.join(settings.CONTENT_TYPES)},
    )

    class Meta:
        """Meta class"""

        verbose_name = _('Accompanying document')
        verbose_name_plural = _('Accompanying documents')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(AccompanyingDocument, self).validate_unique()
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


class PublicDocument(models.Model):
    """
    PublicDocument class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False, unique=True)
    active = models.BooleanField(_("Active"), default=True)
    document = models.FileField(
        _("Document"),
        upload_to='uploads/publicdocs/%Y',
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)')
        % {'authorized_types': ','.join(settings.CONTENT_TYPES)},
    )
    published = models.BooleanField(_("Published"), default=False)

    objects = CustomDeleteManager()

    class Meta:
        """Meta class"""

        verbose_name = _('Public document')
        verbose_name_plural = _('Public documents')

    def __str__(self):
        """str"""
        return self.label

    def validate_unique(self, exclude=None):
        """Validate unique"""
        try:
            super(PublicDocument, self).validate_unique()
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


class EvaluationType(models.Model):
    """
    Evaluation type class
    """

    code = models.CharField(_("Code"), max_length=30, unique=True)
    label = models.CharField(_("Label"), max_length=128)

    class Meta:
        """Meta class"""

        verbose_name = _('Evaluation type')
        verbose_name_plural = _('Evaluation types')

    def __str__(self):
        """str"""
        return f'{self.code} : {self.label}'

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An evaluation type with this code already exists'))


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

    class Meta:
        """Meta class"""

        verbose_name = _('Evaluation form link')
        verbose_name_plural = _('Evaluation forms links')

    def __str__(self):
        """str"""
        return f'{self.evaluation_type.label} : {self.url}'

    def validate_unique(self, exclude=None):
        try:
            super().validate_unique()
        except ValidationError as e:
            raise ValidationError(_('An evaluation form link with this evaluation type already exists'))


class Slot(models.Model):
    """
    Slot class
    """

    course = models.ForeignKey(
        Course, verbose_name=_("Course"), null=False, blank=False, on_delete=models.CASCADE, related_name="slots",
    )
    course_type = models.ForeignKey(
        CourseType,
        verbose_name=_("Course type"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="slots",
    )

    campus = models.ForeignKey(
        Campus, verbose_name=_("Campus"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )
    building = models.ForeignKey(
        Building, verbose_name=_("Building"), null=True, blank=True, on_delete=models.CASCADE, related_name="slots",
    )
    room = models.CharField(_("Room"), max_length=50, blank=True, null=True)

    date = models.DateField(_('Date'), blank=True, null=True)
    start_time = models.TimeField(_('Start time'), blank=True, null=True)
    end_time = models.TimeField(_('End time'), blank=True, null=True)

    teachers = models.ManyToManyField(ImmersionUser, verbose_name=_("Teachers"), related_name='slots')

    n_places = models.PositiveIntegerField(_('Number of places'))
    additional_information = models.CharField(_('Additional information'), max_length=128, null=True, blank=True)

    published = models.BooleanField(_("Published"), default=True, null=False)

    def available_seats(self):
        """
        :return: number of available seats for instance slot
        """
        s = self.n_places - Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()
        return 0 if s < 0 else s

    def registered_students(self):
        """
        :return: number of registered students for instance slot
        """
        return Immersion.objects.filter(slot=self.pk, cancellation_type__isnull=True).count()

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
        try:
            return self.ATT_STATUS[self.attendance_status][1]
        except KeyError:
            return ''

    class Meta:
        verbose_name = _('Immersion')
        verbose_name_plural = _('Immersions')


class GeneralSettings(models.Model):
    setting = models.CharField(_("Setting name"), max_length=128, unique=True)
    value = models.CharField(_("Setting value"), max_length=256, null=True, blank=True)
    description = models.CharField(_("Setting description"), max_length=256, default='')

    class Meta:
        verbose_name = _('General setting')
        verbose_name_plural = _('General settings')


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
    components_count = models.SmallIntegerField(_("Participating structures count"), default=0)
    trainings_one_slot_count = models.SmallIntegerField(_("Trainings offering at least one slot count"), default=0)
    courses_one_slot_count = models.SmallIntegerField(_("Courses offering at least one slot count"), default=0)
    total_slots_count = models.SmallIntegerField(_("Total slots count"), default=0)
    approved_highschools = models.SmallIntegerField(_("Approved highschools count"), default=0)
    highschools_without_students = models.SmallIntegerField(_("Highschools with no students"), default=0)

    class Meta:
        verbose_name = _('Annual statistics')
        verbose_name_plural = _('Annual statistics')

class CertificateLogo(models.Model):

    """
    CertificateLogo class (singleton)
    """

    logo = models.ImageField(
        _("Logo"),
        upload_to='uploads/certificate_logo/',
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )

    objects = CustomDeleteManager()

    @classmethod
    def object(cls):
        return cls._default_manager.all().first()

    # Singleton !
    def save(self, *args, **kwargs):
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
        upload_to='uploads/certificate_signature/',
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)') % {'authorized_types': 'gif, jpg, png'},
    )

    objects = CustomDeleteManager()

    @classmethod
    def object(cls):
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
