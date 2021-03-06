# Generated by Django 3.2.8 on 2022-01-12 17:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import immersionlyceens.apps.core.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('immersion', '0025_remove_studentrecord_civility'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitorRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('civility', models.SmallIntegerField(choices=[(1, 'Mr'), (2, 'Mrs')], default=1, verbose_name='Civility')),
                ('phone', models.CharField(blank=True, max_length=14, null=True, verbose_name='Phone number')),
                ('birth_date', models.DateField(verbose_name='Birth date')),
                ('motivation', models.TextField(verbose_name='Motivation')),
                ('identity_document', models.FileField(help_text='Seulement des fichiers de type (jpg, jpeg, png). Taille max : 20,0\xa0Mio', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Identity document')),
                ('civil_liability_insurance', models.FileField(help_text='Seulement des fichiers de type (jpg, jpeg, png). Taille max : 20,0\xa0Mio', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Civil liability insurance')),
                ('validation', models.SmallIntegerField(choices=[(1, 'To validate'), (2, 'Validated'), (3, 'Rejected')], default=1, verbose_name='Validation')),
                ('allowed_global_registrations', models.SmallIntegerField(blank=True, null=True, verbose_name='Number of allowed year registrations (excluding visits and events)')),
                ('allowed_first_semester_registrations', models.SmallIntegerField(blank=True, null=True, verbose_name='Number of allowed registrations for second semester (excluding visits and events)')),
                ('allowed_second_semester_registrations', models.SmallIntegerField(blank=True, null=True, verbose_name='Number of allowed registrations for first semester (excluding visits and events)')),
                ('visitor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='visitor_record', to=settings.AUTH_USER_MODEL, verbose_name='Visitor')),
            ],
            options={
                'verbose_name': 'Visitor record',
                'verbose_name_plural': 'Visitor records',
            },
        ),
    ]
