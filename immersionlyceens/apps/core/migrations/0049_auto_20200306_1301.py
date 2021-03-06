# Generated by Django 2.2.10 on 2020-03-06 12:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_merge_20200224_1536'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='accompanyingdocument',
            managers=[
            ],
        ),
        migrations.CreateModel(
            name='Immersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attendance_status', models.SmallIntegerField(choices=[(0, 'Not entered'), (1, 'Present'), (2, 'Absent')], default=0, verbose_name='Attendance status')),
                ('cancellation_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='immersions', to='core.CancelType', verbose_name='Cancellation type')),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='immersions', to='core.Slot', verbose_name='Slot')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='immersions', to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'Immersion',
                'verbose_name_plural': 'Immersionss',
            },
        ),
    ]
