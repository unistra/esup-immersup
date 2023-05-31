from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from . import Schedulable

class Command(BaseCommand, Schedulable):
    def handle(self, *args, **options):
        with open("/tmp/immersion_cron_test", "a") as f:
            f.write(f"{timezone.now()}\n")

