# Generated by Django 3.2.19 on 2023-07-26 07:27
from django.db import migrations

def associate_template_vars(apps, schema_editor):
    MailTemplate = apps.get_model('core', 'MailTemplate')
    MailTemplateVars = apps.get_model('core', 'MailTemplateVars')

    try:
        template = MailTemplate.objects.get(code='EVALUATION_CRENEAU')
        var = MailTemplateVars.objects.get(code__iexact='{{ creneau.campus.ville }}')
        template.available_vars.add(var)
    except MailTemplate.DoesNotExist:
        print("Mail template EVALUATION_CRENEAU does not exist")
    except MailTemplateVars.DoesNotExist:
        print("Mail template variable {{ creneau.campus.ville }} does not exist")

    try:
        template = MailTemplate.objects.get(code='IMMERSION_ANNUL')

        codes = ['creneau.campus.ville', 'creneau.limite_annulation_depassee', 'creneau.limite_inscription_depassee']

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template IMMERSION_ANNUL does not exist")

    try:
        template = MailTemplate.objects.get(code='IMMERSION_CONFIRM')

        codes = ['creneau.limite_annulation_depassee', 'creneau.limite_inscription_depassee']

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template IMMERSION_CONFIRM does not exist")

    try:
        template = MailTemplate.objects.get(code='IMMERSION_RAPPEL')

        codes = ['creneau.limite_annulation_depassee', 'creneau.limite_inscription_depassee']

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template IMMERSION_RAPPEL does not exist")

    try:
        template = MailTemplate.objects.get(code='IMMERSION_RAPPEL_INT')

        codes = ['creneau.batiment.lien', 'creneau.nbPlaceslibres']

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template IMMERSION_RAPPEL_INT does not exist")

    try:
        template = MailTemplate.objects.get(code='IMMERSION_RAPPEL_STR')

        codes = ['creneau.batiment.lien', 'creneau.nbPlaceslibres']

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template IMMERSION_RAPPEL_STR does not exist")

    # For existing instances, first reset available variables for CPT_FUSION template
    try:
        template = MailTemplate.objects.get(code='CPT_FUSION')
        template.available_vars.clear()

        codes = ["urlPlateforme", "nom", "prenom", "lienDemandeur", "lienAssociationComptes"]

        for code in codes:
            try:
                var = MailTemplateVars.objects.get(code__iexact="{{ %s }}" % code)
                template.available_vars.add(var)
            except MailTemplateVars.DoesNotExist:
                print("Mail template variable {{ %s }} does not exist" % code)
    except MailTemplate.DoesNotExist:
        print("Mail template CPT_FUSION does not exist")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0206_new_template_var_20230719_1056'),
    ]

    operations = [
        migrations.RunPython(associate_template_vars)
    ]
