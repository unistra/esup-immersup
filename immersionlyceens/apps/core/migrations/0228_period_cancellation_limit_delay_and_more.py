# Generated by Django 5.0.4 on 2024-05-14 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0227_slot_allow_group_registrations_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='period',
            name='cancellation_limit_delay',
            field=models.PositiveSmallIntegerField(blank=True, default=0, null=True, verbose_name='Cancellation limit delay'),
        ),
        migrations.AlterField(
            model_name='period',
            name='registration_end_date_policy',
            field=models.SmallIntegerField(choices=[(0, 'Utiliser la date de fin des inscriptions de la période'), (1, 'Utiliser la date de fin de chaque créneau')], default=1, verbose_name='Registration end date policy'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='public_group',
            field=models.BooleanField(blank=True, null=True, verbose_name='Public group registrations'),
        ),
    ]