# Generated by Django 5.0.4 on 2024-04-23 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0222_highschool_allow_individual_immersions_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalsettings',
            name='setting_type',
            field=models.SmallIntegerField(null=True, blank=True, choices=[(0, 'Technical'), (1, 'Functional')], default=0, verbose_name='Setting type'),
        ),
    ]
