from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _
from django.conf import settings

from . import Schedulable

class Command(BaseCommand, Schedulable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.DEBUG:
            self.schedulable = False


    def handle(self, *args, **options):
        return _("Cron test success")
