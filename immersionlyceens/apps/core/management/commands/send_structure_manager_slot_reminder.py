#!/usr/bin/env python
"""
Send a reminder to structures manager for upcoming slots
"""
import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import (
    Immersion, ImmersionUser, Period, RefStructuresNotificationsSettings, Slot,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        today = timezone.now()

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
        # ================
        slot_date = today.date() + datetime.timedelta(days=days)
        slots = Slot.objects.filter(date=slot_date, published=True)

        for slot in slots:
            slot_structure = slot.get_structure()
            # < !!!
            if slot.registration_limit_date > today:
                str_managers = ImmersionUser.objects.filter(groups__name='REF-STR', structures__in=[slot_structure.id,])
                for s in str_managers:
                    if RefStructuresNotificationsSettings.objects.filter(user=s, structures__in=[slot_structure.pk,]).exists():
                        s.send_message(None, 'IMMERSION_RAPPEL_STR', slot=slot)
