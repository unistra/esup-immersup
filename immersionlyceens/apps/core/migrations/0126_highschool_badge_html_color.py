# Generated by Django 3.2.8 on 2022-01-10 08:24

import random

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0125_auto_20220107_1502'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschool',
            name='badge_html_color',
            field=models.CharField(default='#{:02x}{:02x}{:02x}'.format(*map(lambda x: random.randint(0, 255), range(3))), max_length=7, verbose_name='Badge color (HTML)'),
            preserve_default=False,
        ),
    ]