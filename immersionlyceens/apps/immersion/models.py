import json
import logging

from django.db import models
from django.utils.translation import gettext, ugettext_lazy as _
from immersionlyceens.apps.core import models as core_models

logger = logging.getLogger(__name__)

class HighSchoolStudentRecord(models.Model):
    """
    High school student class, linked to ImmersionUsers accounts
    """
    CIVS = [(1, _('Mr')),
            (2, _('Mrs'))]

    LEVELS = [
        (1, _('Pupil in year 12 / 11th grade student')),
        (2, _('Pupil in year 13 / 12th grade student')),
        (3, _('Above A Level / High-School Degree'))
    ]

    BACHELOR_TYPES = [
        (1, _('General')),
        (2, _('Technological')),
        (3, _('Professional'))
    ]

    POST_BACHELOR_ORIGIN_TYPES = BACHELOR_TYPES.copy()
    POST_BACHELOR_ORIGIN_TYPES.append(
        (4, _('DAEU'))
    )

    POST_BACHELOR_LEVELS = [
        (1, _('BTS1')),
        (2, _('BTS2')),
        (3, _('BTSA1')),
        (4, _('BTSA2')),
        (5, _('Other')),
    ]

    student = models.OneToOneField(
        core_models.ImmersionUser,
        verbose_name=_('Student'),
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="student_record"
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
    civility = models.SmallIntegerField(_("Civility"), default=1, choices=CIVS)
    phone = models.CharField(_("Phone number"), max_length=14)
    level = models.SmallIntegerField(_("Level"), default=1, choices=LEVELS)
    class_name = models.CharField(_("Class name"), blank=False, null=False, max_length=32)

    # For pre-bachelor levels
    bachelor_type = models.SmallIntegerField(_("Bachelor type"), default=1, choices=BACHELOR_TYPES)

    general_bachelor_teachings = models.ManyToManyField(core_models.GeneralBachelorTeaching,
        verbose_name=_("Components"), blank=True, related_name='student_records'
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

    # For post-bachelor levels
    post_bachelor_level = models.SmallIntegerField(_("Level"),
        default=1, null=True, blank=True, choices=POST_BACHELOR_LEVELS)
    origin_bachelor_type = models.SmallIntegerField(_("Bachelor type"),
        default=1, null=True, blank=True, choices=POST_BACHELOR_ORIGIN_TYPES)
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
        _("Number of allowed registrations for second semester"), null=True, blank=True)

    allowed_second_semester_registrations = models.SmallIntegerField(
        _("Number of allowed registrations for first semester"), null=True, blank=True)

    duplicates = models.TextField(_("Duplicates list"), null=True, blank=True, default=None)

    def __str__(self):
        return gettext("Record for %s %s" % (self.student.first_name, self.student.last_name))

    def search_duplicates(self):
        """
        Search records with same name, birth date and highschool
        :return:
        """
        dupes = HighSchoolStudentRecord.objects.filter(
            student__last_name=self.student.last_name, student__first_name=self.student.first_name,
            birth_date=self.birth_date, highschool=self.highschool
        ).exclude(id=self.id)

        ids_list = [record.id for record in dupes]

        if ids_list:
            self.duplicates = json.dumps(ids_list)
            self.save()

            for id in ids_list:
                other_ids_list = [self.id] + [i for i in ids_list if i!=id]
                json_list = json.dumps(other_ids_list)
                HighSchoolStudentRecord.objects.get(pk=id).update(duplicates=json_list)

            return ids_list
        elif self.duplicates is not None:
            self.duplicates = None
            self.save()

        return []

    def has_duplicates(self):
        return self.duplicates is not None

    def get_duplicates(self):
        if self.has_duplicates():
            return json.loads(self.duplicates)
        else:
            return []
