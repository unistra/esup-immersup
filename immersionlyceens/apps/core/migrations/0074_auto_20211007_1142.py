# Generated by Django 3.2.8 on 2021-10-07 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0073_establishment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bachelormention',
            options={'verbose_name': 'Technological bachelor series', 'verbose_name_plural': 'Technological bachelor series'},
        ),
        migrations.AlterField(
            model_name='accompanyingdocument',
            name='document',
            field=models.FileField(help_text='Only files with type (doc,pdf,xls,ods,odt,docx)', upload_to='uploads/accompanyingdocs/%Y', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='certificatelogo',
            name='logo',
            field=models.ImageField(help_text='Only files with type (gif, jpg, png)', upload_to='uploads/certificate_logo/', verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='certificatesignature',
            name='signature',
            field=models.ImageField(help_text='Only files with type (gif, jpg, png)', upload_to='uploads/certificate_signature/', verbose_name='Signature'),
        ),
        migrations.AlterField(
            model_name='establishment',
            name='data_source_plugin',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Accounts source plugin'),
        ),
        migrations.AlterField(
            model_name='publicdocument',
            name='document',
            field=models.FileField(help_text='Only files with type (doc,pdf,xls,ods,odt,docx)', upload_to='uploads/publicdocs/%Y', verbose_name='Document'),
        ),
    ]