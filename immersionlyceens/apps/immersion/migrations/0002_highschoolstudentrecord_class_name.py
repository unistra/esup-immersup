# Generated by Django 2.2.10 on 2020-02-13 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschoolstudentrecord',
            name='class_name',
            field=models.CharField(default='', max_length=32, verbose_name='Class name'),
            preserve_default=False,
        ),
    ]
