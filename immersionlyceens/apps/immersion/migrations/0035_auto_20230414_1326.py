# Generated by Django 3.2.18 on 2023-04-14 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0034_highschoolstudentrecord_validation_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschoolstudentrecord',
            name='rejected_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Rejected date'),
        ),
        migrations.AddField(
            model_name='visitorrecord',
            name='rejected_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Rejected date'),
        ),
    ]