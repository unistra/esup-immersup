#!/usr/bin/env python
"""
Send a reminder to speakers for upcoming slots
"""
import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import Immersion, ImmersionUser, RefStructuresNotificationsSettings, Slot
from . import Schedulable

logger = logging.getLogger(__name__)


class Command(BaseCommand, Schedulable):
    """ """

    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send speaker slot reminder"), _("success"))
        returns = []
        today = timezone.now()
        default_value = 4

        # settings / default value
        try:
            days = settings.DEFAULT_NB_DAYS_SPEAKER_SLOT_REMINDER
        except AttributeError:
            days = default_value

        # Configured value
        try:
            days = int(get_general_setting("NB_DAYS_SPEAKER_SLOT_REMINDER"))
        except (ValueError, NameError):
            pass

        # If configured value is invalid
        if days <= 0:
            days = default_value

        # ================
        slot_date = today.date() + datetime.timedelta(days=days)
        slots = Slot.objects.filter(
            date=slot_date,
            published=True,
            registration_limit_date__gt=today,
            reminder_notification_sent=False,
        )

        for slot in slots:
            # TODO: if we should optimise this come from Immersion and not from Slot !!!
            if slot.registered_students() > 0 or slot.group_immersions.exists():
                # Speakers
                for speaker in slot.speakers.all():
                    msg = speaker.send_message(None, "IMMERSION_RAPPEL_INT", slot=slot)
                    if msg:
                        returns.append(msg)

                # Structures managers
                slot_structure = slot.get_structure()

                if slot_structure:
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
                            msg = s.send_message(None, "IMMERSION_RAPPEL_STR", slot=slot)
                            if msg:
                                returns.append(msg)

                # High school managers if it's a high school slot (course or event)
                highschool = slot.get_highschool()

                if highschool:
                    # Get this high school managers
                    # Check the message preferences (False by default)
                    # Send the same message template
                    for manager in highschool.users.filter(groups__name='REF-LYC'):
                        if manager.get_preference("RECEIVE_REGISTERED_STUDENTS_LIST", False):
                            msg = manager.send_message(None, "IMMERSION_RAPPEL_STR", slot=slot)

                            if msg:
                                msg = (_("Cannot send high school manager slot reminder to %(email)s : %(msg)s")
                                       % {'email': manager.email, 'msg': msg}
                                )
                                returns.append(msg)

        # Format and return the errors to the cron master
        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)

        logger.info(success)
        return success
