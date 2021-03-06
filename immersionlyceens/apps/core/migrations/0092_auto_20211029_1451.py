# Generated by Django 3.2.8 on 2021-10-29 12:51

from django.db import migrations, models
import django.db.models.constraints


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0091_training_highschool'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='course',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(deferrable=django.db.models.constraints.Deferrable['IMMEDIATE'], fields=('highschool', 'training', 'label'), name='unique_highschool_course'),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(deferrable=django.db.models.constraints.Deferrable['IMMEDIATE'], fields=('structure', 'training', 'label'), name='unique_structure_course'),
        ),
    ]
