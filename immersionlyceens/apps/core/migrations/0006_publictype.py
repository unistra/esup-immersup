# Generated by Django 2.2.9 on 2020-01-15 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_coursetype'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=256, unique=True, verbose_name='Label')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Public type',
                'verbose_name_plural': 'Public type',
            },
        ),
    ]
