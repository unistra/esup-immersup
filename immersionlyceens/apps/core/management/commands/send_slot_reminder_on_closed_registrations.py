#!/usr/bin/env python
"""
Send a reminder to speakers for upcoming slots
"""
import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import Immersion, ImmersionUser, RefStructuresNotificationsSettings, Slot
from . import Schedulable

logger = logging.getLogger(__name__)


class Command(BaseCommand, Schedulable):
    """Sends speakers & structures managers notifcations for slots reminders"""

    def handle(self, *args, **options):
        success = "%s : %s" % (
            _("Send slot reminder on closed registration"),
            _("success"),
        )
        returns = []
        today = timezone.now()

        slots = Slot.objects.filter(
            registration_limit_date__lte=today,
            published=True,
            reminder_notification_sent=False,
        )

        for slot in slots:
            if slot.registered_students() > 0:
                # Speakers
                for speaker in slot.speakers.all():
                    msg = speaker.send_message(None, "IMMERSION_RAPPEL_INT", slot=slot)
                    if msg:
                        returns.append(msg)
                # Structures managers
                try:
                    slot_structure = slot.get_structure()
                    str_managers = ImmersionUser.objects.filter(
                        groups__name="REF-STR",
                        structures__in=[
                            slot_structure.pk,
                        ],
                    )
                    for s in str_managers:
                        if RefStructuresNotificationsSettings.objects.filter(
                            user=s,
                            structures__in=[
                                slot_structure.pk,
                            ],
                        ).exists():
                            msg = s.send_message(
                                None, "IMMERSION_RAPPEL_STR", slot=slot
                            )
                            if msg:
                                returns.append(msg)
                except Exception as e:
                    print(e)

                slot.reminder_notification_sent = True
                slot.save()

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)

        logger.info(success)
        return success
