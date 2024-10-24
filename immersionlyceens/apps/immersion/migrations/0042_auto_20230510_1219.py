# Generated by Django 3.2.18 on 2023-05-10 10:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0174_auto_20230510_1219'),
        ('immersion', '0041_alter_studentrecord_origin_bachelor_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='general_bachelor_teachings',
            field=models.ManyToManyField(blank=True, related_name='student_records', to='core.GeneralBachelorTeaching', verbose_name='General bachelor teachings'),
        ),
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='technological_bachelor_mention',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_records', to='core.bachelormention', verbose_name='Technological bachelor mention'),
        ),
    ]
