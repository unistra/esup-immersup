# Generated by Django 2.2.11 on 2020-04-02 09:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_auto_20200330_1103'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='usercoursealert',
            options={'verbose_name': 'Course free slot alert', 'verbose_name_plural': 'Course free slot alerts'},
        ),
        migrations.RemoveField(
            model_name='component',
            name='url',
        ),
    ]
