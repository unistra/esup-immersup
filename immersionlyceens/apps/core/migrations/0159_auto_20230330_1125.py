# Generated by Django 3.2.18 on 2023-03-30 09:25
import json
from django.db import migrations

def high_school_settings(apps, schema_editor):
    GeneralSettings = apps.get_model("core", "GeneralSettings")

    if not GeneralSettings.objects.filter(setting='ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT').exists():
        GeneralSettings.objects.create(
            setting='ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT',
            parameters={"type": "boolean", "value": True, "description": "Activation des lycées conventionnés"}
        )

    if not GeneralSettings.objects.filter(setting='ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT').exists():
        GeneralSettings.objects.create(
            setting='ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT',
            parameters={"type": "boolean", "value": False, "description": "Activation des lycées non conventionnés"}
        )

    if not GeneralSettings.objects.filter(setting='REQUEST_FOR_STUDENT_AGREEMENT').exists():
        GeneralSettings.objects.create(
            setting='REQUEST_FOR_STUDENT_AGREEMENT',
            parameters={"type": "boolean", "value": True, "description": "Demander l'accord des lycéens pour que leur lycée puisse voir leurs immersions"}
        )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0158_auto_20230328_1307'),
    ]

    operations = [
        migrations.RunPython(high_school_settings),
    ]
