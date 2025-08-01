# Generated by Django 5.0.14 on 2025-07-09 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0261_establishment_disability_notify_on_record_validation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='establishment',
            name='disability_notify_on_record_validation',
            field=models.BooleanField(default=True, help_text='Notify disability referent on record validation', verbose_name='Disability referent record notification'),
        ),
    ]
