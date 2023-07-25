
from django.db import migrations

def load_mail_template_vars(apps, schema_editor):
    MailTemplateVars = apps.get_model('core', 'MailTemplateVars')

    data = {
        '{{ creneau.limite_annulation_depassee }}': 'Date limite d\'annulation dépassée',
        '{{ creneau.limite_inscription_depassee }}': 'Date limite d\'inscription dépassée',
    }

    for code, description in data.items():
        if not MailTemplateVars.objects.filter(code=code).exists():
            MailTemplateVars.objects.create(code=code, description=description)


def load_mail_templates(apps, schema_editor):
    MailTemplate = apps.get_model('core', 'MailTemplate')
    MailTemplateVars = apps.get_model('core', 'MailTemplateVars')

    data = {
        'IMMERSION_RAPPEL_INT': {
            'label': 'Mail de rappel de participation à un créneau pour les intervenants',
            'description': 'Mail envoyé à un intervenant n jours avant le créneau',
            'subject': 'Rappel : votre cours en immersion',
            'body': "<p></p><p>Bonjour {{ prenom }} {{ nom }}, </p><p>Vous avez été désigné comme intervenant sur {% if creneau.estuncours %}le cours{% elif creneau.estunevisite %}la visite au {{ creneau.lycee }}{% elif creneau.estunevenement %}l' évènement{% endif %} organisé par {% if creneau.lycee %}le lycée {{ creneau.lycee }}{% else %}l'établissement {{ creneau.etablissement }}{% if creneau.structure %} - {{ creneau.structure }}{% endif %}{% endif %}.<br></p>{% if creneau.estuncours %}Formation : {{ creneau.cours.formation }}<br>Cours : {{ creneau.cours.libelle }}<br>Type : {{ creneau.cours.type }}<br>{% elif creneau.estunevisite %}Objet de la visite&nbsp; : {{ creneau.visite.libelle }}.<br>{% elif creneau.estunevenement %}Type d'évènement : {{ creneau.evenement.type }}<br>Intitulé : {{ creneau.evenement.libelle }}<br>Description : {{ creneau.evenement.description }}{% endif %}<br><br>Ce créneau aura lieu le {{ creneau.date }} de {{ creneau.heuredebut }} à {{ creneau.heurefin }}.<br><br>{% if creneau.temoindistanciel %}Il aura lieu en distanciel sur le lien suivant : {{ creneau.lien }}{% else %}<br>{% if creneau.campus %}Campus : {{ creneau.campus }}{% endif %}<br>{% if creneau.batiment.libelle %}Bâtiment : {{ creneau.batiment.libelle }}{% endif %}<br>Lieu : {{ creneau.salle }}{% endif %}<br><br>Intervenants :<br>{{ creneau.intervenants }}<br>{% if creneau.info %} Informations complémentaires : {{ creneau.info }}{% endif %}<p>Voici la liste des inscrits : <br>{{ creneau.listeInscrits }}</p><p>Cordialement, </p><p>Le service en ligne d'immersions</p><p></p>",
            'active': True,
            'available_vars': ['{{ annee }}',
                '{{ creneau.batiment.libelle }}',
                '{{ creneau.campus }}',
                '{{ creneau.cours.formation }}',
                '{{ creneau.cours.libelle }}',
                '{{ creneau.cours.type }}',
                '{{ creneau.date }}',
                '{{ creneau.estunevenement }}',
                '{{ creneau.estunevisite }}',
                '{{ creneau.etablissement }}',
                '{{ creneau.evenement.description }}',
                '{{ creneau.evenement.libelle }}',
                '{{ creneau.evenement.type }}',
                '{{ creneau.heuredebut }}',
                '{{ creneau.heurefin }}',
                '{{ creneau.info }}',
                '{{ creneau.intervenants }}',
                '{{ creneau.lien }}',
                '{{ creneau.limite_annulation }}',
                '{{ creneau.limite_inscription }}',
                '{{ creneau.limite_annulation_depassee }}',
                '{{ creneau.limite_inscription_depassee }}',                
                '{{ creneau.estuncours }}',
                '{{ creneau.listeInscrits }}',
                '{{ creneau.lycee }}',
                '{{ creneau.salle }}',
                '{{ creneau.structure }}',
                '{{ creneau.temoindistanciel }}',
                '{{ creneau.visite.libelle }}',
                '{{ nom }}',
                '{{ prenom }}',
                '{{ urlPlateforme }}',
                '{{ aujourdhui }}',
                '{{ maintenant }}'                
            ]
        },
        'IMMERSION_RAPPEL_STR': {
            'label': 'Mail de rappel de participation à un créneau pour les refs structures',
            'description': "Mail envoyé à un ref structure n jours avant le créneau.Le mail sera envoyé uniquement aux référents Structures qui auront accepté l'envoi dans les paramètres.",
            'subject': 'Rappel : le cours de votre structure en immersion',
            'body': "<p></p><p>Bonjour {{ prenom }} {{ nom }}, </p><p>Vous avez paramétré de recevoir les notifications pour le {% if creneau.estuncours %}le cours{% elif creneau.estunevisite %}la visite au {{ creneau.lycee }}{% elif creneau.estunevenement %}l' évènement{% endif %} organisé par {% if creneau.lycee %}le lycée {{ creneau.lycee }}{% else %}l'établissement {{ creneau.etablissement }}{% if creneau.structure %} - {{ creneau.structure }}{% endif %}{% endif %}.<br></p>{% if creneau.estuncours %}Formation : {{ creneau.cours.formation }}<br>Cours : {{ creneau.cours.libelle }}<br>Type : {{ creneau.cours.type }}<br>{% elif creneau.estunevisite %}Objet de la visite&nbsp; : {{ creneau.visite.libelle }}.<br>{% elif creneau.estunevenement %}Type d'évènement : {{ creneau.evenement.type }}<br>Intitulé : {{ creneau.evenement.libelle }}<br>Description : {{ creneau.evenement.description }}{% endif %}<br><br>Ce créneau aura lieu le {{ creneau.date }} de {{ creneau.heuredebut }} à {{ creneau.heurefin }}.<br><br>{% if creneau.temoindistanciel %}Il aura lieu en distanciel sur le lien suivant : {{ creneau.lien }}{% else %}<br>{% if creneau.campus %}Campus : {{ creneau.campus }}{% endif %}<br>{% if creneau.batiment.libelle %}Bâtiment : {{ creneau.batiment.libelle }}{% endif %}<br>Lieu : {{ creneau.salle }}{% endif %}<br><br>Intervenants :<br>{{ creneau.intervenants }}<br>{% if creneau.info %} Informations complémentaires : {{ creneau.info }}{% endif %}<p>Voici la liste des inscrits : <br>{{ creneau.listeInscrits }}</p><p>Cordialement, </p><p>Le service en ligne d'immersions</p>",
            'active': True,
            'available_vars': ['{{ creneau.batiment.libelle }}',
                '{{ creneau.campus }}',
                '{{ creneau.cours.formation }}',
                '{{ creneau.cours.libelle }}',
                '{{ creneau.cours.type }}',
                '{{ creneau.date }}',
                '{{ creneau.estunevenement }}',
                '{{ creneau.estunevisite }}',
                '{{ creneau.etablissement }}',
                '{{ creneau.evenement.description }}',
                '{{ creneau.evenement.libelle }}',
                '{{ creneau.evenement.type }}',
                '{{ creneau.heuredebut }}',
                '{{ creneau.heurefin }}',
                '{{ creneau.info }}',
                '{{ creneau.intervenants }}',
                '{{ creneau.lien }}',
                '{{ creneau.limite_annulation }}',
                '{{ creneau.limite_inscription }}',
                '{{ creneau.limite_annulation_depassee }}',
                '{{ creneau.limite_inscription_depassee }}',
                '{{ creneau.estuncours }}',
                '{{ creneau.listeInscrits }}',
                '{{ creneau.lycee }}',
                '{{ creneau.salle }}',
                '{{ creneau.structure }}',
                '{{ creneau.temoindistanciel }}',
                '{{ creneau.visite.libelle }}',
                '{{ nom }}',
                '{{ prenom }}'
            ]
        }
    }

    for code, template in data.items():
        try:
            mt = MailTemplate.objects.get(code=code)
            mt.available_vars.clear()
        except MailTemplate.DoesNotExist:
            mt = MailTemplate.objects.create(
                code=code,
                label=template['label'],
                description=template['description'],
                active=template['active'],
                subject=template['subject'],
                body=template['body'],
            )

        for var in MailTemplateVars.objects.filter(code__in=template['available_vars']):
            mt.available_vars.add(var.id)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0203_load_scheduled_tasks_20230711_1439'),
    ]

    operations = [
        migrations.RunPython(load_mail_template_vars),
        migrations.RunPython(load_mail_templates)
    ]
