# Generated by Django 3.2.8 on 2021-12-20 19:23

from django.db import migrations, models
import django.contrib.postgres.fields

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0112_auto_20211220_1840'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE core_slot ADD COLUMN "saved_allowed_highschool_levels" smallint[]'),
        migrations.RunSQL('UPDATE core_slot SET saved_allowed_highschool_levels = allowed_highschool_levels'),
    ]

