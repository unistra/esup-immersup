# Generated by Django 2.2.9 on 2020-01-17 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_calendar_calendar_mode'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='calendar',
            options={'verbose_name': 'Calendar', 'verbose_name_plural': 'Calendars'},
        ),
        migrations.AlterField(
            model_name='calendar',
            name='registration_start_date_per_semester',
            field=models.PositiveIntegerField(default=2),
        ),
        migrations.AlterField(
            model_name='calendar',
            name='year_nb_authorized_immersion',
            field=models.PositiveIntegerField(default=4),
        ),
    ]
