# Generated by Django 3.2.12 on 2022-05-04 09:16

from django.db import migrations, models
import immersionlyceens.apps.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0027_remove_visitorrecord_civility'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitorrecord',
            name='parental_auth_document',
            field=models.FileField(blank=True, help_text='Seulement des fichiers de type (jpg, jpeg, png). Taille max : 20,0\xa0Mio', null=True, upload_to=immersionlyceens.apps.core.models.get_file_path, verbose_name='Parental authorization'),
        ),
    ]
