# Generated by Django 5.0.6 on 2024-07-16 05:55

from django.db import migrations

def update_general_settings(apps, schema_editor):
    GeneralSettings = apps.get_model('core', 'GeneralSettings')

    try:
        gs = GeneralSettings.objects.get(setting='HIGHSCHOOL_VISIT')
        gs.delete()
    except GeneralSettings.DoesNotExist:
        # nothing to do
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0246_remove_slot_face_to_face'),
    ]

    operations = [
        migrations.RunPython(update_general_settings)
    ]
