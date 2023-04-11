

import functools

from django.db import migrations, models


def population_cons_str_group(apps, schema_editor):

    Groups = apps.get_model('auth', 'Group')

    if not Groups.objects.filter(name='CONS-STR').exists():
        Groups.objects.create(
                name = "CONS-STR"
        )


def cons_str_group_permissions(apps, group_name):
    permission_list = []
    Group = apps.get_model('auth', 'Group')
    group = Group.objects.get(name="CONS-STR")
    group.permissions.add(*permission_list)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0162_alter_period_options'),
    ]

    operations = [
      migrations.RunPython(population_cons_str_group),
      migrations.RunPython(cons_str_group_permissions),
    ]
