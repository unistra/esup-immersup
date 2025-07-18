import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Union

from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, time_format
from django.utils.translation import pgettext, gettext as _

from requests import Request

from immersionlyceens.apps.core.models import (
    EvaluationFormLink, GeneralSettings, Immersion, UniversityYear, MailTemplateVars,
    Slot, ImmersionUser, ImmersionGroupRecord, Course, OffOfferEvent
)
from immersionlyceens.libs.utils import get_general_setting, render_text

from django.utils.html import format_html

logger = logging.getLogger(__name__)


def parser(message_body, available_vars=None, user=None, group=None, recipient=None, request=None, **kwargs):
    """
    :param message_body: the message body
    :param available_vars: variables that can be used in this template
    :param user: the ImmersionUser the mail will be sent to
    :param group: the ImmersionGroupRecord the mail will be sent to
    :param recipient: the recipient type, 'user' or 'group'
    :param request: request
    :return: parsed mail template
    """

    return Parser.parser(
        message_body=message_body,
        available_vars=available_vars,
        user=user,
        group=group,
        recipient=recipient,
        request=request,
        **kwargs
    )


def parser_faker(message_body, context_params, available_vars=None, user=None, group=None, request=None, **kwargs):
    return ParserFaker.parser(
        message_body=message_body,
        context_params=context_params,
        available_vars=available_vars,
        user=user,
        group=group,
        request=request,
        **kwargs
    )


class ParserFaker:
    @classmethod
    def parser(cls, message_body: str, available_vars: Optional[List[MailTemplateVars]], context_params: Dict[str, Any],
               user: Optional[ImmersionUser] = None, group: Optional[ImmersionGroupRecord] = None,
               request: Optional[Request] = None, context: Optional[Dict] = None, **kwargs) -> str:

        context: Dict[str, Any] = cls.get_context(request, **context_params)
        return render_text(template_data=message_body, data=context)

    @classmethod
    def add_tooltip(cls, var_name: str, content: str):
        text: str = '<span style="border-bottom: 1px dotted gray;">' + str(content) + '<span title="' + str(var_name)
        text += '" class="help help-tooltip help-icon"></span></span>'
        return format_html(text)

    @classmethod
    def get_context(cls, request, user_is, slot_type, local_account, place, recipient, educonnect):
        today: datetime = timezone.localdate()
        formatted_today: str = today.strftime("%d/%m/%Y")

        cancellation_date: str = date_format(timezone.now() - timedelta(hours=24), "j F - G\\hi")
        registration_date: str = date_format(timezone.now() - timedelta(hours=48), "j F - G\\hi")

        speakers: List[str] = ["Henri Matisse", "Hans Arp", "Alexander Calder"]

        slot_list: List[str] = [
            f"* {formatted_today} (10h00 - 12h00) : Mon cours (TD)<br>Bâtiment principal, salle 1605<br> -> {', '.join(speakers)}",
            f"* {formatted_today} (12h00 - 14h00) : Mon cours 2 (CM)<br>Bâtiment secondaire, salle 309<br> -> {', '.join(speakers)}",
            f"* {formatted_today} (15h30 - 17h30) : Mon cours (TD)<br>Bâtiment principal, salle 170<br> -> {', '.join(speakers)}",
        ]

        attestations: List[str] = [
            "* Attestation d'assurance - %s" % date_format(today + timedelta(days=10), "j F Y"),
            "* Autorisation parentale - %s" % date_format(today + timedelta(days=30), "j F Y")
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
            "justificatifs_expires": cls.add_tooltip("justificatifs_expires", "<br>".join(attestations)),
            "educonnect": educonnect,
        })
        context[user_is] = True

        # a registered high school student / student / visitor
        context.update({
            "inscrit": {
                "prenom": cls.add_tooltip("inscrit.prenom", "Jeanne"),
                "nom": cls.add_tooltip("inscrit.nom", "Jacques"),
                "email": cls.add_tooltip("inscrit.email", "jj@domain.tld"),
                "aDeclareHandicap": True,
            }
        })

        # course
        context.update({
            "cours": {
                "libelle": cls.add_tooltip("cours.libelle", "Cours n°1"),
                "formation": cls.add_tooltip("cours.formation", "Formation n°2"),
                "nbplaceslibre": 25,
                "type": "TD"
            }
        })

        # event
        context.update({
            "evenement": {
                "type": cls.add_tooltip("evenement.type", "Conférence"),
                "libelle": cls.add_tooltip("evenement.libelle", _("Event N°1")),
                "nbplaceslibre": 27
            }
        })

        # slot
        context.update({
            "creneau": {
                "libelle": cls.add_tooltip("creneau.libelle", "Cours n°2"),
                "estuncours": False,
                "estunevenement": False,
                "etablissement": cls.add_tooltip("creneau.etablissement", "Mon Établissement"),
                "lycee": cls.add_tooltip("creneau.lycee", "Lycée Frida Kahlo (New York)"),
                "structure": cls.add_tooltip("creneau.structure", "Ma Structure"),
                "batiment": {
                    "libelle": cls.add_tooltip("creneau.batiment.libelle", "Musée d'art moderne (MoMa)"),
                    "lien": cls.add_tooltip(
                        "creneau.batiment.lien",
                        format_html(f"<a href='https://www.moma.org/'>https://www.moma.org/</a>")
                    ),
                },
                "campus": {
                    "libelle": cls.add_tooltip("creneau.campus.libelle", "Campus principal"),
                    "ville": cls.add_tooltip("creneau.campus.ville", "Columbia"),
                },
                "temoindistanciel": place == Slot.REMOTE,
                "lien": cls.add_tooltip(
                    "creneau.lien",
                    format_html(f"<a href='https://unistra.fr/'>https://unistra.fr/</a>")
                ),
                "cours": {
                    "libelle": cls.add_tooltip("creneau.cours.libelle", "Mon cours"),
                    "type": cls.add_tooltip("creneau.cours.type", "TD"),
                    "formation": cls.add_tooltip("creneau.cours.formation", "Ma formation"),
                },
                "evenement": {
                    "libelle": cls.add_tooltip("creneau.evenement.libelle", _("My event")),
                    "description": cls.add_tooltip("creneau.evenement.description", _("My event description")),
                    "type": cls.add_tooltip("creneau.evenement.type", "Conférence")
                },
                "date": cls.add_tooltip("creneau.date", formatted_today),
                "limite_annulation": cls.add_tooltip("creneau.limite_annulation", cancellation_date),
                "limite_inscription": cls.add_tooltip("creneau.limite_inscription", registration_date),
                "intervenants": cls.add_tooltip("creneau.intervenants", ", ".join(speakers)),
                "heuredebut": cls.add_tooltip("creneau.heuredebut", "10h00"),
                "heurefin": cls.add_tooltip("creneau.heurefin", "12h00"),
                "info": cls.add_tooltip("creneau.info", "Ceci est une information sur ce créneau"),
                "salle": cls.add_tooltip("creneau.salle", "Salle 102"),
                "nbplaceslibres": 25,
                "listeInscrits": format_html(
                    cls.add_tooltip("creneau.listeInscrits", "Alexandre COMBEAU<br>")
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
                "liste": cls.add_tooltip("creneaux.liste", "<br><br>".join(slot_list))
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

        # Group data
        context.update({
            "cohorte": {
                "etablissementInscrit": cls.add_tooltip(
                    "cohorte.etablissementInscrit",
                    "École Européenne de Strasbourg"
                ),
                "nbEleves": cls.add_tooltip("cohorte.nbEleves", "12"),
                "nbAccompagnateurs": cls.add_tooltip("cohorte.nbEleves", "2"),
                "nbPlaces": cls.add_tooltip("cohorte.nbEleves", "14"),
                "fichierJoint": cls.add_tooltip(
                    "cohorte.fichierJoint",
                    "<a href=''>Composition du groupe.pdf</a>"
                ),
                "commentaires": cls.add_tooltip(
                    "cohorte.fichierJoint",
                    "Le groupe viendra en bus, merci de prévoir un emplacement pour le stationnement."
                ),
            }
        })

        # Recipient data
        context.update({
            "destinataire": {
                "estCohorte": recipient == 'group',
                "estIndividu": recipient == 'user',
            }
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
    def get_slot_context(slot: Optional[Slot]) -> Dict[str, Any]:
        def get_registered_students(slot):
            # Move to Slot model ?
            institution_label: str = _("Unknown home institution")
            registered_students: List[str] = []

            for registration in slot.immersions.filter(cancellation_type__isnull=True):
                has_disability = ""
                record = None

                if registration.student.is_high_school_student():
                    record = registration.student.get_high_school_student_record()
                    if record and record.highschool:
                        institution_label = f"{record.highschool.label} ({record.highschool.city})"
                elif registration.student.is_student():
                    record = registration.student.get_student_record()
                    if record:
                        institution_label = record.institution.label if record.institution else record.uai_code
                elif registration.student.is_visitor():
                    record = registration.student.get_visitor_record()

                if record and record.disability:
                    has_disability = "(%s)" % _("disabled person")

                registered_students.append(" - ".join(
                    list(filter(lambda x:x, [
                        registration.student.last_name,
                        " ".join([registration.student.first_name, has_disability]),
                        registration.student.email,
                        institution_label
                    ])))
                )

            return registered_students

        def get_registered_groups(slot):
            registered_groups: List[str] = []
            for group_reg in slot.group_immersions.filter(cancellation_type__isnull=True):
                registered_group = _("Group : %s students, %s guides - %s") % (
                    group_reg.students_count,
                    group_reg.guides_count,
                    group_reg.highschool.label,
                )

                if group_reg.emails:
                    registered_group += "<br>" + _("Contact(s) : %s") % group_reg.emails

                if group_reg.file:
                    registered_group += f"<br> {_('File')} : " + format_html(
                        '<a href="{0}">{1}</a>',
                        reverse('group_document', kwargs={'immersion_group_id': group_reg.id}),
                        group_reg.file.name
                    )

                if group_reg.comments:
                    registered_group += f"<br> {_('Comments')} : " + format_html(group_reg.comments)

                registered_groups.append(registered_group)

            return registered_groups

        if slot:
            establishment = slot.get_establishment()
            structure = slot.get_structure()
            highschool = slot.get_highschool()
            registered_students = get_registered_students(slot)
            registered_groups = get_registered_groups(slot)

            cancellation_limit = date_format(timezone.localtime(slot.cancellation_limit_date), "j F - G\\hi") \
                if slot.cancellation_limit_date else ""

            registration_limit = date_format(timezone.localtime(slot.registration_limit_date), "j F - G\\hi") \
                if slot.registration_limit_date else ""

            return {
                "creneau": {
                    "libelle": slot.get_label(),
                    "estuncours": slot.is_course(),
                    "estunevenement": slot.is_event(),
                    "etablissement": establishment.label if establishment else "",
                    "lycee": f"{highschool.label} ({highschool.city})" if highschool else "",
                    "structure": structure.label if structure else "",
                    "batiment": {
                        'libelle': slot.building.label,
                        'lien': format_html(f"<a href='{slot.building.url}'>{slot.building.url}</a>"),
                    } if slot.building else {},
                    "campus": {
                        'libelle': slot.campus.label if slot.campus else "",
                        'ville': slot.campus.city if slot.campus and slot.campus.city else "",
                    },
                    "temoindistanciel": slot.place == Slot.REMOTE,
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
                    "date": date_format(slot.date) if slot.date else "",
                    "limite_annulation": cancellation_limit,
                    "limite_inscription": registration_limit,
                    "intervenants": ",".join([f"{t.first_name} {t.last_name}" for t in slot.speakers.all()]),
                    "heuredebut": slot.start_time.strftime("%-Hh%M") if slot.start_time else "",
                    "heurefin": slot.end_time.strftime("%-Hh%M") if slot.end_time else "",
                    "info": slot.additional_information or pgettext("slot data", "None"),
                    "salle": slot.room,
                    "nbplaceslibres": slot.available_seats(),
                    "listeInscrits": format_html("<br>".join(sorted(registered_students)) if registered_students else ""),
                    "listeCohortes": format_html("<br><br>".join(registered_groups) if registered_groups else ""),
                    "limite_annulation_depassee": slot.is_cancellation_limit_date_due(),
                    "limite_inscription_depassee": slot.is_registration_limit_date_due(),
                }
            }
        return {}

    @staticmethod
    def get_user_context(user: Optional[ImmersionUser]):
        if user:
            try:
                agent_federation = GeneralSettings.get_setting("ACTIVATE_FEDERATION_AGENT")
            except:
                agent_federation = False

            local_account = not any([
                user.is_student(),
                user.establishment and user.establishment.data_source_plugin,
                agent_federation and user.highschool and user.highschool.uses_agent_federation
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
                record = user.get_high_school_student_record()

                if record:
                    attestations_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")

                    attestations = [f"* {a.attestation.label} - {date_format(a.validity_date, 'j F Y')}"
                        for a in record.attestation.filter(
                            archive=False,
                            requires_validity_date=True,
                            validity_date__lte=timezone.localdate() + timedelta(days=attestations_delay)
                        )
                    ]

                    context.update({
                        "lycee": record.highschool.label if record and record.highschool else _("unknown"),
                        "educonnect": record.highschool.uses_student_federation if record and record.highschool else False,
                        "datedenaissance": date_format(record.birth_date, 'd/m/Y') if record.birth_date else "",
                        "justificatifs_expires": format_html("<br>".join(attestations))
                    })

            elif user.is_student():
                record = user.get_student_record()

                if record:
                    institution_label = record.institution.label if record.institution else record.uai_code

                    # TODO: maybe instead of lycee use a home_institution tpl var ???
                    context.update({
                        "lycee": institution_label,
                        "inscrit_datedenaissance": date_format(record.birth_date, 'd/m/Y') if record.birth_date else ""
                    })
            elif user.is_visitor():
                record = user.get_visitor_record()

                if record:
                    attestations_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")

                    attestations = [f"* {a.attestation.label} - {date_format(a.validity_date, 'j F Y')}"
                        for a in record.attestation.filter(
                            archive=False,
                            requires_validity_date=True,
                            validity_date__lte=timezone.localdate() + timedelta(days=attestations_delay)
                        )
                    ]

                    context.update({
                        "justificatifs_expires": format_html("<br>".join(attestations))
                    })

            elif user.highschool:
                context.update({"lycee": user.highschool.label})

            return context
        return {}

    @staticmethod
    def get_registrant_context(registrant: ImmersionUser):
        record = (
            registrant.get_high_school_student_record()
            or registrant.get_student_record()
            or registrant.get_visitor_record()
        )

        return {
            "inscrit": {
                "prenom": registrant.first_name,
                "nom": registrant.last_name,
                "email": registrant.email,
                "aDeclareHandicap": record.disability if record else False,
            }
        }

    @staticmethod
    def get_recipient_context(recipient):
        return {
            "destinataire": {
                "estCohorte": recipient == "group",
                "estIndividu": recipient == "user",
            }
        }
    @staticmethod
    def get_group_context(immersion_group: Optional[ImmersionGroupRecord]):
        if immersion_group:
            return {
                "cohorte": {
                    "etablissementInscrit": immersion_group.highschool.label,
                    "nbEleves": immersion_group.students_count,
                    "nbAccompagnateurs": immersion_group.guides_count,
                    "nbPlaces": (immersion_group.students_count or 0) + (immersion_group.guides_count or 0),
                    "fichierJoint": format_html('<a href="{0}">{1}</a>', reverse(
                        'group_document',
                        kwargs={'immersion_group_id': immersion_group.id}
                    ), immersion_group.file.name) if immersion_group.file else "",
                    "commentaires": immersion_group.comments or _("None")
                }
            }

    @staticmethod
    def get_cancellation_type_context(immersion: Optional[Immersion], group_immersion: Optional[ImmersionGroupRecord]) -> Dict[str, Any]:
        if immersion and immersion.cancellation_type:
            return {
                "motifAnnulation": immersion.cancellation_type.label
            }
        elif group_immersion and group_immersion.cancellation_type:
            return {
                "motifAnnulation": group_immersion.cancellation_type.label
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
                if slot.place == Slot.FACE_TO_FACE:
                    place = "{0} : {1}, ".format(_("campus"), slot.campus.label) if slot.campus else ""
                    place += "{0} : {1}, ".format(_("building"), slot.building.label) if slot.building else ""
                    place += "{0} : {1}".format(_("room"), slot.room) if slot.room else ""
                elif slot.place == Slot.REMOTE:
                    place = _("remote slot")
                elif slot.place == Slot.OUTSIDE:
                    place = slot.room

                if slot.is_event():
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
        event: Optional[OffOfferEvent] = kwargs.get('event')
        immersion: Optional[Immersion] = kwargs.get('immersion')
        group: Optional[ImmersionGroupRecord] = kwargs.get('group')
        link_validation_string: Optional[str] = kwargs.get('link_validation_string', '')
        link_source_user: Optional[str] = kwargs.get('link_source_user', '')
        recipient: Union[List[str], str] = kwargs.get('recipient', 'user')
        registrant: Optional[ImmersionUser] = kwargs.get('registrant')

        slot_survey: Optional[EvaluationFormLink] = cls.get_slot_survey()
        global_survey: Optional[EvaluationFormLink] = cls.get_global_survey()
        platform_url: str = cls.get_platform_url(request)
        year: Optional[UniversityYear] = cls.get_year()

        context: Dict[str, Any] = {
            "annee": year.label if year else _("not set"),
            "urlPlateforme": platform_url,
        }

        if group:
            context.update(cls.get_group_context(group))

        context.update(cls.get_course_context(course))
        context.update(cls.get_event_context(event))
        context.update(cls.get_slot_context(slot))

        context.update(cls.get_recipient_context(recipient))

        if registrant:
            context.update(cls.get_registrant_context(registrant))

        context.update(cls.get_cancellation_type_context(immersion, group))

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
