#!/usr/bin/env python
"""
Send a reminder to speakers for upcoming slots
"""
import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import Immersion, Slot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        today = datetime.datetime.today().date()
        default_value = 4

        # settings / default value
        try:
            days = settings.DEFAULT_NB_DAYS_SPEAKER_SLOT_REMINDER
        except AttributeError:
            days = default_value

        # Configured value
        try:
            days = int(get_general_setting('NB_DAYS_SPEAKER_SLOT_REMINDER'))
        except (ValueError, NameError):
            pass

        # If configured value is invalid
        if days <= 0:
            days = default_value

        # ================
        slot_date = today + datetime.timedelta(days=days)
        slots = Slot.objects.filter(date=slot_date, published=True)

        for slot in slots:
            for speaker in slot.speakers.all():
                speaker.send_message(None, 'IMMERSION_RAPPEL_INT', slot=slot)

