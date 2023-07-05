from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission

class Command(BaseCommand):
    help = 'Fixes permissions names'

    def handle(self, *args, **options):
        for p in Permission.objects.filter(content_type__app_label="core"):
            if not p.content_type.model_class():
                print(f"{p.codename} has no model class : delete")
                p.delete()
            else:
                try:
                    p.name = "Can %s %s"%(p.codename.split('_')[0], p.content_type.model_class()._meta.verbose_name)
                    p.save()
                except AttributeError as e:
                    print(f"Permission {p} (name : {p.codename}) : {e}")

