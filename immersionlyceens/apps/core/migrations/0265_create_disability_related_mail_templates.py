# Generated by Django 5.0.14 on 2025-07-10 09:58
from django.db import migrations

def add_templates(apps, schema_editor):
    MailTemplate = apps.get_model('core', "MailTemplate")

    templates = {
        "HANDICAP_NOTIF_FICHE_VALIDE": {
            "label": "Notification du référent Handicap de l’inscription à la plateforme",
            "description": "Notification du référent Handicap de l’inscription à la plateforme d’un élève ayant déclaré un handicap (utilisé à la validation de la fiche)",
            "subject": "[immersup-handicap] Un nouvel inscrit sur la plateforme",
            "body": "<p>Bonjour, </p><p>Un nouvel inscrit sur la plateforme Immersup a déclaré un handicap.</p><p>Il s'agit de : {{ inscrit.prenom }} {{ inscrit.nom }} - {{ inscrit.email }}</p><p>Merci de le contacter pour voir s'il a besoin d'un accompagnement.</p>""",
            "active": True
        },
        "HANDICAP_NOTIF_IMMERSION": {
            "label": "Notification du référent Handicap de l’inscription à un créneau",
            "description": "Notification du référent Handicap de l’inscription à un créneau d’un élève ayant déclaré un handicap (utilisé à l'inscription au créneau)",
            "subject": "[immersup-handicap] Un nouvel inscrit pour un créneau",
            "body": "<p>Bonjour,</p><p>Un nouvel inscrit a déclaré un handicap pour le {% if creneau.estuncours %}le cours{% elif creneau.estunevenement %}l'évènement{% endif %} organisé par {% if creneau.lycee %}le lycée {{ creneau.lycee }}{% else %}l'établissement {{ creneau.etablissement }}{% if creneau.structure %} - {{ creneau.structure }}{% endif %}{% endif %}.</p><p>{% if creneau.estuncours %}Formation : {{ creneau.cours.formation }}</p><p>Cours : {{ creneau.cours.libelle }}</p><p>Type : {{ creneau.cours.type }}</p><p>{% elif creneau.estunevenement %}Type d'évènement : {{ creneau.evenement.type }}</p><p>Intitulé : {{ creneau.evenement.libelle }}</p><p>Description : {{ creneau.evenement.description }}{% endif %}</p><p>Ce créneau aura lieu le {{ creneau.date }} de {{ creneau.heuredebut }} à {{ creneau.heurefin }}.</p><p>{% if creneau.temoindistanciel %}Il aura lieu en distanciel sur le lien suivant : {{ creneau.lien }}{% else %}</p><p>{% if creneau.campus.libelle %}Campus : {{ creneau.campus.libelle }}{% endif %}</p><p>{% if creneau.batiment.libelle %}Bâtiment : {{ creneau.batiment.libelle }}{% endif %}</p><p>Lieu : {{ creneau.salle }}{% endif %}</p><p>Intervenants :</p><p>{{ creneau.intervenants }}</p><p>{% if creneau.info %} Informations complémentaires : {{ creneau.info }}{% endif %}</p><p>Il s'agit de : {{ inscrit.prenom }} {{ inscrit.nom }} - {{ inscrit.email }}</p><p>Merci de le contacter pour voir si il a besoin d'un accompagnement.</p>",
            "active": True
        },
    }

    for code, template in templates.items():
        if not MailTemplate.objects.filter(code=code).exists():
            MailTemplate.objects.create(
                code=code,
                **template
            )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0264_create_registrant_mail_template_vars'),
    ]

    operations = [
        migrations.RunPython(add_templates),
    ]
