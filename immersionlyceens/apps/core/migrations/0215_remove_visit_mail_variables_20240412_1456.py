# Generated by Django 5.0.4 on 2024-04-12 12:56

from django.db import migrations

def remove_visit_mail_template_vars(apps, schema_editor):
    MailTemplateVars = apps.get_model('core', 'MailTemplateVars')

    codes = [
        "{{ visite.libelle }}",
        "{{ visite.nbplaceslibre }}",
        "{{ creneau.visite.libelle }}",
        "{{ creneau.estunevisite }}"
    ]

    MailTemplateVars.objects.filter(code__in=codes).delete()

    # Updates:
    (MailTemplateVars.objects
        .filter(code="{{ creneau.libelle }}")
        .update(description="Créneau : libellé du cours ou de l'évènement")
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0214_remove_slot_visit_delete_visit'),
    ]

    operations = [
        migrations.RunPython(remove_visit_mail_template_vars)
    ]