# Generated by Django 2.2.10 on 2020-03-12 13:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_auto_20200312_1406'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursetype',
            name='full_label',
            field=models.CharField(max_length=256, unique=True, verbose_name='Full label'),
        ),
    ]