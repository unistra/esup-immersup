# Generated by Django 2.2.9 on 2020-01-23 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_course'),
    ]

    operations = [
        migrations.CreateModel(
            name='InformationText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=255, verbose_name='Label')),
                ('code', models.CharField(max_length=64, verbose_name='Code')),
                ('content', models.TextField(max_length=2000, verbose_name='Content')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Information text',
                'verbose_name_plural': 'Information texts',
            },
        ),
    ]
