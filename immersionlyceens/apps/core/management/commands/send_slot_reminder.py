#!/usr/bin/env python
"""
Send a reminder to all students registered to slots planned in X days
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _
from django.conf import settings
from ...models import Slot, Immersion, ImmersionGroupRecord

from immersionlyceens.libs.utils import get_general_setting
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send slot reminder"), _("success"))
        returns = []
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

        immersions = Immersion.objects.prefetch_related("slot").filter(
            cancellation_type__isnull=True,
            slot__date=slot_date,
            slot__published=True
        )

        for immersion in immersions:
            msg = immersion.student.send_message(None, 'IMMERSION_RAPPEL', slot=immersion.slot, immersion=immersion)

            if msg:
                returns.append(msg)

        group_immersions = ImmersionGroupRecord.objects.prefetch_related("slot", "highschool").filter(
            cancellation_type__isnull=True,
            slot__date=slot_date,
            slot__published=True
        )

        for group_immersion in group_immersions:
            # Send message to group contacts
            msg, error = group_immersion.send_message(None, 'IMMERSION_RAPPEL')

            if error:
                returns.append(msg)

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)


        logger.info(success)
        return success