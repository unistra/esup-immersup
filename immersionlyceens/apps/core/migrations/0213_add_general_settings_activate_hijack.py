from django.db import migrations


def create_general_settings(apps, schema_editor):
    """Create general settings ACTIVATE_HIJACK"""
    GeneralSettings = apps.get_model('core', 'GeneralSettings')

    parameters = {
        'type': 'boolean',
        'value': False,
        'description': "Activation de l'usurpation d'identité pour les utilisateurs non superutilisateurs",
    }

    if not GeneralSettings.objects.filter(setting='ACTIVATE_HIJACK').exists():
        GeneralSettings.objects.create(setting='ACTIVATE_HIJACK', parameters=parameters)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0212_general_settings_pdf_emails_20231019_1637'),
    ]

    operations = [
        migrations.RunPython(create_general_settings)
    ]
