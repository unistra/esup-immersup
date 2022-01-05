from django.db import migrations
from django.core.management import call_command

def forward_func(apps, schema_editor):
    call_command('loaddata', '../fixtures/group.json', verbosity=1)

def reverse_func(apps, schema_editor):
    print('reverse')

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0120_auto_20220103_1057'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func)
    ]
