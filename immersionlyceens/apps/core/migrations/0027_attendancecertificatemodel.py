# Generated by Django 2.2.9 on 2020-01-29 21:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_auto_20200128_1723'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceCertificateModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.FileField(help_text='Only files with type (docx)', upload_to='uploads/attendance_cert_model/', verbose_name='Document')),
            ],
            options={
                'verbose_name': 'Attendance certificate model',
                'verbose_name_plural': 'Attendance certificate model',
            },
        ),
    ]
