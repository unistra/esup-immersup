# Generated by Django 2.2.10 on 2020-02-14 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0002_highschoolstudentrecord_class_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschoolstudentrecord',
            name='duplicates',
            field=models.TextField(blank=True, default=None, null=True, verbose_name='Duplicates list'),
        ),
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='bachelor_type',
            field=models.SmallIntegerField(choices=[(1, 'General'), (2, 'Technological'), (3, 'Professional')], default=1, verbose_name='Bachelor type'),
        ),
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='origin_bachelor_type',
            field=models.SmallIntegerField(blank=True, choices=[(1, 'General'), (2, 'Technological'), (3, 'Professional'), (4, 'DAEU')], default=1, null=True, verbose_name='Bachelor type'),
        ),
    ]
