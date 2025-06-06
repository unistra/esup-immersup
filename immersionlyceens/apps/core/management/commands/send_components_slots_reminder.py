#!/usr/bin/env python
"""
Send a reminder to structures referents for upcoming slots in N weeks
This command is made to be run once a week (any day)
"""
import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import HighSchool, Immersion, Slot, Structure, Vacation
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """
    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send components slots reminder"), _("success"))
        returns = []
        today = datetime.datetime.today().date()

        default_value = 1

        # settings / default value
        try:
            weeks = settings.DEFAULT_NB_WEEKS_STRUCTURES_SLOT_REMINDER
        except AttributeError:
            weeks = default_value

        # Configured value
        try:
            weeks = int(get_general_setting('NB_WEEKS_STRUCTURES_SLOT_REMINDER'))
        except (ValueError, NameError):
            pass

        # If configured value is invalid
        if weeks <= 0:
            weeks = default_value

        # ================
        structures = Structure.objects.filter(active=True)

        # if tomorrow (today+1) is a vacation day, don't send any reminder
        if Vacation.date_is_inside_a_vacation(today + datetime.timedelta(days=1)):
            return success

        # from (today + N weeks) to (today + N weeks + 6 days)
        slot_min_date = today + datetime.timedelta(weeks=weeks)

        # if min_date is in a vacation period, extend max_date to the end of the period + 1 week
        vacation_period = Vacation.get_vacation_period(slot_min_date)
        if vacation_period:
            slot_max_date = vacation_period.end_date + datetime.timedelta(weeks=1)
        else:
            slot_max_date = slot_min_date + datetime.timedelta(days=6) # interval = 6 days

        logger.debug("%s - sending reminders for slots between %s and %s (N = %s week(s))",
            today, slot_min_date, slot_max_date, weeks
        )

        for structure in structures:
            slot_list = [
                s for s in Slot.objects.prefetch_related("course__structure", "event__structure")
                    .filter(
                        Q(course__structure=structure)|Q(event__structure=structure),
                        date__gte=slot_min_date,
                        date__lte=slot_max_date,
                        published=True
                    ).order_by('date', 'start_time')
            ]

            logger.debug("======= Structure : %s", structure.label)
            for s in slot_list:
                logger.debug(s.__dict__)

            if slot_list:
                for referent in structure.referents.all():
                    msg = referent.send_message(None, 'RAPPEL_STRUCTURE', slot_list=slot_list)

                    if msg:
                        msg = _("Cannot send components slot reminder to %s : %s") % (referent.email, msg)
                        returns.append(msg)

        # Format and return the errors to the cron master
        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)

        logger.info(success)
        return success
