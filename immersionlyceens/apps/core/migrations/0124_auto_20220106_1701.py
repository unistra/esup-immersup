from django.db import migrations
from immersionlyceens.apps.core.models import HighSchoolLevel

def forward_func(apps, schema_editor):
    for level in HighSchoolLevel.objects.all():
        level.order = level.pk
        level.save()


def reverse_func(apps, schema_editor):
    print('reverse')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0123_highschoollevel_order'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func)
    ]
