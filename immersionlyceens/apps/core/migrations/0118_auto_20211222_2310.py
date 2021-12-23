from django.db import migrations
from django.core.management import call_command

def forward_func(apps, schema_editor):
    call_command('loaddata', '../fixtures/high_school_levels.json', verbosity=1)
    call_command('loaddata', '../fixtures/post_bachelor_levels.json', verbosity=1)
    call_command('loaddata', '../fixtures/student_levels.json', verbosity=1)

def reverse_func(apps, schema_editor):
    print('reverse')

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0117_auto_20211222_2310'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func)
    ]
