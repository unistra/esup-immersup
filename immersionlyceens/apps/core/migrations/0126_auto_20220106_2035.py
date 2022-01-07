from django.db import migrations
from immersionlyceens.apps.core.models import PostBachelorLevel, StudentLevel

def forward_func(apps, schema_editor):
    for level in PostBachelorLevel.objects.all():
        level.order = level.pk
        level.save()

    for level in StudentLevel.objects.all():
        level.order = level.pk
        level.save()


def reverse_func(apps, schema_editor):
    print('reverse')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0125_auto_20220106_2035'),
    ]

    operations = [
        migrations.RunPython(forward_func, reverse_func)
    ]
