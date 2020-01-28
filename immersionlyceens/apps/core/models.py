import enum
import logging
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from immersionlyceens.fields import UpperCharField
from immersionlyceens.libs.geoapi.utils import get_cities, get_departments

logger = logging.getLogger(__name__)


class Component(models.Model):
    """
    Component class
    """

    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=128)
    url = models.URLField(_("Website address"), max_length=256, blank=True, null=True)
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


class ImmersionUser(AbstractUser):
    """
    Main user class
    """

    _user_filters = [
        lambda has_group, su: has_group or su,
        lambda has_group, su: has_group and not su,
    ]
    _groups = {
        'SCUIO-IP': 'scuio_ip_manager',
        'REF-CMP': 'component_manager',
        'REF-LYC': 'high_school_manager',
        'ETU': 'student',
        'ENS-CH': 'teacher',
        'SRV-JUR': 'legal_department_staff',
    }

    components = models.ManyToManyField(
        Component, verbose_name=_("Components"), blank=True, related_name='referents'
    )

    class Meta:
        verbose_name = _('User')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for code, name in self._groups.items():
            setattr(self, 'is_%s' % name, partial(self.has_groups, code, negated=False))

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
            self.is_superuser, self.groups.filter(name__in=groups).exists()
        )

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
        TrainingSubdomain,
        verbose_name=_("Training subdomains"),
        blank=False,
        related_name='Trainings',
    )
    components = models.ManyToManyField(
        Component, verbose_name=_("Components"), blank=False, related_name='Trainings'
    )
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

        verbose_name = _('Bachelor mention')
        verbose_name_plural = _('Bachelor mentions')

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
        Campus,
        verbose_name=_("Campus"),
        default=None,
        on_delete=models.CASCADE,
        related_name="buildings",
    )
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
                _('A building with this label for the same campus already exists')
            )


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

    label = models.CharField(_("Label"), max_length=256, unique=True)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        """Meta class"""

        verbose_name = _('Course type')
        verbose_name_plural = _('Course type')

    def __str__(self):
        """str"""  # from .utils import get_cities, get_departments
        return self.label

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
            raise ValidationError(_('A public type with this label already exists'))

    def save(self, *args, **kwargs):
        objs = UniversityYear.objects.filter(active=True)
        if len(objs) < 1:
            self.active = True
        super(UniversityYear, self).save(*args, **kwargs)

    def date_is_between(self, _date):
        return self.start_date <= _date and _date <= self.end_date


class Holiday(models.Model):
    """University year"""

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
            raise ValidationError(_('An holiday with this label already exists'))


class Vacation(models.Model):
    """University year"""

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


class Calendar(models.Model):
    """University year"""

    CALENDAR_MODE = [
        ('YEAR', _('Year')),
        ('SEMESTER', _('Semester')),
    ]

    label = models.CharField(_("Label"), max_length=256, unique=True)
    calendar_mode = models.CharField(
        _("Calendar mode"), max_length=16, choices=CALENDAR_MODE, default="YEAR"
    )

    year_start_date = models.DateField(_("Year start date"), null=True, blank=True)
    year_end_date = models.DateField(_("Year end date"), null=True, blank=True)
    year_registration_start_date = models.DateField(
        _("Year start registration date"), null=True, blank=True
    )
    year_nb_authorized_immersion = models.PositiveIntegerField(
        _("Number of authorized immersions per year"), default=4
    )

    semester1_start_date = models.DateField(_("Semester 1 start date"), null=True, blank=True)
    semester1_end_date = models.DateField(_("Semester 1 end date"), null=True, blank=True)
    semester1_registration_start_date = models.DateField(
        _("Semester 1 start registration date"), null=True, blank=True
    )
    semester2_start_date = models.DateField(_("Semester 2 start date"), null=True, blank=True)
    semester2_end_date = models.DateField(_("Semester 2 end date"), null=True, blank=True)
    semester2_registration_start_date = models.DateField(
        _("Semester 2 start registration date"), null=True, blank=True
    )
    registration_start_date_per_semester = models.PositiveIntegerField(
        _("Number of authorized immersions per semester"), default=2
    )

    global_evaluation_date = models.DateField(
        _("Global evaluation send date"), null=True, blank=True
    )

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
            return self.semester1_start_date <= _date and _date <= self.semester2_end_date


class HighSchool(models.Model):
    """
    HighSchool class
    """

    class Meta:
        verbose_name = _('High school')
        unique_together = ('label', 'city')

    choices_departments = choices_cities = choices_zipcodes = []

    if settings.USE_GEOAPI:
        choices_departments = get_departments()
        choices_cities = get_cities()

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    address = models.CharField(_("Address"), max_length=255, blank=False, null=False)
    address2 = models.CharField(_("Address2"), max_length=255, blank=True, null=True)
    address3 = models.CharField(_("Address3"), max_length=255, blank=True, null=True)
    department = models.CharField(
        _("Department"), max_length=128, blank=False, null=False, choices=choices_departments
    )
    city = UpperCharField(
        _("City"), max_length=255, blank=False, null=False, choices=choices_cities
    )
    zip_code = models.CharField(
        _("Zip code"), max_length=128, blank=False, null=False, choices=choices_zipcodes
    )
    phone_number = models.CharField(_("Phone number"), max_length=20, null=False, blank=False)
    fax = models.CharField(_("Fax"), max_length=20, null=True, blank=True)
    email = models.EmailField(_('Email'))
    head_teacher_name = models.CharField(
        _("Head teacher name"),
        max_length=255,
        blank=False,
        null=False,
        help_text=_('civility last name first name'),
    )
    referent_name = models.CharField(
        _('Referent name'),
        max_length=255,
        blank=False,
        null=False,
        help_text=_('last name first name'),
    )
    referent_phone_number = models.CharField(
        _("Referent phone number"), max_length=20, blank=False, null=False
    )
    referent_email = models.EmailField(_('Referent email'))
    convention_start_date = models.DateField(_("Convention start date"), null=True, blank=True)
    convention_end_date = models.DateField(_("Convention end date"), null=True, blank=True)

    def __str__(self):
        # TODO: Should we display city as well (????)
        return self.label


class Course(models.Model):
    """
    Course class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)

    training = models.ForeignKey(
        Training,
        verbose_name=_("Training"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    published = models.BooleanField(_("Published"), default=True)

    teachers = models.ManyToManyField(
        ImmersionUser, verbose_name=_("Teachers"), related_name='courses'
    )

    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        unique_together = ('training', 'label')


class MailTemplateVars(models.Model):
    code = models.CharField(_("Code"), max_length=64, blank=False, null=False, unique=True)
    description = models.CharField(
        _("Description"), max_length=128, blank=False, null=False, unique=True
    )

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
        MailTemplateVars,
        related_name='mail_templates',
        verbose_name=_("Available variables"),
        blank=False,
    )

    def __str__(self):
        return "%s : %s" % (self.code, self.label)

    class Meta:
        verbose_name = _('Mail template')
        verbose_name_plural = _('Mail templates')


class InformationText(models.Model):
    label = models.CharField(_("Label"), max_length=255, blank=False, null=False)
    code = models.CharField(
        _("Code"),
        max_length=64,
        help_text=_('civility last name first name'),
        blank=False,
        null=False,
    )
    content = models.TextField(_('Content'), max_length=2000, blank=False, null=False)
    active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _('Information text')
        verbose_name_plural = _('Information texts')


class CustomDeleteManager(models.Manager):
    def delete(self):
        for obj in self.get_queryset():
            obj.delete()


class AccompanyingDocument(models.Model):
    """
    AccompanyingDocument class
    """

    label = models.CharField(_("Label"), max_length=255, blank=False, null=False, unique=True)
    public_type = models.ForeignKey(
        PublicType,
        verbose_name=_("Public type"),
        null=False,
        blank=False,
        related_name="publictypes",
        on_delete=models.CASCADE,
    )
    description = models.CharField(_("Description"), max_length=255, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)
    document = models.FileField(
        _("Document"),
        upload_to='uploads/accompanyingdocs/%Y',
        blank=False,
        null=False,
        help_text=_('Only files with type (%s)' % ','.join(settings.CONTENT_TYPES)),
    )

    objects = CustomDeleteManager()

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
        help_text=_('Only files with type (%s)' % ','.join(settings.CONTENT_TYPES)),
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
