# Generated by Django 2.2.11 on 2020-04-06 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_auto_20200406_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='highereducationinstitution',
            name='country',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Country'),
        ),
        migrations.AddField(
            model_name='highereducationinstitution',
            name='zip_code',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Zip code'),
        ),
    ]
