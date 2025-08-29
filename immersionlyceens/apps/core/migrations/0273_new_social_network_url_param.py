from django.db import migrations

def update_social_settings(apps, schema_editor):
    GeneralSettings = apps.get_model('core', 'GeneralSettings')

    old_setting = GeneralSettings.objects.filter(setting='SOCIAL_NETWORK_URL').first()
    if old_setting:
        old_setting.delete()

    new_data = {
        "type": "object",
        "value": {
            "twitter": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "facebook": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "instagram": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "linkedin": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "youtube": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "university_website": {
                "activate": False,
                "logo": "image",
                "url": "url"
            },
            "divers": {
                "activate": False,
                "name": "name",
                "logo": "image",
                "url": "url"
            },
        },
        "description": "Différents réseaux sociaux de l'université"
    }

    if not GeneralSettings.objects.filter(setting='SOCIAL_ACCOUNT_URL').exists():
        GeneralSettings.objects.create(setting='SOCIAL_ACCOUNT_URL', parameters=new_data)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0272_immersionuser_email_change_date_and_more'),
    ]

    operations = [
        migrations.RunPython(update_social_settings),
    ]