# Generated by Django 3.2.18 on 2023-06-09 12:38

from django.db import migrations


def rename_setting(apps, schema_editor):
    GeneralSettings = apps.get_model('core', "GeneralSettings")

    if not GeneralSettings.objects.filter(setting="DELETE_RECORD_ATTACHMENTS_AT_VALIDATION").exists():
        try:
            parameter = GeneralSettings.objects.get(setting="DELETE_VISITOR_ATTACHMENTS_AT_VALIDATION")
            parameter.setting = "DELETE_RECORD_ATTACHMENTS_AT_VALIDATION"
            parameter.parameters["description"] = "Si le paramètre est à 'true', les justificatifs sans date de validité seront supprimés après la validation d'une fiche lycéen ou visiteur"
            parameter.save()
        except GeneralSettings.DoesNotExist:
            GeneralSettings.objects.create(
                setting="DELETE_RECORD_ATTACHMENTS_AT_VALIDATION",
                parameters={
                    "description": "Si le paramètre est à 'true', les justificatifs sans date de validité seront supprimés après la validation d'une fiche lycéen ou visiteur",
                    "type": "boolean",
                    "value": True,
                }
            )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0193_add_highschools_informations_texts'),
    ]

    operations = [
        migrations.RunPython(rename_setting),
    ]
