# Generated by Django 2.2.10 on 2020-02-18 06:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_auto_20200214_1456'),
    ]

    operations = [
        migrations.AddField(
            model_name='immersionuser',
            name='recovery_string',
            field=models.TextField(blank=True, null=True, unique=True, verbose_name='Account password recovery string'),
        ),
    ]