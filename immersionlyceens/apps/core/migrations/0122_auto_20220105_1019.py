from django.db import migrations
from django.core.management import call_command

def forward_func(apps, schema_editor):
    call_command('loaddata', '../fixtures/group_permissions.json', verbosity=1)

def reverse_func(apps, schema_editor):
    print('reverse')

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0121_auto_20220105_1018'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func)
    ]
