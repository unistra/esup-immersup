# Generated by Django 2.2.11 on 2020-04-21 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0010_auto_20200408_1400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='level',
            field=models.SmallIntegerField(choices=[(1, 'Première'), (2, 'Terminale'), (3, 'Post-bac')], default=1, verbose_name='Level'),
        ),
    ]