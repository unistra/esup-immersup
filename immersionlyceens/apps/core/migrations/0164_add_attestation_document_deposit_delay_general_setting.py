import functools

from django.db import migrations, models

from immersionlyceens.apps.core.models import GeneralSettings


def add_attestation_document_setting(apps, schema_editor):

    code = 'ATTESTATION_DOCUMENT_DEPOSIT_DELAY'
    if not GeneralSettings.objects.filter(setting=code).exists():
        GeneralSettings.objects.create(
            setting=code,
            parameters={
                "type": "integer",
                "value": 30,
                "description": "Délai (en jours) à partir duquel un lycéen ou un visiteur peut redéposer une pièce justificative valide."
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0163_add_cons_str_group'),
    ]

    operations = [
      migrations.RunPython(add_attestation_document_setting),
    ]
