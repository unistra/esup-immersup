# Generated by Django 2.2.10 on 2020-03-12 13:06

from django.db import migrations, models
import django.utils.timezone

def set_course_full_label(apps, schema_editor):
    # noinspection PyPep8Naming
    CourseType = apps.get_model('core', 'CourseType')
    for course_type in CourseType.objects.all():
        course_type.full_label = course_type.label
        course_type.save()

def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_auto_20200306_1301'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='immersion',
            options={'verbose_name': 'Immersion', 'verbose_name_plural': 'Immersions'},
        ),
        migrations.AddField(
            model_name='coursetype',
            name='full_label',
            field=models.CharField(default=django.utils.timezone.now(), max_length=256, unique=False, verbose_name='Full label'),
            preserve_default=False,
        ),
        
        migrations.RunPython(code=set_course_full_label, reverse_code=do_nothing)
    ]