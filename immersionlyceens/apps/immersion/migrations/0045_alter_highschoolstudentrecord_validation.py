# Generated by Django 5.0.7 on 2024-09-20 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0044_alter_highschoolstudentrecorddocument_document_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='validation',
            field=models.SmallIntegerField(choices=[(0, 'To complete'), (1, 'To validate'), (2, 'Validated'), (3, 'Rejected'), (4, 'To revalidate'), (5, 'Initialization (to complete)')], default=0, verbose_name='Validation'),
        ),
    ]