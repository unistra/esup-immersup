# Generated by Django 3.2.18 on 2023-05-04 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('immersion', '0038_auto_20230422_1825'),
    ]

    operations = [
        migrations.AddField(
            model_name='highschoolstudentrecorddocument',
            name='renewal_email_sent',
            field=models.BooleanField(default=False, verbose_name='Renewal warning email sent'),
        ),
        migrations.AddField(
            model_name='visitorrecorddocument',
            name='renewal_email_sent',
            field=models.BooleanField(default=False, verbose_name='Renewal warning email sent'),
        ),
        migrations.AlterField(
            model_name='highschoolstudentrecord',
            name='validation',
            field=models.SmallIntegerField(choices=[(0, 'To complete'), (1, 'To validate'), (2, 'Validated'), (3, 'Rejected'), (4, 'To revalidate')], default=0, verbose_name='Validation'),
        ),
        migrations.AlterField(
            model_name='visitorrecord',
            name='validation',
            field=models.SmallIntegerField(choices=[(0, 'To complete'), (1, 'To validate'), (2, 'Validated'), (3, 'Rejected'), (4, 'To revalidate')], default=0, verbose_name='Validation'),
        ),
    ]