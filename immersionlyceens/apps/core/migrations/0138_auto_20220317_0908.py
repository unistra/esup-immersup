# Generated by Django 3.2.8 on 2022-03-17 08:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0137_auto_20220315_1230'),
    ]

    operations = [
        migrations.AlterField(
            model_name='immersionuser',
            name='highschool',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='core.highschool', verbose_name='High school'),
        ),
        migrations.AlterField(
            model_name='pendingusergroup',
            name='immersionuser1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur 1'),
        ),
        migrations.AlterField(
            model_name='pendingusergroup',
            name='immersionuser2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur 2'),
        ),
    ]