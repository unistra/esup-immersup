# Generated by Django 3.2.18 on 2023-04-14 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0165_auto_20230413_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='immersion',
            name='cancellation_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Cancellation date'),
        ),
    ]