# Generated by Django 3.2.16 on 2023-03-28 11:07

from django.db import migrations, models
import immersionlyceens.apps.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0157_auto_20230324_0858'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Calendar',
        ),
        migrations.AddField(
            model_name='universityyear',
            name='global_evaluation_date',
            field=models.DateField(blank=True, null=True, verbose_name='Global evaluation date'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='date',
            field=models.DateField(blank=True, null=True, validators=[immersionlyceens.apps.core.models.validate_slot_date], verbose_name='Date'),
        ),
    ]