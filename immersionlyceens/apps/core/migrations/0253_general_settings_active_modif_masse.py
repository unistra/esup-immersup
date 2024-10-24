# Generated by Django 5.0.7 on 2024-08-01 09:45

from django.db import migrations

def add_mass_update_settings(apps, schema_editor):
    GeneralSettings = apps.get_model('core', "GeneralSettings")

    code = 'ACTIVATE_MASS_UPDATE'

    if not GeneralSettings.objects.filter(setting=code).exists():
        GeneralSettings.objects.create(
            setting=code,
            parameters={
                "type": "boolean",
                "value": False,
                "description": "Activation des modifications de masse"
            }
        )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0252_update_mail_templates_variables'),
    ]

    operations = [
        migrations.RunPython(add_mass_update_settings),
    ]
