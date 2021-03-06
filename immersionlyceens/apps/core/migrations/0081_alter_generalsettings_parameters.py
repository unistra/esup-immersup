# Generated by Django 3.2.8 on 2021-10-12 15:43

from os.path import dirname, join

import immersionlyceens.libs.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0080_alter_generalsettings_parameters'),
    ]

    schema_path = join(dirname(dirname(__file__)), 'schemas', 'general_settings.json')

    operations = [
        migrations.AlterField(
            model_name='generalsettings',
            name='parameters',
            field=models.JSONField(default=dict, validators=[immersionlyceens.libs.validators.JsonSchemaValidator(schema_path)], verbose_name='Setting configuration'),
        ),
    ]
