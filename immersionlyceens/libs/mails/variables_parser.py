import logging
import re

from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import ugettext as _

from immersionlyceens.apps.core.models import EvaluationFormLink, EvaluationType, Immersion, UniversityYear
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
from immersionlyceens.libs.utils import get_general_setting

logger = logging.getLogger(__name__)


def multisub(subs, subject):
    """
    Simultaneously replace all vars in text
    """
    pattern = '|'.join('(%s)' % re.escape(p) for p, s in subs)
    substs = [s for p, s in subs]
    replace = lambda m: substs[m.lastindex - 1]
    return re.sub(pattern, replace, subject)


def parser(message_body, available_vars=None, user=None, request=None, **kwargs):
    slot = kwargs.get('slot')
    slot_list = kwargs.get('slot_list')
    course = kwargs.get('course')
    immersion = kwargs.get('immersion')
    slot_survey = None
    global_survey = None
    institution_label = None
    record = None

    if request:
        # The following won't work in 'commands'
        platform_url = request.build_absolute_uri(reverse('home'))
    else:
        try:
            platform_url = get_general_setting("PLATFORM_URL")
        except (ValueError, NameError):
            logger.warning("Warning : PLATFORM_URL not set in core General Settings")
            platform_url = "https://<plateforme immersion>"

    try:
        slot_survey = EvaluationFormLink.objects.get(evaluation_type__code='EVA_CRENEAU', active=True)
    except (EvaluationFormLink.DoesNotExist, EvaluationFormLink.MultipleObjectsReturned):
        pass

    try:
        global_survey = EvaluationFormLink.objects.get(evaluation_type__code='EVA_DISPOSITIF', active=True)
    except (EvaluationFormLink.DoesNotExist, EvaluationFormLink.MultipleObjectsReturned):
        pass

    try:
        year = UniversityYear.objects.get(active=True)
    except UniversityYear.DoesNotExist:
        return None

    vars = [
        ('${annee}', year.label),
        ('${urlPlateforme}', platform_url)
    ]

    if course:
        vars += [
            ('${cours.libelle}', course.label),
            ('${cours.nbplaceslibre}', course.free_seats())
        ]

    if slot:
        vars += [
            ('${creneau.batiment}', slot.building.label),
            ('${creneau.campus}', slot.campus.label),
            ('${creneau.composante}', slot.course.component.label),
            ('${creneau.cours}', slot.course.label),
            ('${creneau.date}', date_format(slot.date)),
            ('${creneau.enseignants}', ','.join(["%s %s" % (t.first_name, t.last_name) for t in slot.teachers.all()])),
            ('${creneau.formation}', slot.course.training.label),
            ('${creneau.heuredebut}', slot.start_time.strftime("%-Hh%M")),
            ('${creneau.heurefin}', slot.end_time.strftime("%-Hh%M")),
            ('${creneau.info}', slot.additional_information),
            ('${creneau.salle}', slot.room),
            ('${creneau.type}', slot.course_type.full_label),
        ]

        # Registered students to a slot
        registered_students = []

        for registration in Immersion.objects.filter(slot=slot, cancellation_type__isnull=True):
            institution_label = _("Unknown home institution")
            if registration.student.is_high_school_student():
                record = registration.student.get_high_school_student_record()
                if record and record.highschool:
                    institution_label = record.highschool.label
            elif registration.student.is_student():
                record = registration.student.get_student_record()
                if record:
                    uai_code, institution = record.home_institution()
                    institution_label = institution.label if institution else uai_code

            registered_students.append(
                "%s %s - %s" % (registration.student.last_name, registration.student.first_name, institution_label)
            )

        vars += [('${listeInscrits}', '<br />'.join(sorted(registered_students)))]

    if immersion and immersion.cancellation_type:
        vars += [('${motifAnnulation}', immersion.cancellation_type.label)]

    if user:
        vars += [
            ('${nom}', user.last_name),
            ('${prenom}', user.first_name),
            ('${ens.nom}', user.last_name),  # ! doublon
            ('${ens.prenom}', user.first_name),  # ! doublon
            ('${referentlycee.nom}', user.last_name),  # ! doublon
            ('${referentlycee.prenom}', user.first_name),  # ! doublon
            ('${identifiant}', user.get_cleaned_username()),
            ('${jourDestructionCptMin}', user.get_localized_destruction_date()),
        ]

        if request:
            vars += [
                (
                    '${lienValidation}',
                    "<a href='{0}'>{0}</a>".format(
                        request.build_absolute_uri(
                            reverse('immersion:activate', kwargs={'hash': user.validation_string})
                        )
                    ),
                ),
                (
                    '${lienMotDePasse}',
                    "<a href='{0}'>{0}</a>".format(
                        request.build_absolute_uri(
                            reverse('immersion:reset_password', kwargs={'hash': user.recovery_string})
                        )
                    ),
                ),
            ]
        else:
            vars += [
                (
                    '${lienValidation}',
                    "<a href='{0}{1}'>{0}{1}</a>".format(
                        platform_url, reverse('immersion:activate', kwargs={'hash': user.validation_string})
                    ),
                ),
                (
                    '${lienMotDePasse}',
                    "<a href='{0}{1}'>{0}{1}</a>".format(
                        platform_url, reverse('immersion:reset_password', kwargs={'hash': user.recovery_string})
                    ),
                ),
            ]

        if user.is_high_school_student():
            try:
                vars.append(('${lycee}', user.high_school_student_record.highschool.label))
                vars.append(
                    ('${etudiant_date_naissance}', date_format(user.high_school_student_record.birth_date, 'd/m/Y'))
                )
            except HighSchoolStudentRecord.DoesNotExist:
                pass
        elif user.is_student():
            # TODO: maybe instead of lycee use a home_institution tpl var ???
            vars.append(('${lycee}', institution_label))
            if record:
                vars.append(('${etudiant_date_naissance}', date_format(record.birth_date, 'd/m/Y')))
        elif user.highschool:
            vars.append(('${lycee}', user.highschool.label))

    if slot_list:
        slot_txt = [
            "* %s (%s - %s) : %s (%s)<br />Bâtiment %s, salle %s<br /> -> %s"
            % (
                date_format(s.date),
                s.start_time.strftime("%-Hh%M"),
                s.end_time.strftime("%-Hh%M"),
                s.course.label,
                s.course_type.label,
                s.building,
                s.room,
                ','.join(["%s %s" % (t.first_name, t.last_name) for t in s.teachers.all()]),
            )
            for s in slot_list
        ]
        vars += [('${creneaux.liste}', '<br /><br />'.join(slot_txt))]

    if slot_survey:
        vars.append(('${lienCreneau}', "<a href='{0}'>{0}</a>".format(slot_survey.url)))
    else:
        vars.append(('${lienCreneau}', _("Link improperly configured")))

    if global_survey:
        vars.append(('${lienGlobal}', "<a href='{0}'>{0}</a>".format(global_survey.url)))
    else:
        vars.append(('${lienGlobal}', _("Link improperly configured")))

    return multisub(vars, message_body)
