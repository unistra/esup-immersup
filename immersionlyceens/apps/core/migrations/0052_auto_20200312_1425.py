# Generated by Django 2.2.10 on 2020-03-12 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_auto_20200312_1423'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursetype',
            name='label',
            field=models.CharField(max_length=256, unique=True, verbose_name='Short label'),
        ),
    ]
