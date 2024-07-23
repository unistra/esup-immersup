import json
import logging
from typing import Any, List, Tuple

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext, gettext_lazy as _

from immersionlyceens.apps.core import models as core_models
from immersionlyceens.apps.core.models import Period, get_file_path

logger = logging.getLogger(__name__)


class HighSchoolStudentRecord(models.Model):
    """
    High school student class, linked to ImmersionUsers accounts
    """

    TO_COMPLETE = 0
    TO_VALIDATE = 1
    VALIDATED = 2
    REJECTED = 3
    TO_REVALIDATE = 4
    INIT = 5

    STATUSES = {
        "TO_COMPLETE": TO_COMPLETE,
        "TO_VALIDATE": TO_VALIDATE,
        "VALIDATED": VALIDATED,
        "REJECTED": REJECTED,
        "TO_REVALIDATE": TO_REVALIDATE,
        "INITIALIZATION": INIT,
    }

    # Display values
    VALIDATION_STATUS = [
        (TO_COMPLETE, _('To complete')),
        (TO_VALIDATE, _('To validate')),
        (VALIDATED, _('Validated')),
        (REJECTED, _('Rejected')),
        (TO_REVALIDATE, _('To revalidate')),
        (INIT, _('Initialization (to complete)'))
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
        null=True,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_records"
    )

    birth_date = models.DateField(_("Birth date"), null=True, blank=False)
    phone = models.CharField(_("Phone number"), max_length=14, blank=True, null=True)

    level = models.ForeignKey(
        core_models.HighSchoolLevel,
        verbose_name=_("Level"),
        null=True,
        blank=False,
        on_delete=models.CASCADE,
        related_name="high_school_student_record"
    )

    class_name = models.CharField(_("Class name"), blank=False, null=True, max_length=32)

    bachelor_type = models.ForeignKey(
        core_models.BachelorType,
        verbose_name=_('Bachelor type'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_records",
        limit_choices_to={'pre_bachelor_level': True}
    )

    general_bachelor_teachings = models.ManyToManyField(
        core_models.GeneralBachelorTeaching,
        verbose_name=_("General bachelor teachings"),
        blank=True,
        related_name='student_records'
    )

    technological_bachelor_mention = models.ForeignKey(
        core_models.BachelorMention,
        verbose_name=_('Technological bachelor mention'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_records"
    )

    professional_bachelor_mention = models.CharField(
        _("Professional bachelor mention"), blank=True, null=True, max_length=128)

    post_bachelor_level = models.ForeignKey(
        core_models.PostBachelorLevel,
        verbose_name=_("Post bachelor level"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="high_school_student_record"
    )

    origin_bachelor_type = models.ForeignKey(
        core_models.BachelorType,
        verbose_name=_('Origin bachelor type'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    current_diploma = models.CharField(
        _("Current diploma"), blank=True, null=True, max_length=128)

    attestation_documents = models.ManyToManyField(
        core_models.AttestationDocument,
        through="HighSchoolStudentRecordDocument"
    )

    visible_immersion_registrations = models.BooleanField(
        _("Allow students from my school to see my registrations"), default=False)

    visible_email = models.BooleanField(
        _("Allow students from my school to see my email address"), default=False)

    allow_high_school_consultation = models.BooleanField(
        _("Allow my high school to view my immersions and attendance certificates"), default=False)

    allowed_immersions = models.ManyToManyField(Period, through='HighSchoolStudentRecordQuota')

    validation = models.SmallIntegerField(_("Validation"), default=0, choices=VALIDATION_STATUS)

    duplicates = models.TextField(_("Duplicates list"), null=True, blank=True, default=None)
    solved_duplicates = models.TextField(_("Solved duplicates list"), null=True, blank=True, default=None)

    creation_date = models.DateTimeField(_("Creation date"), auto_now_add=True)
    updated_date = models.DateTimeField(_("Modification date"),auto_now=True)
    validation_date = models.DateTimeField(_("Validation date"), null=True, blank=True)
    rejected_date = models.DateTimeField(_("Rejected date"), null=True, blank=True)


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
        return self.validation == self.STATUSES["VALIDATED"]

    def set_status(self, status: str):
        """
        Update validation attribute
        """
        if isinstance(status, str) and status.upper() in self.STATUSES:
            self.validation = self.STATUSES[status.upper()]
            return True

        return False

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

    student = models.OneToOneField(
        core_models.ImmersionUser,
        verbose_name=_('Student'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_record"
    )

    uai_code = models.CharField(_("Home institution code"), blank=False, null=False, max_length=256)
    birth_date = models.DateField(_("Birth date"), null=True, blank=False)
    phone = models.CharField(_("Phone number"), max_length=14, blank=True, null=True)

    level = models.ForeignKey(
        core_models.StudentLevel,
        verbose_name=_("Level"),
        null=True,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_record"
    )

    institution = models.ForeignKey(
        core_models.HigherEducationInstitution,
        verbose_name=_("Home institution"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_records"
    )

    origin_bachelor_type = models.ForeignKey(
        core_models.BachelorType,
        verbose_name=_('Bachelor type'),
        null=True,
        blank=False,
        on_delete=models.PROTECT,
        related_name="+"
    )

    current_diploma = models.CharField(
        _("Current diploma"), blank=True, null=True, max_length=128)

    allowed_immersions = models.ManyToManyField(Period, through='StudentRecordQuota')

    creation_date = models.DateTimeField(_("Creation date"), auto_now_add=True)
    updated_date = models.DateTimeField(_("Modification date"),auto_now=True)

    def __str__(self):
        if hasattr(self, "student"):
            return gettext(f"Record for {self.student.first_name} {self.student.last_name}")
        else:
            return gettext(f"Record for student id {self.student_id}")

    def is_valid(self):
        return True

    def home_institution(self):
        """
        Get home institution if we can find a matching code, else return the code
        Returns (label, object) if found, (code, None) if not
        """

        # For compatibility
        if self.institution:
            return self.institution.label, self.institution
        else:
            return self.uai_code, None


    class Meta:
        verbose_name = _('Student record')
        verbose_name_plural = _('Student records')


class VisitorRecord(models.Model):
    """
    Visitor record class, linked to ImmersionUsers accounts
    """
    TO_COMPLETE = 0
    TO_VALIDATE = 1
    VALIDATED = 2
    REJECTED = 3
    TO_REVALIDATE = 4

    STATUSES = {
        "TO_COMPLETE": TO_COMPLETE,
        "TO_VALIDATE": TO_VALIDATE,
        "VALIDATED": VALIDATED,
        "REJECTED": REJECTED,
        "TO_REVALIDATE": TO_REVALIDATE,
    }

    VALIDATION_STATUS: List[Tuple[int, Any]] = [
        (TO_COMPLETE, _('To complete')),
        (TO_VALIDATE, _('To validate')),
        (VALIDATED, _('Validated')),
        (REJECTED, _('Rejected')),
        (TO_REVALIDATE, _('To revalidate'))
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
    birth_date = models.DateField(_("Birth date"), null=True, blank=False)
    motivation = models.TextField(_("Motivation"), null=True, blank=False)

    attestation_documents = models.ManyToManyField(
        core_models.AttestationDocument,
        through="VisitorRecordDocument"
    )

    validation = models.SmallIntegerField(_("Validation"), default=0, choices=VALIDATION_STATUS)
    allowed_immersions = models.ManyToManyField(Period, through='VisitorRecordQuota')

    creation_date = models.DateTimeField(_("Creation date"), auto_now_add=True)
    updated_date = models.DateTimeField(_("Modification date"),auto_now=True)
    validation_date = models.DateTimeField(_("Validation date"), null=True, blank=True)
    rejected_date = models.DateTimeField(_("Rejected date"), null=True, blank=True)

    def is_valid(self):
        return self.validation == self.STATUSES["VALIDATED"]

    def set_status(self, status: str):
        """
        Update validation attribute
        """
        if isinstance(status, str) and status.upper() in self.STATUSES:
            self.validation = self.STATUSES[status.upper()]
            return True

        return False

    def __str__(self):
        return gettext(f"Record for {self.visitor.first_name} {self.visitor.last_name}")

    class Meta:
        verbose_name = _('Visitor record')
        verbose_name_plural = _('Visitor records')


class HighSchoolStudentRecordQuota(models.Model):
    """
    M2M 'through' relation between high school student records and period for immersions quotas
    """
    record = models.ForeignKey(HighSchoolStudentRecord, related_name="quota", on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    allowed_immersions = models.PositiveIntegerField(
        _('Allowed immersions'), null=False, blank=False, default=1
    )

    def __str__(self):
        return f"{self.record} / {self.period} : {self.allowed_immersions}"

    class Meta:
        verbose_name = _('High school student record / Period quota')
        verbose_name_plural = _('High school student record / Period quotas')
        constraints = [
            models.UniqueConstraint(
                fields=['record', 'period'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_high_school_student_record_period'
            )
        ]

class StudentRecordQuota(models.Model):
    """
    M2M 'through' relation between student records and period for immersions quotas
    """
    record = models.ForeignKey(StudentRecord, related_name="quota", on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    allowed_immersions = models.PositiveIntegerField(
        _('Allowed immersions'), null=False, blank=False, default=1
    )

    def __str__(self):
        return f"{self.record} / {self.period} : {self.allowed_immersions}"

    class Meta:
        verbose_name = _('Student record / Period quota')
        verbose_name_plural = _('Student record / Period quotas')
        constraints = [
            models.UniqueConstraint(
                fields=['record', 'period'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_student_record_period'
            )
        ]


class VisitorRecordQuota(models.Model):
    """
    M2M 'through' relation between visitor records and period for immersions quotas
    """
    record = models.ForeignKey(VisitorRecord, related_name="quota", on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    allowed_immersions = models.PositiveIntegerField(
        _('Allowed immersions'), null=False, blank=False, default=1
    )

    def __str__(self):
        return f"{self.record} / {self.period} : {self.allowed_immersions}"

    class Meta:
        verbose_name = _('Visitor record / Period quota')
        verbose_name_plural = _('Visitor record / Period quotas')
        constraints = [
            models.UniqueConstraint(
                fields=['record', 'period'],
                deferrable=models.Deferrable.IMMEDIATE,
                name='unique_visitor_record_period'
            )
        ]


class RecordDocument(models.Model):
    """
    Abstract base Class for record documents
    """
    # FIXME : move this in settings ?
    ALLOWED_TYPES = {
        'png': "image/png",
        'jpeg': "image/jpeg",
        'jpg': "image/jpeg",
        'pdf': "application/pdf",
        'doc': "application/msword",
        'docx': "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        'odt': "application/vnd.oasis.opendocument.text",
    }

    created = models.DateTimeField(_("Creation date"), auto_now_add=True)
    last_updated = models.DateTimeField(_("Last updated date"), auto_now=True)
    attestation = models.ForeignKey(core_models.AttestationDocument, on_delete=models.CASCADE)
    document = models.FileField(
        _("Document"),
        upload_to=get_file_path,
        blank=False,
        null=False,
        help_text=_('Only files with type (%(authorized_types)s). Max file size : %(max_size)s')
                  % {
                      'authorized_types': ', '.join(ALLOWED_TYPES.keys()),
                      'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE)
                  },
    )
    deposit_date = models.DateTimeField(_("Deposit date"), blank=True, null=True)
    validity_date = models.DateField(_("Valid until"), blank=True, null=True)
    archive = models.BooleanField(_("Archive status"), default=False)

    # The following fields are copied from AttestationDocument object on creation,
    # and are not meant to be updated then
    for_minors = models.BooleanField(_("For minors"), default=True)
    mandatory = models.BooleanField(_("Mandatory"), default=True)
    requires_validity_date = models.BooleanField(_("Requires a validity date"), default=True)
    renewal_email_sent = models.BooleanField(_("Renewal warning email sent"), default=False)

    def __str__(self):
        return f"{self.record} / {self.attestation}"

    def delete(self, *args, **kwargs):
        if bool(self.document):
            try:
                self.document.storage.delete(self.document.name)
            except Exception as e:
                logger.error(f"Cannot delete {self.document.name} : {e}")

        return super().delete(*args, **kwargs)

    class Meta:
        abstract = True


class HighSchoolStudentRecordDocument(RecordDocument):
    """
    M2M 'through' relation between high school student records and attestation documents
    """
    record = models.ForeignKey(HighSchoolStudentRecord, related_name="attestation", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('High school student record / Attestation document')
        verbose_name_plural = _('High school student record / Attestation documents')
        constraints = [
            models.UniqueConstraint(
                fields=['record', 'attestation', 'archive'],
                condition=Q(archive=False),
                name='unique_high_school_student_record_document'
            )
        ]


class VisitorRecordDocument(RecordDocument):
    """
    M2M 'through' relation between visitor records and attestation documents
    """
    record = models.ForeignKey(VisitorRecord, related_name="attestation", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Visitor record / Attestation document')
        verbose_name_plural = _('Visitor record / Attestation documents')
        constraints = [
            models.UniqueConstraint(
                fields=['record', 'attestation', 'archive'],
                condition=Q(archive=False),
                name='unique_visitor_record_document'
            )
        ]