# Generated by Django 5.0.4 on 2024-04-12 08:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0213_alter_slot_allowed_bachelor_mentions_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='slot',
            name='visit',
        ),
        migrations.DeleteModel(
            name='Visit',
        ),
    ]