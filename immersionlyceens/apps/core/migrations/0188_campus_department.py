# Generated by Django 3.2.19 on 2023-06-06 12:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0187_auto_20230606_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='campus',
            name='department',
            field=models.CharField(default='', max_length=128, verbose_name='Department'),
            preserve_default=False,
        ),
    ]