# Generated by Django 3.2.8 on 2021-10-11 09:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0077_merge_0073_auto_20211008_1613_0076_auto_20211008_1455'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bachelormention',
            options={'verbose_name': 'Technological bachelor series', 'verbose_name_plural': 'Séries du baccalauréat technologique'},
        ),
        migrations.RenameField(
            model_name='course',
            old_name='teachers',
            new_name='speakers'
        ),
        migrations.RenameField(
            model_name='slot',
            old_name='teachers',
            new_name='speakers'
        ),

        migrations.AlterField(
            model_name='accompanyingdocument',
            name='document',
            field=models.FileField(help_text='Seulement des fichiers de type (doc,pdf,xls,ods,odt,docx)', upload_to='uploads/accompanyingdocs/%Y', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='annualstatistics',
            name='structures_count',
            field=models.SmallIntegerField(default=0, verbose_name='Participating structures count'),
        ),
        migrations.AlterField(
            model_name='certificatelogo',
            name='logo',
            field=models.ImageField(help_text='Seulement des fichiers de type (gif, jpg, png)', upload_to='uploads/certificate_logo/', verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='certificatesignature',
            name='signature',
            field=models.ImageField(help_text='Seulement des fichiers de type (gif, jpg, png)', upload_to='uploads/certificate_signature/', verbose_name='Signature'),
        ),
        migrations.AlterField(
            model_name='course',
            name='structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='core.structure', verbose_name='Structure'),
        ),
        migrations.AlterField(
            model_name='immersionuser',
            name='structures',
            field=models.ManyToManyField(blank=True, related_name='referents', to='core.Structure', verbose_name='Structures'),
        ),
        migrations.AlterField(
            model_name='publicdocument',
            name='document',
            field=models.FileField(help_text='Seulement des fichiers de type (doc,pdf,xls,ods,odt,docx)', upload_to='uploads/publicdocs/%Y', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='training',
            name='structures',
            field=models.ManyToManyField(related_name='Trainings', to='core.Structure', verbose_name='Structures'),
        ),
    ]