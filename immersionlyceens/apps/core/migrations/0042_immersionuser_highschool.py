# Generated by Django 2.2.9 on 2020-02-12 13:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_merge_20200212_1122'),
    ]

    operations = [
        migrations.AddField(
            model_name='immersionuser',
            name='highschool',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='highschool_referent', to='core.HighSchool', verbose_name='High school'),
        ),
    ]