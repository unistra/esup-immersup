# Generated by Django 5.0.4 on 2024-04-22 10:11

import immersionlyceens.apps.core.models
import immersionlyceens.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0220_new_cancel_mail_templates'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='establishment',
            options={'ordering': ['label'], 'verbose_name': 'Higher education establishment', 'verbose_name_plural': 'Higher education establishments'},
        ),
        migrations.AlterModelOptions(
            name='highschool',
            options={'ordering': ['city', 'label'], 'verbose_name': 'High school / Secondary school', 'verbose_name_plural': 'High schools / Secondary schools'},
        ),
        migrations.AlterField(
            model_name='accompanyingdocument',
            name='document',
            field=models.FileField(help_text='Uniquement des fichiers de type (doc, pdf, xls, ods, odt, docx, xlsx). Taille max : 20,0\xa0Mio', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='attestationdocument',
            name='template',
            field=models.FileField(blank=True, help_text='Uniquement des fichiers de type (doc, pdf, xls, ods, odt, docx, xlsx). Taille max : 20,0\xa0Mio', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Template'),
        ),
        migrations.AlterField(
            model_name='certificatelogo',
            name='logo',
            field=models.ImageField(help_text='Uniquement des fichiers de type (gif, jpg, png)', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='certificatesignature',
            name='signature',
            field=models.ImageField(help_text='Uniquement des fichiers de type (gif, jpg, png)', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Signature'),
        ),
        migrations.AlterField(
            model_name='customthemefile',
            name='file',
            field=models.FileField(help_text='Uniquement des fichiers de type (png, jpeg, jpg, ico, css, js). Taille max : 20,0\xa0Mio', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='File'),
        ),
        migrations.AlterField(
            model_name='establishment',
            name='logo',
            field=models.ImageField(blank=True, help_text='Uniquement des fichiers de type (gif, jpg, png)', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='establishment',
            name='signature',
            field=models.ImageField(blank=True, help_text='Uniquement des fichiers de type (gif, jpg, png)', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Signature'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='address',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Address'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='city',
            field=immersionlyceens.fields.UpperCharField(blank=True, max_length=255, null=True, verbose_name='City'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='department',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name='Department'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='head_teacher_name',
            field=models.CharField(blank=True, help_text='civility last name first name', max_length=255, null=True, verbose_name='Head teacher name'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='logo',
            field=models.ImageField(blank=True, help_text='Uniquement des fichiers de type (gif, jpg, png)', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Phone number'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='signature',
            field=models.ImageField(blank=True, help_text='Uniquement des fichiers de type (gif, jpg, png)', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Signature'),
        ),
        migrations.AlterField(
            model_name='highschool',
            name='zip_code',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name='Zip code'),
        ),
        migrations.AlterField(
            model_name='publicdocument',
            name='document',
            field=models.FileField(help_text='Uniquement des fichiers de type (doc, pdf, xls, ods, odt, docx, xlsx). Taille max : 20,0\xa0Mio', upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Document'),
        ),
    ]
