# Generated by Django 3.2.18 on 2023-05-30 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0181_auto_20230517_1410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='refstructuresnotificationssettings',
            name='structures',
            field=models.ManyToManyField(blank=True, related_name='source_structures', to='core.Structure', verbose_name='Structures'),
        ),
    ]
