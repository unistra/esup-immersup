# Generated by Django 3.2.18 on 2023-05-26 10:03

from django.db import migrations

def add_missing_attestation_cancel_type(apps, schema_editor):
    CancelType = apps.get_model('core', "CancelType")

    code = 'ATT'

    if not CancelType.objects.filter(code=code).exists():
        CancelType.objects.create(
            code='ATT',
            system=True,
            label='Défaut de pièce',
            active=True,
        )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0179_auto_20230525_1652'),
    ]

    operations = [
        migrations.RunPython(add_missing_attestation_cancel_type),
    ]