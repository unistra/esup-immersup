#!/usr/bin/env python
"""
Send a reminder to all students registered to slots planned in X days
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from ...models import Slot, Immersion

from immersionlyceens.libs.utils import get_general_setting

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.datetime.today().date()
        default_value = 4

        # settings / default value
        try:
            days = settings.DEFAULT_NB_DAYS_SLOT_REMINDER
        except AttributeError:
            days = default_value

        # Configured value
        try:
            days = int(get_general_setting('NB_DAYS_SLOT_REMINDER'))
        except (ValueError, NameError):
            pass

        # If configured value is invalid
        if days <= 0:
            days = default_value

        slot_date = today + datetime.timedelta(days=days)

        immersions = Immersion.objects.filter(
            cancellation_type__isnull=True, slot__date=slot_date, slot__published=True)

        for immersion in immersions:
            immersion.student.send_message(None, 'IMMERSION_RAPPEL', slot=immersion.slot, immersion=immersion)
            # Todo : gestion des erreurs d'envoi ?
