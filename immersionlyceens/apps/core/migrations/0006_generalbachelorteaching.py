# Generated by Django 2.2.9 on 2020-01-15 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_coursetype'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneralBachelorTeaching',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=256, unique=True, verbose_name='Label')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'General bachelor specialty teaching',
                'verbose_name_plural': 'General bachelor specialties teaching',
            },
        ),
    ]