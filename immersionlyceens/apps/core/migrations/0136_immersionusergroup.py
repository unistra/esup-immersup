# Generated by Django 3.2.12 on 2022-03-15 05:57

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0135_immersionuser_creation_email_sent'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImmersionUserGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('immersionusers', models.ManyToManyField(related_name='siblings', to=settings.AUTH_USER_MODEL, verbose_name='Group members')),
            ],
            options={
                'verbose_name': 'User group',
                'verbose_name_plural': 'User groups',
                'ordering': ['pk'],
            },
        ),
    ]