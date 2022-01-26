import json
import logging
from typing import Any, List, Tuple

from django.conf import settings
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext, gettext_lazy as _
from immersionlyceens.apps.core import models as core_models
from immersionlyceens.apps.core.models import Calendar, get_file_path

logger = logging.getLogger(__name__)


class HighSchoolStudentRecord(models.Model):
    """
    High school student class, linked to ImmersionUsers accounts
    """

    # Use gettext on the next one because strings HAS to be translated here
    # in order to avoid sending lazy translation objects to JSON in charts API
    """
    LEVELS = [
        (1, gettext('Pupil in year 11 / 10th grade student')),
        (2, gettext('Pupil in year 12 / 11th grade student')),
        (3, gettext('Pupil in year 13 / 12th grade student')),
        (4, gettext('Above A Level / High-School Degree'))
    ]
    """

    BACHELOR_TYPES = [
        (1, _('General')),
        (2, _('Technological')),
        (3, _('Professional'))
    ]

    POST_BACHELOR_ORIGIN_TYPES = BACHELOR_TYPES.copy()
    POST_BACHELOR_ORIGIN_TYPES.append(
        (4, _('DAEU'))
    )

    """
    POST_BACHELOR_LEVELS = [
        (1, _('BTS1')),
        (2, _('BTS2')),
        (3, _('BTSA1')),
        (4, _('BTSA2')),
        (5, _('Other')),
    ]
    """

    VALIDATION_STATUS = [
        (1, _('To validate')),
        (2, _('Validated')),
        (3, _('Rejected'))
    ]

    student = models.OneToOneField(
        core_models.ImmersionUser,
        verbose_name=_('Student'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="high_school_student_record"
    )

    highschool = models.ForeignKey(
        core_models.HighSchool,
        verbose_name=_('High school'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_records"
    )

    birth_date = models.DateField(_("Birth date"), null=False, blank=False)
    phone = models.CharField(_("Phone number"), max_length=14, blank=True, null=True)
    # level = models.SmallIntegerField(_("Level"), default=1, choices=LEVELS)

    level = models.ForeignKey(
        core_models.HighSchoolLevel,
        verbose_name=_("Level"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="high_school_student_record"
    )

    class_name = models.CharField(_("Class name"), blank=False, null=False, max_length=32)

    # For pre-bachelor levels
    bachelor_type = models.SmallIntegerField(_("Bachelor type"), default=1, choices=BACHELOR_TYPES)

    general_bachelor_teachings = models.ManyToManyField(
        core_models.GeneralBachelorTeaching,
        verbose_name=_("Structures"),
        blank=True,
        related_name='student_records'
    )

    technological_bachelor_mention = models.ForeignKey(
        core_models.BachelorMention,
        verbose_name=_('Technological bachelor series'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_records"
    )

    professional_bachelor_mention = models.CharField(
        _("Professional bachelor mention"), blank=True, null=True, max_length=128)

    # For post-bachelor levels
    # post_bachelor_level = models.SmallIntegerField(_("Post bachelor level"),
    #  default=1, null=True, blank=True, choices=POST_BACHELOR_LEVELS)

    post_bachelor_level = models.ForeignKey(
        core_models.PostBachelorLevel,
        verbose_name=_("Post bachelor level"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="high_school_student_record"
    )

    origin_bachelor_type = models.SmallIntegerField(_("Origin bachelor type"),
                                                    default=1, null=True, blank=True,
                                                    choices=POST_BACHELOR_ORIGIN_TYPES)
    current_diploma = models.CharField(
        _("Current diploma"), blank=True, null=True, max_length=128)

    # ===

    visible_immersion_registrations = models.BooleanField(
        _("Allow students from my school to see my registrations"), default=False)

    visible_email = models.BooleanField(
        _("Allow students from my school to see my email address"), default=False)

    allowed_global_registrations = models.SmallIntegerField(
        _("Number of allowed year registrations"), null=True, blank=True)

    allowed_first_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for first semester (excluding visits and events)"), null=True, blank=True)

    allowed_second_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for second semester (excluding visits and events)"), null=True, blank=True)

    validation = models.SmallIntegerField(_("Validation"), default=1, choices=VALIDATION_STATUS)

    duplicates = models.TextField(_("Duplicates list"), null=True, blank=True, default=None)
    solved_duplicates = models.TextField(_("Solved duplicates list"), null=True, blank=True, default=None)

    def __str__(self):
        return gettext(f"Record for {self.student.first_name} {self.student.last_name}")

    def search_duplicates(self):
        """
        Search records with same name, birth date and highschool
        :return:
        """
        solved_duplicates_list = [int(x) for x in self.solved_duplicates.split(',')] if self.solved_duplicates else []

        dupes = HighSchoolStudentRecord.objects.filter(
            student__last_name__iexact=self.student.last_name, student__first_name__iexact=self.student.first_name,
            birth_date=self.birth_date, highschool=self.highschool
        ).exclude(id=self.id).exclude(id__in=solved_duplicates_list)

        ids_list = [record.id for record in dupes]

        if ids_list:
            self.duplicates = json.dumps(ids_list)
            self.save()

            for id in ids_list:
                other_ids_list = sorted([self.id] + [i for i in ids_list if i != id])
                try:
                    record = HighSchoolStudentRecord.objects.get(pk=id)
                    solved_duplicates = {
                        int(x) for x in record.solved_duplicates.split(',')} if record.solved_duplicates else set()
                    record.duplicates = json.dumps(list(set(other_ids_list) - solved_duplicates))
                    record.save()
                except HighSchoolStudentRecord.DoesNotExist:
                    pass

            return ids_list
        elif self.duplicates is not None:
            self.duplicates = None
            self.save()

        return []

    def has_duplicates(self):
        """
        Returns True if record has duplicates
        """
        return self.duplicates is not None

    def get_duplicates(self):
        """
        Returns duplicates list
        """
        if self.has_duplicates():
            return sorted(json.loads(self.duplicates))
        else:
            return []

    def remove_duplicate(self, id=None):
        """
        Remove a record id from duplicates list
        """
        try:
            id = int(id)
        except ValueError:
            return

        if self.duplicates:
            dupes = json.loads(self.duplicates)
            try:
                dupes.remove(id)
                self.duplicates = json.dumps(dupes) if dupes else None
            except ValueError:
                pass

        if self.solved_duplicates:
            solved_list = self.solved_duplicates.split(',')
            if str(id) not in solved_list:
                solved_list.append(str(id))
                self.solved_duplicates = ','.join(solved_list)
        else:
            self.solved_duplicates = str(id)

        self.save()

    def is_valid(self):
        return self.validation == 2

    @classmethod
    def get_duplicate_tuples(cls):
        dupes_list = []

        records = cls.objects.filter(duplicates__isnull=False)

        for record in records:
            dupes_list.append(tuple(d for d in sorted(json.loads(record.duplicates) + [record.id])))

        return set(dupes_list)

    @classmethod
    def clear_duplicate(cls, record_id):
        """
        Aggressive method to clear a record id from all records duplicates lists
        """
        for record in cls.objects.filter(duplicates__isnull=False):
            try:
                dupes = json.loads(record.duplicates)
                dupes.remove(record_id)  # will raise a Value error if record_id not in dupes
                record.duplicates = json.dumps(dupes) if dupes else None
                record.save()
            except Exception:
                pass

        for record in cls.objects.filter(solved_duplicates__isnull=False):
            try:
                solved_dupes = record.solved_duplicates.split(',')
                solved_dupes.remove(str(record_id))
                record.solved_duplicates = ','.join(solved_dupes)
                record.save()
            except Exception:
                pass

    class Meta:
        verbose_name = _('High school student record')
        verbose_name_plural = _('High school student records')


class StudentRecord(models.Model):
    """
    Student record class, linked to ImmersionUsers accounts
    """

    """
    LEVELS = [
        (1, _('Licence 1 (1st year above A level)')),
        (2, _('Licence 2 (2nd year above A level)')),
        (3, _('Licence 3 (3rd year above A level)')),
        (4, _('BTEC 1')),
        (5, _('BTEC 2')),
        (6, _('Other')),
    ]
    """

    BACHELOR_TYPES = [
        (1, _('General')),
        (2, _('Technological')),
        (3, _('Professional')),
        (4, _('DAEU'))
    ]

    student = models.OneToOneField(
        core_models.ImmersionUser,
        verbose_name=_('Student'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_record"
    )

    uai_code = models.CharField(_("Home institution code"), blank=False, null=False, max_length=256)
    birth_date = models.DateField(_("Birth date"), null=False, blank=False)
    phone = models.CharField(_("Phone number"), max_length=14, blank=True, null=True)
    # level = models.SmallIntegerField(_("Level"), default=1, blank=False, null=False, choices=LEVELS)

    level = models.ForeignKey(
        core_models.StudentLevel,
        verbose_name=_("Level"),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_record"
    )

    origin_bachelor_type = models.SmallIntegerField(_("Origin bachelor type"),
                                                    default=1, null=False, blank=False, choices=BACHELOR_TYPES)

    current_diploma = models.CharField(
        _("Current diploma"), blank=True, null=True, max_length=128)

    allowed_global_registrations = models.SmallIntegerField(
        _("Number of allowed year registrations (excluding visits and events)"), null=True, blank=True)

    allowed_first_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for second semester (excluding visits and events)"), null=True, blank=True)

    allowed_second_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for first semester (excluding visits and events)"), null=True, blank=True)

    def __str__(self):
        return gettext(f"Record for {self.student.first_name} {self.student.last_name}")

    def is_valid(self):
        return True

    def home_institution(self):
        """
        Get home institution if we can find a matching code, else return the code
        Returns (label, object) if found, (code, None) if not
        """
        try:
            inst = core_models.HigherEducationInstitution.objects.get(uai_code=self.uai_code)
            return inst.label, inst
        except core_models.HigherEducationInstitution.DoesNotExist:
            return self.uai_code, None

    class Meta:
        verbose_name = _('Student record')
        verbose_name_plural = _('Student records')


class VisitorRecord(models.Model):
    """
    Visitor record class, linked to ImmersionUsers accounts
    """
    VALIDATION_STATUS: List[Tuple[int, Any]] = [
        (1, _('To validate')),
        (2, _('Validated')),
        (3, _('Rejected'))
    ]
    AUTH_CONTENT_TYPES: List[str] = ["jpg", "jpeg", "png"]

    visitor = models.OneToOneField(
        core_models.ImmersionUser,
        verbose_name=_('Visitor'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="visitor_record"
    )
    phone = models.CharField(_("Phone number"), max_length=14, blank=True, null=True)
    birth_date = models.DateField(_("Birth date"), null=False, blank=False)

    motivation = models.TextField(_("Motivation"), null=False, blank=False)
    identity_document = models.FileField(
        _("Identity document"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(AUTH_CONTENT_TYPES),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )
    civil_liability_insurance = models.FileField(
        _("Civil liability insurance"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(AUTH_CONTENT_TYPES),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )

    validation = models.SmallIntegerField(_("Validation"), default=1, choices=VALIDATION_STATUS)
    allowed_global_registrations = models.SmallIntegerField(
        _("Number of allowed year registrations (excluding visits and events)"), null=True, blank=True)
    allowed_first_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for second semester (excluding visits and events)"), null=True, blank=True)
    allowed_second_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for first semester (excluding visits and events)"), null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.allowed_first_semester_registrations is None and self.allowed_second_semester_registrations is None \
                and self.allowed_global_registrations is None:
            calendar = Calendar.objects.all().first()
            self.allowed_first_semester_registrations = calendar.nb_authorized_immersion_per_semester
            self.allowed_second_semester_registrations = calendar.nb_authorized_immersion_per_semester
            self.allowed_global_registrations = calendar.year_nb_authorized_immersion

        super().save(*args, **kwargs)


    def is_valid(self):
        return self.validation == 2


    def __str__(self):
        return gettext(f"Record for {self.visitor.first_name} {self.visitor.last_name}")

    def is_valid(self):
        return self.validation == 2

    class Meta:
        verbose_name = _('Visitor record')
        verbose_name_plural = _('Visitor records')
