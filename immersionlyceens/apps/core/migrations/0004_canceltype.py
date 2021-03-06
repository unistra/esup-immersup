# Generated by Django 2.2.9 on 2020-01-14 13:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_training'),
    ]

    operations = [
        migrations.CreateModel(
            name='CancelType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=256, unique=True, verbose_name='Label')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Cancel type',
                'verbose_name_plural': 'Cancel types',
            },
        ),
    ]
