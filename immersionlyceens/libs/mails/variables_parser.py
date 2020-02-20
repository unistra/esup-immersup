import re
from django.urls import reverse
from immersionlyceens.apps.core.models import (
    UniversityYear, EvaluationFormLink, EvaluationType,
    GeneralSettings)


def multisub(subs, subject):
    """
    Simultaneously replace all vars in text
    """
    pattern = '|'.join('(%s)' % re.escape(p) for p, s in subs)
    substs = [s for p, s in subs]
    replace = lambda m: substs[m.lastindex - 1]
    return re.sub(pattern, replace, subject)


def parser(user, request, message_body, vars, **kwargs):
    slot = kwargs.get('slot')
    course = kwargs.get('course')
    registration = kwargs.get('registration')
    slot_survey = None
    global_survey = None

    if request:
        # The following won't work in 'commands'
        platform_url = request.build_absolute_uri(reverse('home'))
    else:
        try:
            platform_url_setting = GeneralSettings.objects.get(setting='PLATFORM_URL')
            platform_url = platform_url_setting.value
        except GeneralSettings.DoesNotExist:
            logger.warning("Warning : PLATFORM_URL not set in core General Settings")
            platform_url = "https://<plateforme immersion>"
            
    try:
        slot_survey = EvaluationFormLink.objects.get(
            evaluation_type__code='EVA_CRENEAU', active=True)
    except (EvaluationFormLink.DoesNotExist, EvaluationFormLink.MultipleObjectsReturned):
        pass

    try:
        global_survey = EvaluationFormLink.objects.get(
            evaluation_type__code='EVA_DISPOSITIF', active=True)
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
            ('${creneau.date}', slot.date.strftime('%d %B %Y')),
            ('${creneau.enseignants}', ','.join([
                "%s %s" % (t.first_name, t.last_name) for t in slot.teachers]
            )),
            ('${creneau.formation}', slot.training.label)
            ('${creneau.heuredebut}', slot.start_time)
            ('${creneau.heurefin}', slot.end_time)
            ('${creneau.info}', slot.additional_information)
            ('${creneau.salle}', slot.room)
            ('${creneau.type}', slot.course_type.label)
        ]
        # TODO avec les inscriptions aux créneaux
        # vars += [('${listeInscrits}',
        #     '\n'.join(["%s %s - %s" % (i.first_name, i.last_name, i.<etablissement>)
        #     for i in slot.liste_des_inscrits]))]

    # TODO avec les annulations d'inscriptions aux créneaux
    #if registration:
    #    vars += [('${motifAnnulation}', registration.cancel_type.label)]

    vars += [
        ('${nom}', user.last_name),
        ('${prenom}', user.first_name),
        ('${ens.nom}', user.last_name), # ! doublon
        ('${ens.prenom}', user.first_name), # ! doublon
        ('${referentlycee.nom}', user.last_name),  # ! doublon
        ('${referentlycee.prenom}', user.first_name), # ! doublon

        ('${identifiant}', user.get_cleaned_username()),
        ('${jourDestructionCptMin}', user.get_localized_destruction_date())
    ]
    
    if request:
        vars += [
            ('${lienValidation}', "<a href='{0}'>{0}</a>".format(request.build_absolute_uri(
                reverse('immersion:activate', kwargs={'hash':user.validation_string})))),
            ('${lienMotDePasse}', "<a href='{0}'>{0}</a>".format(request.build_absolute_uri(
                reverse('immersion:reset_password', kwargs={'hash':user.recovery_string}))))    
        ]
    else:
        vars += [
            ('${lienValidation}', "<a href='{0}{1}'>{0}{1}</a>".format(
                platform_url,
                reverse('immersion:activate', kwargs={'hash':user.validation_string}))),
            ('${lienMotDePasse}', "<a href='{0}{1}'>{0}{1}</a>".format(
                platform_url,
                reverse('immersion:reset_password', kwargs={'hash':user.recovery_string})))
        ]

    if slot_survey:
        vars.append(('${lienCreneau}', slot_survey.url))

    if global_survey:
        vars.append(('${lienGlobal}', global_survey.url))

    # TODO avec la fiche lycéen
    # if user == lyceen:
    #     vars.append(('${lycee}', ''))

    return multisub(vars, message_body)
