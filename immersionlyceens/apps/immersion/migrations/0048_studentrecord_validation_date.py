# Generated by Django 5.0.14 on 2025-07-11 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0047_highschoolstudentrecord_disability_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentrecord',
            name='validation_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Validation date'),
        ),
    ]
