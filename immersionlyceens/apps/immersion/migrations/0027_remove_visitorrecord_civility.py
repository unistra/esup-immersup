# Generated by Django 3.2.8 on 2022-01-12 17:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0026_visitorrecord'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='visitorrecord',
            name='civility',
        ),
    ]