# Generated by Django 3.2 on 2021-10-12 08:39

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0078_auto_20211011_1135'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generalsettings',
            name='description',
        ),
        migrations.RemoveField(
            model_name='generalsettings',
            name='value',
        ),
        migrations.AddField(
            model_name='generalsettings',
            name='parameters',
            field=models.JSONField(default=dict, verbose_name='Setting parameters'),
        ),
        migrations.AlterField(
            model_name='course',
            name='speakers',
            field=models.ManyToManyField(related_name='courses', to=settings.AUTH_USER_MODEL, verbose_name='Speakers'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='speakers',
            field=models.ManyToManyField(related_name='slots', to=settings.AUTH_USER_MODEL, verbose_name='Speakers'),
        ),
    ]