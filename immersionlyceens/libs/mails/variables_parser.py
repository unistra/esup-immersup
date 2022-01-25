import logging
from typing import Any, Dict, Optional, List, Union

from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import pgettext, gettext as _
from requests import Request

from immersionlyceens.apps.core.models import (EvaluationFormLink, Immersion, UniversityYear,
    MailTemplateVars, Slot, Course, ImmersionUser, Course, Visit, OffOfferEvent)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.libs.utils import get_general_setting, render_text

from django.utils.safestring import mark_safe
from django.utils.html import format_html

logger = logging.getLogger(__name__)


def parser(message_body, available_vars=None, user=None, request=None, **kwargs):
    return Parser.parser(
        message_body=message_body,
        available_vars=available_vars,
        user=user,
        request=request,
        **kwargs
    )


class Parser:
    @classmethod
    def parser(cls, message_body: str, available_vars: Optional[List[MailTemplateVars]],
               user: Optional[ImmersionUser] = None, request: Optional[Request] = None, **kwargs) -> str:
        context: Dict[str, Any] = cls.get_context(user, request, **kwargs)
        return render_text(template_data=message_body, data=context)

    @staticmethod
    def get_platform_url(request: Optional[Request]):
        platform_url: str = ""
        if request:
            # The following won't work in 'commands'
            platform_url = request.build_absolute_uri(reverse('home'))
        else:
            try:
                platform_url = get_general_setting("PLATFORM_URL")
            except (ValueError, NameError):
                logger.warning("Warning : PLATFORM_URL not set in core General Settings")
                platform_url = format_html("https://<plateforme immersion>")
        return platform_url

    @staticmethod
    def get_slot_survey() -> Optional[EvaluationFormLink]:
        try:
            return EvaluationFormLink.objects.get(evaluation_type__code='EVA_CRENEAU', active=True)
        except (EvaluationFormLink.DoesNotExist, EvaluationFormLink.MultipleObjectsReturned):
            return

    @staticmethod
    def get_global_survey() -> Optional[EvaluationFormLink]:
        try:
            return EvaluationFormLink.objects.get(evaluation_type__code='EVA_DISPOSITIF', active=True)
        except (EvaluationFormLink.DoesNotExist, EvaluationFormLink.MultipleObjectsReturned):
            return

    @staticmethod
    def get_year() -> Optional[UniversityYear]:
        try:
            return UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            return

    @staticmethod
    def get_course_context(course: Optional[Course]) -> Dict[str, Any]:
        if course:
            return {
                "cours": {
                    "libelle": course.label,
                    "formation": course.training.label,
                    "nbplaceslibre": course.free_seats(),
                }
            }
        return {}

    @staticmethod
    def get_event_context(event: Optional[OffOfferEvent]) -> Dict[str, Any]:
        if event:
            return {
                "evenement": {
                    "libelle": event.event_type.label,
                    "nbplaceslibre": event.free_seats(),
                }
            }
        return {}

    @staticmethod
    def get_visit_context(visit: Optional[Visit]) -> Dict[str, Any]:
        if visit:
            return {
                "visite": {
                    "libelle": visit.purpose,
                    "nbplaceslibre": visit.free_seats(),
                }
            }
        return {}

    @staticmethod
    def get_slot_context(slot: Optional[Slot]) -> Dict[str, Any]:
        def get_registered_students(slot):
            # Move to Slot model ?
            institution_label: str = _("Unknown home institution")
            registered_students: List[str] = []

            for registration in slot.immersions.filter(cancellation_type__isnull=True):
                if registration.student.is_high_school_student():
                    record = registration.student.get_high_school_student_record()
                    if record and record.highschool:
                        institution_label = f"{record.highschool.label} ({record.highschool.city})"
                elif registration.student.is_student():
                    record = registration.student.get_student_record()
                    if record:
                        uai_code, institution = record.home_institution()
                        institution_label = institution.label if institution else uai_code

                registered_students.append(
                    f"{registration.student.last_name} {registration.student.first_name} - {institution_label}"
                )

            return registered_students


        if slot:
            establishment = slot.get_establishment()
            structure = slot.get_structure()
            highschool = slot.get_highschool()
            registered_students = get_registered_students(slot)

            return {
                "creneau": {
                    "libelle": slot.get_label(),
                    "type": _(slot.get_type()),
                    "etablissement": establishment.label if establishment else "",
                    "lycee": f"{highschool.label} ({highschool.city})" if highschool else "",
                    "structure": structure.label if structure else "",
                    "batiment": slot.building.label if slot.building else "",
                    "campus": slot.campus.label if slot.campus else "",
                    "temoindistanciel": not slot.face_to_face,
                    "lien": format_html(slot.url) if slot.url else "",
                    "cours": {
                        'libelle': slot.get_label(),
                        'type': slot.course_type.full_label if slot.course_type else "",
                        'formation': slot.course.training.label
                    } if slot.course else {},
                    "evenement" : {
                        'libelle': slot.get_label(),
                        'description': slot.event.description,
                        'type': slot.event.event_type.label,
                    } if slot.event else {},
                    "visite": {
                        'libelle': slot.get_label(),
                    } if slot.visit else {},
                    "date": date_format(slot.date) if slot.date else "",
                    "intervenants": ",".join([f"{t.first_name} {t.last_name}" for t in slot.speakers.all()]),
                    "heuredebut": slot.start_time.strftime("%-Hh%M") if slot.start_time else "",
                    "heurefin": slot.end_time.strftime("%-Hh%M") if slot.end_time else "",
                    "info": slot.additional_information or pgettext("slot data", "None"),
                    "salle": slot.room,
                    "nbplaceslibres": slot.available_seats(),
                    "listeInscrits": "<br />".join(sorted(registered_students)) if registered_students else ""
                }
            }
        return {}

    @staticmethod
    def get_user_context(user: Optional[ImmersionUser]):
        if user:
            local_account = True

            if all([user.is_speaker(), user.establishment and user.establishment.data_source_plugin]):
                local_account = False

            context: Dict[str, Any] = {
                "nom": user.last_name,
                "prenom": user.first_name,
                "referentlycee": {
                    "lycee": f"{user.highschool.label} ({user.highschool.city}" if user.highschool else "",
                },
                "identifiant": user.get_cleaned_username(),
                "jourDestructionCptMin": user.get_localized_destruction_date(),
                "estetudiant": user.is_student(),
                "estlyceen": user.is_high_school_student(),
                "estvisiteur": user.is_visitor(),
                "estintervenant": user.is_speaker(),
                "estreflycee": user.is_high_school_manager(),
                "estrefstructure": user.is_structure_manager(),
                "intervenant_compte_local": local_account
            }

            if user.is_high_school_student():
                try:
                    context.update({
                        "lycee": user.high_school_student_record.highschool.label,
                        "datedenaissance": date_format(user.high_school_student_record.birth_date, 'd/m/Y'),
                    })
                except HighSchoolStudentRecord.DoesNotExist:
                    pass
            elif user.is_student():
                record = user.get_student_record()

                if record:
                    uai_code, institution = record.home_institution()
                    institution_label = institution.label if institution else uai_code

                    # TODO: maybe instead of lycee use a home_institution tpl var ???
                    context.update({
                        "lycee": institution_label,
                        "inscrit_datedenaissance": date_format(record.birth_date, 'd/m/Y')
                    })
            elif user.highschool:
                context.update({"lycee": user.highschool.label})

            return context
        return {}


    @staticmethod
    def get_cancellation_type_context(immersion: Optional[Immersion]) -> Dict[str, Any]:
        if immersion and immersion.cancellation_type:
            return {
                "motifAnnulation": immersion.cancellation_type.label
            }
        return {}

    @staticmethod
    def get_user_request_context(user: ImmersionUser, request: Any, platform_url: str) -> Dict[str, Any]:
        if user:
            if request:
                return {
                    "lienValidation": format_html('<a href="{0}">{0}</a>',
                        request.build_absolute_uri(
                            reverse('immersion:activate', kwargs={'hash': user.validation_string})
                        )
                    ),
                    "lienMotDePasse": format_html('<a href="{0}">{0}</a>',
                        request.build_absolute_uri(
                            reverse("immersion:reset_password", kwargs={'hash': user.recovery_string})
                        )
                    ),
                }
            else:
                return {
                    'lienValidation': format_html("<a href='{0}{1}'>{0}{1}</a>",
                        platform_url, reverse('immersion:activate', kwargs={'hash': user.validation_string})
                    ),
                    'lienMotDePasse': format_html("<a href='{0}{1}'>{0}{1}</a>",
                        platform_url, reverse('immersion:reset_password', kwargs={'hash': user.recovery_string})
                    )
                }

        return {}

    @staticmethod
    def get_slot_list_context(slot_list):
        if slot_list:
            slot_text: List[str] = [
                "* {date} ({start_time} - {end_time}) : {course} ({course_type})<br />Bâtiment {building}, salle {room}<br /> -> {speakers}".format(
                    date=date_format(s.date),
                    start_time=s.start_time.strftime("%-Hh%M"),
                    end_time=s.end_time.strftime("%-Hh%M"),
                    course=s.course.label if s.course else "",
                    course_type=s.course_type.label if s.course_type else "",
                    building=s.building,
                    room=s.room,
                    speakers=','.join([f"{t.first_name} {t.last_name}" for t in s.speakers.all()]),
                )
                for s in slot_list
            ]

            return {
                "creneaux": {
                    "liste": "<br /><br />".join(slot_text)
                }
            }
        return {}

    @staticmethod
    def get_slot_survey_context(slot_survey: Optional[EvaluationFormLink]) -> Dict[str, Any]:
        if slot_survey:
            return {"lienCreneau": f"<a href='{slot_survey.url}'>{slot_survey.url}</a>"}
        else:
            return {"lienCreneau": _("Link improperly configured")}

    @staticmethod
    def get_global_survey_context(global_survey: Optional[EvaluationFormLink]) -> Dict[str, Any]:
        if global_survey:
            return {"lienGlobal": f"<a href='{global_survey.url}'>{global_survey.url}</a>"}
        else:
            return {"lienGlobal": _("Link improperly configured")}

    @classmethod
    def get_context(cls, user: Optional[ImmersionUser], request: Optional[Request] = None, **kwargs) -> Dict[str, Any]:
        slot: Optional[Slot] = kwargs.get('slot')
        slot_list: Optional[List[Slot]] = kwargs.get('slot_list')
        course: Optional[Course] = kwargs.get('course')
        visit: Optional[Visit] = kwargs.get('visit')
        event: Optional[OffOfferEvent] = kwargs.get('event')
        immersion: Optional[Immersion] = kwargs.get('immersion')

        slot_survey: Optional[EvaluationFormLink] = cls.get_slot_survey()
        global_survey: Optional[EvaluationFormLink] = cls.get_global_survey()
        platform_url: str = cls.get_platform_url(request)
        year: Optional[UniversityYear] = cls.get_year()

        context: Dict[str, Any] = {
            "annee": year.label if year else _("not set"),
            "urlPlateforme": platform_url,
        }

        context.update(cls.get_course_context(course))
        context.update(cls.get_visit_context(visit))
        context.update(cls.get_event_context(event))
        context.update(cls.get_slot_context(slot))

        context.update(cls.get_cancellation_type_context(immersion))

        context.update(cls.get_user_context(user))
        context.update(cls.get_user_request_context(user, request, platform_url))

        context.update(cls.get_slot_list_context(slot_list))
        context.update(cls.get_slot_survey_context(slot_survey))
        context.update(cls.get_global_survey_context(global_survey))

        context.update()
        return context

    @staticmethod
    def get_registered_students(slot: Optional[Slot]) -> Dict[str, Any]:
        if slot:
            institution_label: str = _("Unknown home institution")
            registered_students: List[str] = []
            registered: Immersion
            for registration in Immersion.objects.filter(slot=slot, cancellation_type__isnull=True):
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
                    f"{registration.student.last_name} {registration.student.first_name} - {institution_label}"
                )

            return registered_students

        return []


