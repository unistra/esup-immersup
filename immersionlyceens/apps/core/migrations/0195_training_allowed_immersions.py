# Generated by Django 3.2.19 on 2023-06-27 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0194_auto_20230609_1438'),
    ]

    operations = [
        migrations.AddField(
            model_name='training',
            name='allowed_immersions',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Allowed immersions per student, per period'),
        ),
    ]