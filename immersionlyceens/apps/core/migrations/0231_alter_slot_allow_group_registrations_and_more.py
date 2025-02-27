# Generated by Django 5.0.4 on 2024-05-15 08:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0230_alter_slot_allow_group_registrations_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='slot',
            name='allow_group_registrations',
            field=models.BooleanField(default=False, verbose_name='Allow group registrations'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='allow_individual_registrations',
            field=models.BooleanField(default=True, verbose_name='Allow individual registrations'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='group_mode',
            field=models.SmallIntegerField(blank=True, choices=[(0, 'One group'), (1, 'By number of places')], default=0, null=True, verbose_name='Group management mode'),
        ),
        migrations.AlterField(
            model_name='slot',
            name='public_group',
            field=models.BooleanField(default=False, verbose_name='Public group registrations'),
            preserve_default=False,
        ),
    ]
