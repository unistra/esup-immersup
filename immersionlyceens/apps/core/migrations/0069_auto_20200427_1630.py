# Generated by Django 2.2.10 on 2020-04-27 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_auto_20200424_1517'),
    ]

    operations = [
        migrations.CreateModel(
            name='CertificateLogo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logo', models.ImageField(help_text='Seulement des fichiers de type (gif, jpg, png)', upload_to='uploads/certificate_logo/', verbose_name='Logo')),
            ],
            options={
                'verbose_name': 'Logo for attendance certificate',
                'verbose_name_plural': 'Logo for attendance certificate',
            },
        ),
        migrations.CreateModel(
            name='CertificateSignature',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature', models.ImageField(help_text='Seulement des fichiers de type (gif, jpg, png)', upload_to='uploads/certificate_signature/', verbose_name='Signature')),
            ],
            options={
                'verbose_name': 'Signature for attendance certificate',
                'verbose_name_plural': 'Signature for attendance certificate',
            },
        ),
        migrations.DeleteModel(
            name='AttendanceCertificateModel',
        ),
    ]