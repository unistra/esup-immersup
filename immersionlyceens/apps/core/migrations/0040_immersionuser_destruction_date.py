# Generated by Django 2.2.10 on 2020-02-11 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_immersionuser_validation_string'),
    ]

    operations = [
        migrations.AddField(
            model_name='immersionuser',
            name='destruction_date',
            field=models.DateField(blank=True, null=True, verbose_name='Account destruction date'),
        ),
    ]
