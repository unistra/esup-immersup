# Generated by Django 5.0.4 on 2024-04-22 11:22

import django_countries.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0221_alter_establishment_options_alter_highschool_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschool',
            name='allow_individual_immersions',
            field=models.BooleanField(default=True, help_text='If unchecked, allow only group immersions by the school manager', verbose_name='Allow individual immersions'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='country',
            field=django_countries.fields.CountryField(blank=True, max_length=2, null=True, verbose_name='Country'),
        ),
    ]