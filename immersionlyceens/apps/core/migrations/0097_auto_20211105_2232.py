# Generated by Django 3.2.8 on 2021-11-05 21:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0096_auto_20211104_1646'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accompanyingdocument',
            name='document',
            field=models.FileField(help_text='Seulement des fichiers de type (doc, pdf, xls, ods, odt, docx). Taille max : 20,0\xa0Mio', upload_to='uploads/accompanyingdocs/%Y', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='publicdocument',
            name='document',
            field=models.FileField(help_text='Seulement des fichiers de type (doc, pdf, xls, ods, odt, docx). Taille max : 20,0\xa0Mio', upload_to='uploads/publicdocs/%Y', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='training',
            name='structures',
            field=models.ManyToManyField(blank=True, related_name='Trainings', to='core.Structure', verbose_name='Structures'),
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purpose', models.CharField(max_length=256, verbose_name='Purpose')),
                ('published', models.BooleanField(default=True, verbose_name='Published')),
                ('establishment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='core.establishment', verbose_name='Establishment')),
                ('highschool', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='core.highschool', verbose_name='High school')),
                ('speakers', models.ManyToManyField(related_name='visits', to=settings.AUTH_USER_MODEL, verbose_name='Speakers')),
                ('structure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visits', to='core.structure', verbose_name='Structure')),
            ],
            options={
                'verbose_name': 'Visit',
                'verbose_name_plural': 'Visits',
            },
        ),
    ]