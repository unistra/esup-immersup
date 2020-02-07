import enum
import logging
import re
from functools import partial

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from mailmerge import MailMerge

from immersionlyceens.fields import UpperCharField
from immersionlyceens.libs.geoapi.utils import get_cities, get_departments

from .managers import ActiveManager, ComponentQuerySet

logger = logging.getLogger(__name__)


class Component(models.Model):
    """
    Component class
    """

    code = models.CharField(_("Code"), max_length=16, unique=True)
    label = models.CharField(_("Label"), max_length=128)
    url = models.URLField(_("Website address"), max_length=256, blank=True, null=True)
    active = models.BooleanField(_("Active"), default=True)

    objects = models.Manager()  # default manager
    activated = ActiveManager.from_queryset(
        ComponentQuerySet
    )()  # returns only activated components

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

    def has_course_rights(self, course_id):
        """
        Check if the user can update / delete a course
        :param course_id: Course id
        :return: boolean
        """
        if self.is_superuser or self.has_groups('REF-CMP', 'SCUIO-IP'):
            return True

        try:
            course = Course.objects.get(pk=course_id)
            course_components = course.training.components.all()

            if course_components & self.components.all():
                return True

        except Course.DoesNotExist:
            return False

        return False

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
            raise ValidationError(_('A university year with this label already exists'))

    def save(self, *args, **kwargs):
        if not UniversityYear.objects.filter(active=True).exists():
            self.active = True

        super(UniversityYear, self).save(*args, **kwargs)

    def date_is_between(self, _date):
        return self.start_date <= _date <= self.end_date


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

    component = models.ForeignKey(
        Component,
        verbose_name=_("Component"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    published = models.BooleanField(_("Published"), default=True)

    teachers = models.ManyToManyField(
        ImmersionUser, verbose_name=_("Teachers"), related_name='courses'
    )

    url = models.URLField(_("Website address"), max_length=1024, blank=True, null=True)

    def __str__(self):
        return self.label

    def get_components_queryset(self):
        return self.training.components.all()

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
    code = models.CharField(_("Code"), max_length=64, blank=False, null=False,)
    # 10K chars => MOA demand
    content = models.TextField(_('Content'), max_length=10000, blank=False, null=False)
    description = models.TextField(
        _('Description'), max_length=2000, blank=False, null=False, default=''
    )
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


class CustomDeleteManager(models.Manager):
    def delete(self):
        for obj in self.get_queryset():
            obj.delete()


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
    # TODO: change type mime param to implement labels !
    document = models.FileField(
        _("Document"),
        upload_to='uploads/accompanyingdocs/%Y',
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s)')
        % {'authorized_types': ','.join(settings.CONTENT_TYPES)},
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

    def get_types(self):
        # TODO:
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


class AttendanceCertificateModel(models.Model):
    """
    Attendance Certificate Model class
    """

    document = models.FileField(
        _("Document"),
        upload_to='uploads/attendance_cert_model/',
        blank=False,
        null=False,
        help_text=_('Only files with type (docx)'),
    )

    objects = CustomDeleteManager()

    class Meta:
        """Meta class"""

        verbose_name = _('Attendance certificate model')
        verbose_name_plural = _('Attendance certificate model')

    def __str__(self):
        """str"""
        return self.document.path.split('/')[-1]

    def delete(self, using=None, keep_parents=False):
        """Delete file uploaded from document Filefield"""
        self.document.storage.delete(self.document.name)
        super().delete()

    def save(self, *args, **kwargs):
        # Be sure to not save an other attendance certificate model !!!!
        if not self.pk and AttendanceCertificateModel.objects.exists():
            raise ValidationError('only one Attendance certificate model is allowed')
        return super().save(*args, **kwargs)

    def get_merge_fields(self):
        if self.document:
            doc = MailMerge(self.document.path)
            return doc.get_merge_fields()
        return ""

    def show_merge_fields(self):
        if self.document:
            fields = MailMerge(self.document.path).get_merge_fields()
            return ", ".join([d for d in fields]) if bool(fields) else _('No variables in file')

    get_merge_fields.short_description = _('Variables')
    show_merge_fields.short_description = _('Variables')


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
            raise ValidationError(
                _('An evaluation form link with this evaluation type already exists')
            )


class Slot(models.Model):
    """
    Course class
    """

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    course_type = models.ForeignKey(
        CourseType,
        verbose_name=_("Course type"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="slots",
    )

    campus = models.ForeignKey(
        Campus,
        verbose_name=_("Campus"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    building = models.ForeignKey(
        Building,
        verbose_name=_("Building"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    room = models.CharField(_("Room"), max_length=16, blank=False, null=False)

    date = models.DateField(_('Date'))
    start_time = models.TimeField(_('Start time'))
    end_time = models.TimeField(_('End time'))

    teachers = models.ManyToManyField(
        ImmersionUser, verbose_name=_("Teachers"), related_name='slots'
    )

    n_places = models.PositiveIntegerField(_('Number of places'))
    additional_information = models.CharField(
        _('Additional information'), max_length=128, null=True
    )

    published = models.BooleanField(_("Published"), default=True)

    class Meta:
        verbose_name = _('Slot')
        verbose_name_plural = _('Slots')
        # unique_together = (
        #     'training',
        #     'course',
        #     'course_type',
        #     'campus',
        #     'building',
        #     'date',
        #     'start_time',
        #     'end_time',
        # )
