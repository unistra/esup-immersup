import logging
from datetime import datetime
from typing import Any, Dict, Optional, List, Union

from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, time_format
from django.utils.translation import pgettext, gettext as _

from requests import Request

from immersionlyceens.apps.core.models import (EvaluationFormLink, Immersion, UniversityYear,
    MailTemplateVars, Slot, ImmersionUser, Course, Visit, OffOfferEvent)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
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


def parser_faker(message_body, context_params, available_vars=None, user=None, request=None, **kwargs):
    return ParserFaker.parser(
        message_body=message_body,
        context_params=context_params,
        available_vars=available_vars,
        user=user,
        request=request,
        **kwargs
    )


class ParserFaker:
    @classmethod
    def parser(cls, message_body: str, available_vars: Optional[List[MailTemplateVars]], context_params: Dict[str, Any],
               user: Optional[ImmersionUser] = None, request: Optional[Request] = None, **kwargs) -> str:

        context: Dict[str, Any] = cls.get_context(request, **context_params)
        return render_text(template_data=message_body, data=context)

    @classmethod
    def add_tooltip(cls, var_name: str, content: str):
        text: str = '<span style="border-bottom: 1px dotted gray;">' + str(content) + '<span title="' + str(var_name)
        text += '" class="help help-tooltip help-icon"></span></span>'
        return format_html(text)

    @classmethod
    def get_context(cls, request, user_is, slot_type, local_account, remote):
        today: str = datetime.today().strftime("%d/%m/%Y")

        speakers: List[str] = ["Henri Matisse", "Hans Arp", "Alexander Calder"]

        slot_list: List[str] = [
            f"* {today} (10h00 - 12h00) : Mon cours (TD)<br />Bâtiment principal, salle 1605<br /> -> {', '.join(speakers)}",
            f"* {today} (12h00 - 14h00) : Mon cours 2 (CM)<br />Bâtiment secondaire, salle 309<br /> -> {', '.join(speakers)}",
            f"* {today} (15h30 - 17h30) : Mon cours (TD)<br />Bâtiment principal, salle 170<br /> -> {', '.join(speakers)}",
        ]

        year = Parser.get_year()
        platform_url = Parser.get_platform_url(request)
        context = {
            "annee": cls.add_tooltip("annee", year.label if year else _("not set")),
            "platform_url": cls.add_tooltip("platform_url", platform_url),
        }

        # user
        context.update({
            "prenom": cls.add_tooltip("prenom", "Dominique"),
            "nom": cls.add_tooltip("nom", "MARTIN"),
            "identifiant": cls.add_tooltip("identifiant", "d.martin@service-plublic.fr"),
            "jourDestructionCptMin": cls.add_tooltip("jourDestructionCptMin", "17-10-2022"),
            "estetudiant": False,
            "estlyceen": False,
            "estvisiteur": False,
            "estintervenant": False,
            "estreflycee": False,
            "estrefstructure": False,
            "utilisateurcomptelocal": local_account,
            "lycee": cls.add_tooltip("lycee", "Lycée Georges Brassens (Saint-Gély-du-Fesc)"),
            "datedenaissance": cls.add_tooltip("datedenaissance", "14-07-1980"),
            "inscrit_datedenaissance": cls.add_tooltip("inscrit_datedenaissance", "14-07-1980"),
        })
        context[user_is] = True

        # course
        context.update({
            "cours": {
                "libelle": cls.add_tooltip("cours.libelle", "Cours n°1"),
                "formation": cls.add_tooltip("cours.formation", "Formation n°2"),
                "nbplaceslibre": 25,
                "type": "TD"
            }
        })

        # visit
        context.update({
            "visite": {
                "libelle": cls.add_tooltip("visite.libelle", "Visite N°1"),
                "nbplaceslibre": 35
            }
        })

        # event
        context.update({
            "evenement": {
                "type": cls.add_tooltip("evenement.type", "Conférence"),
                "libelle": cls.add_tooltip("evenement.libelle", "Événement N°1"),
                "nbplaceslibre": 27
            }
        })

        # slot
        context.update({
            "creneau": {
                "libelle": cls.add_tooltip("creneau.libelle", "Cours n°2"),
                "estuncours": False,
                "estunevisite": False,
                "estunevenement": False,
                "etablissement": cls.add_tooltip("creneau.etablissement", "Mon Super Établissement"),
                "lycee": cls.add_tooltip("creneau.lycee", "Lycée Frida Kahlo (New York)"),
                "structure": cls.add_tooltip("creneau.structure", "Ma Super Structure"),
                "batiment": {
                    "libelle": cls.add_tooltip("creneau.batiment.libelle", "Musée d'art moderne (MoMa)"),
                    "lien": cls.add_tooltip(
                        "creneau.batiment.lien",
                        format_html(f"<a href='https://www.moma.org/'>https://www.moma.org/</a>")
                    ),
                },
                "campus": cls.add_tooltip("creneau.campus", "Université de Columbia"),
                "temoindistanciel": remote,
                "lien": cls.add_tooltip(
                    "creneau.lien",
                    format_html(f"<a href='https://unistra.fr/'>https://unistra.fr/</a>")
                ),
                "cours": {
                    "libelle": cls.add_tooltip("creneau.cours.libelle", "Mon cours"),
                    "type": cls.add_tooltip("creneau.cours.type", "TD"),
                    "formation": cls.add_tooltip("creneau.cours.formation", "Ma super formation"),
                },
                "evenement": {
                    "libelle": cls.add_tooltip("creneau.evenement.libelle", "Mon événement"),
                    "description": cls.add_tooltip("creneau.evenement.description", "Description de mon événement"),
                    "type": cls.add_tooltip("creneau.evenement.type", "Conférence")
                },
                "visite": {
                    "libelle": cls.add_tooltip("creneau.visite.libelle", "Ma super visite"),
                },
                "date": cls.add_tooltip("creneau.date", today),
                "limite_annulation": cls.add_tooltip("creneau.limite_annulation", today - datetime.timedelta(hours=24)),
                "intervenants": cls.add_tooltip("creneau.intervenants", ", ".join(speakers)),
                "heuredebut": cls.add_tooltip("creneau.heuredebut", "10h00"),
                "heurefin": cls.add_tooltip("creneau.heurefin", "12h00"),
                "info": cls.add_tooltip("creneau.info", "Ceci est une information sur ce créneau"),
                "salle": cls.add_tooltip("creneau.salle", "Salle 102"),
                "nbplaceslibres": 25,
                "listeInscrits": format_html(
                    cls.add_tooltip("creneau.listeInscrits", "Alexandre COMBEAU<br />")
                ),
            }
        })
        context["creneau"][slot_type] = True
        context.update({
            "motifAnnulation": cls.add_tooltip("motifAnnulation", "Annulation pour cause d'un passage de bisons sur la route")
        })

        # User (request)
        context.update({
            "lienValidation": cls.add_tooltip(
                "lienValidation",
                '<a href="https://github.com/unistra/esup-immersup#lien_validation">https://github.com/unistra/esup-immersup#lien_validation</a>'
            ),
            "lienMotDePasse": cls.add_tooltip(
                "lienMotDePasse",
                '<a href="https://github.com/unistra/esup-immersup#lien_mot_de_passe">https://github.com/unistra/esup-immersup#lien_mot_de_passe</a>'
            ),
            "lienDemandeur": cls.add_tooltip(
                "lienDemandeur",
                '<a href="https://github.com/unistra/esup-immersup#lien_demandeur">https://github.com/unistra/esup-immersup#lien_demandeur</a>'
            ),
            "lienAssociationComptes": cls.add_tooltip(
                "lienAssociationComptes",
                '<a href="https://github.com/unistra/esup-immersup#lien_association_comptes">https://github.com/unistra/esup-immersup#lien_association_comptes</a>'
            ),
        })

        # slot list
        context.update({
            "creneaux": {
                "liste": cls.add_tooltip("creneaux.liste", "<br /><br />".join(slot_list))
            }
        })

        # slot survey and global survey
        context.update({
            "lienCreneau": cls.add_tooltip(
                "lienCreneau",
                '<a href="https://github.com/unistra/esup-immersup#lienCreneau">https://github.com/unistra/esup-immersup#lienCreneau</a>'),
            "lienGlobal": cls.add_tooltip(
                "lienGlobal",
                '<a href="https://github.com/unistra/esup-immersup#lienGlobal">https://github.com/unistra/esup-immersup#lienGlobal</a>'
            ),
        })

        return context


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
            url = request.build_absolute_uri(reverse('home'))
            platform_url = format_html(f"<a href='{url}'>{url}</a>")
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

            cancellation_limit = date_format(timezone.localtime(slot.cancellation_limit_date), "j F - G\hi") \
                if slot.cancellation_limit_date else ""

            return {
                "creneau": {
                    "libelle": slot.get_label(),
                    "estuncours": slot.is_course(),
                    "estunevisite": slot.is_visit(),
                    "estunevenement": slot.is_event(),
                    "etablissement": establishment.label if establishment else "",
                    "lycee": f"{highschool.label} ({highschool.city})" if highschool else "",
                    "structure": structure.label if structure else "",
                    "batiment": {
                        'libelle': slot.building.label,
                        'lien': format_html(f"<a href='{slot.building.url}'>{slot.building.url}</a>"),
                    } if slot.building else {},
                    "campus": slot.campus.label if slot.campus else "",
                    "temoindistanciel": not slot.face_to_face,
                    "lien": format_html(f"<a href='{slot.url}'>{slot.url}</a>") if slot.url else "",
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
                    "limite_annulation": cancellation_limit,
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
            local_account = not any([
                user.is_student(),
                user.establishment and user.establishment.data_source_plugin
            ])

            context: Dict[str, Any] = {
                "nom": user.last_name,
                "prenom": user.first_name,
                "identifiant": user.get_cleaned_username(),
                "jourDestructionCptMin": user.get_localized_destruction_date(),
                "estetudiant": user.is_student(),
                "estlyceen": user.is_high_school_student(),
                "estvisiteur": user.is_visitor(),
                "estintervenant": user.is_speaker(),
                "estreflycee": user.is_high_school_manager(),
                "estrefstructure": user.is_structure_manager(),
                "utilisateurcomptelocal": local_account
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
            slot_text = []

            for slot in slot_list:
                if slot.face_to_face:
                    place = "{0} : {1}, ".format(_("campus"), slot.campus.label) if slot.campus else ""
                    place += "{0} : {1}, ".format(_("building"), slot.building.label) if slot.building else ""
                    place += "{0} : {1}".format(_("room"), slot.room) if slot.room else ""
                else:
                    place = _("remote slot")

                if slot.is_visit():
                    slot_type = _("visit")
                elif slot.is_event():
                    slot_type = _("event")
                else:
                    slot_type = _("course")

                slot_text.append(
                    "* {slot_type}{high_school} : {date} ({start_time} - {end_time}) : {label} {course_type}<br>&rarr; {place}<br>&rarr; {speakers}".format(
                        slot_type=slot_type,
                        high_school=
                            ", {0} {1}, {2}".format(
                                _('high school'), slot.get_highschool().label, slot.get_highschool().city
                            )
                            if slot.get_highschool() else "",
                        date=date_format(slot.date),
                        start_time=slot.start_time.strftime("%-Hh%M"),
                        end_time=slot.end_time.strftime("%-Hh%M"),
                        label=slot.get_label(),
                        course_type=f"({slot.course_type.label})" if slot.course_type else "",
                        place=place,
                        speakers=','.join([f"{t.first_name} {t.last_name}" for t in slot.speakers.all()]),
                    )
                )

            return {
                "creneaux": {
                    "liste": format_html("<br><br>".join(slot_text))
                }
            }
        return {}

    @staticmethod
    def get_slot_survey_context(slot_survey: Optional[EvaluationFormLink]) -> Dict[str, Any]:
        if slot_survey:
            return {"lienCreneau": format_html(f"<a href='{slot_survey.url}'>{slot_survey.url}</a>")}
        else:
            return {"lienCreneau": _("Link improperly configured")}

    @staticmethod
    def get_global_survey_context(global_survey: Optional[EvaluationFormLink]) -> Dict[str, Any]:
        if global_survey:
            return {"lienGlobal": format_html(f"<a href='{global_survey.url}'>{global_survey.url}</a>")}
        else:
            return {"lienGlobal": _("Link improperly configured")}

    @staticmethod
    def get_accounts_link_context(
            request: Any, platform_url: str, link_validation_string: str, link_source_user: str
    ) -> Dict[str, Any]:

        link_dict = {
            "lienDemandeur": link_source_user
        }

        if request:
            link_dict["lienAssociationComptes"] = format_html('<a href="{0}">{0}</a>',
                request.build_absolute_uri(
                    reverse("immersion:link", kwargs={'hash': link_validation_string})
                )
            )
        else:
            link_dict["lienAssociationComptes"] = format_html('<a href="{0}{1}">{0}{1}</a>',
                platform_url,
                reverse("immersion:link", kwargs={'hash': link_validation_string})
            )

        return link_dict


    @classmethod
    def get_context(cls, user: Optional[ImmersionUser], request: Optional[Request] = None, **kwargs) -> Dict[str, Any]:
        slot: Optional[Slot] = kwargs.get('slot')
        slot_list: Optional[List[Slot]] = kwargs.get('slot_list')
        course: Optional[Course] = kwargs.get('course')
        visit: Optional[Visit] = kwargs.get('visit')
        event: Optional[OffOfferEvent] = kwargs.get('event')
        immersion: Optional[Immersion] = kwargs.get('immersion')
        link_validation_string: Optional[str] = kwargs.get('link_validation_string', '')
        link_source_user: Optional[str] = kwargs.get('link_source_user', '')

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

        if link_validation_string and link_source_user:
            context.update(cls.get_accounts_link_context(
                request, platform_url, link_validation_string, link_source_user)
            )

        context.update(cls.get_slot_list_context(slot_list))
        context.update(cls.get_slot_survey_context(slot_survey))
        context.update(cls.get_global_survey_context(global_survey))

        context.update()
        return context
