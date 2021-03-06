# Generated by Django 2.2.10 on 2020-02-05 10:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_merge_20200204_1116'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='component',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='core.Component', verbose_name='Component'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='informationtext',
            name='code',
            field=models.CharField(max_length=64, verbose_name='Code'),
        ),
    ]
