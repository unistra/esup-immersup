# Generated by Django 3.2.8 on 2021-10-19 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0086_alter_immersionuser_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='OffOfferEventType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=256, unique=True, verbose_name='Short label')),
                ('full_label', models.CharField(max_length=256, unique=True, verbose_name='Full label')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Off offer event type',
                'verbose_name_plural': 'Off offer event types',
                'ordering': ('label',),
            },
        ),
        migrations.AlterModelOptions(
            name='accompanyingdocument',
            options={'ordering': ['label'], 'verbose_name': 'Accompanying document', 'verbose_name_plural': 'Accompanying documents'},
        ),
        migrations.AlterModelOptions(
            name='annualstatistics',
            options={'ordering': ['-year'], 'verbose_name': 'Annual statistics', 'verbose_name_plural': 'Annual statistics'},
        ),
        migrations.AlterModelOptions(
            name='bachelormention',
            options={'ordering': ['label'], 'verbose_name': 'Technological bachelor series', 'verbose_name_plural': 'Séries du baccalauréat technologique'},
        ),
        migrations.AlterModelOptions(
            name='building',
            options={'ordering': ['label'], 'verbose_name': 'Building'},
        ),
        migrations.AlterModelOptions(
            name='calendar',
            options={'ordering': ['label'], 'verbose_name': 'Calendar', 'verbose_name_plural': 'Calendars'},
        ),
        migrations.AlterModelOptions(
            name='campus',
            options={'ordering': ['label'], 'verbose_name': 'Campus', 'verbose_name_plural': 'Campus'},
        ),
        migrations.AlterModelOptions(
            name='canceltype',
            options={'ordering': ['label'], 'verbose_name': 'Cancel type', 'verbose_name_plural': 'Cancel types'},
        ),
        migrations.AlterModelOptions(
            name='course',
            options={'ordering': ['label'], 'verbose_name': 'Course', 'verbose_name_plural': 'Courses'},
        ),
        migrations.AlterModelOptions(
            name='coursetype',
            options={'ordering': ['label'], 'verbose_name': 'Course type', 'verbose_name_plural': 'Course type'},
        ),
        migrations.AlterModelOptions(
            name='establishment',
            options={'ordering': ['label'], 'verbose_name': 'Establishment', 'verbose_name_plural': 'Establishments'},
        ),
        migrations.AlterModelOptions(
            name='evaluationformlink',
            options={'ordering': ['evaluation_type'], 'verbose_name': 'Evaluation form link', 'verbose_name_plural': 'Evaluation forms links'},
        ),
        migrations.AlterModelOptions(
            name='evaluationtype',
            options={'ordering': ['label'], 'verbose_name': 'Evaluation type', 'verbose_name_plural': 'Evaluation types'},
        ),
        migrations.AlterModelOptions(
            name='generalbachelorteaching',
            options={'ordering': ['label'], 'verbose_name': 'General bachelor specialty teaching', 'verbose_name_plural': 'General bachelor specialties teachings'},
        ),
        migrations.AlterModelOptions(
            name='generalsettings',
            options={'ordering': ['setting'], 'verbose_name': 'General setting', 'verbose_name_plural': 'General settings'},
        ),
        migrations.AlterModelOptions(
            name='highereducationinstitution',
            options={'ordering': ['label'], 'verbose_name': 'Higher education institution', 'verbose_name_plural': 'Higher education institutions'},
        ),
        migrations.AlterModelOptions(
            name='highschool',
            options={'ordering': ['label'], 'verbose_name': 'High school'},
        ),
        migrations.AlterModelOptions(
            name='holiday',
            options={'ordering': ['label'], 'verbose_name': 'Holiday', 'verbose_name_plural': 'Holidays'},
        ),
        migrations.AlterModelOptions(
            name='immersionuser',
            options={'ordering': ['last_name', 'first_name'], 'verbose_name': 'User'},
        ),
        migrations.AlterModelOptions(
            name='informationtext',
            options={'ordering': ['label'], 'verbose_name': 'Information text', 'verbose_name_plural': 'Information texts'},
        ),
        migrations.AlterModelOptions(
            name='mailtemplate',
            options={'ordering': ['label'], 'verbose_name': 'Mail template', 'verbose_name_plural': 'Mail templates'},
        ),
        migrations.AlterModelOptions(
            name='mailtemplatevars',
            options={'ordering': ['code'], 'verbose_name': 'Template variable', 'verbose_name_plural': 'Template variables'},
        ),
        migrations.AlterModelOptions(
            name='publicdocument',
            options={'ordering': ['label'], 'verbose_name': 'Public document', 'verbose_name_plural': 'Public documents'},
        ),
        migrations.AlterModelOptions(
            name='publictype',
            options={'ordering': ['label'], 'verbose_name': 'Public type', 'verbose_name_plural': 'Public types'},
        ),
        migrations.AlterModelOptions(
            name='structure',
            options={'ordering': ['label'], 'verbose_name': 'Structure', 'verbose_name_plural': 'Structures'},
        ),
        migrations.AlterModelOptions(
            name='training',
            options={'ordering': ['label'], 'verbose_name': 'Training', 'verbose_name_plural': 'Trainings'},
        ),
        migrations.AlterModelOptions(
            name='trainingdomain',
            options={'ordering': ['label'], 'verbose_name': 'Training domain', 'verbose_name_plural': 'Training domains'},
        ),
        migrations.AlterModelOptions(
            name='trainingsubdomain',
            options={'ordering': ['label'], 'verbose_name': 'Training sub domain', 'verbose_name_plural': 'Training sub domains'},
        ),
        migrations.AlterModelOptions(
            name='universityyear',
            options={'ordering': ['label'], 'verbose_name': 'University year', 'verbose_name_plural': 'University years'},
        ),
        migrations.AlterModelOptions(
            name='usercoursealert',
            options={'ordering': ['-alert_date'], 'verbose_name': 'Course free slot alert', 'verbose_name_plural': 'Course free slot alerts'},
        ),
        migrations.AlterModelOptions(
            name='vacation',
            options={'ordering': ['label'], 'verbose_name': 'Vacation', 'verbose_name_plural': 'Vacations'},
        ),
    ]