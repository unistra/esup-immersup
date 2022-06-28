from __future__ import unicode_literals

from django.conf import settings
from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0138_auto_20220317_0908'),
    ]

    if settings.POSTGRESQL_ADD_UNACCENT_EXTENSION:
        operations = [
            UnaccentExtension()
        ]
    else:
        operations = []
