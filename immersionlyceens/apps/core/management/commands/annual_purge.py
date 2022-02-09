#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging

from datetime import datetime
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from ...models import (ImmersionUser, Immersion, Slot, Calendar, UniversityYear, Course, UserCourseAlert,
    Vacation, Holiday, Visit, OffOfferEvent)
    

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()
        
        # Run annual stats first
        try:
            call_command('annual_statistics')
            finished = True
        except CommandError:
            logger.error("Could not finish 'annual_statistics' command")

        if not finished:
            logger.error(_("Cannot parse annual statistics, purge cancelled"))

        # Delete user alerts
        deleted = UserCourseAlert.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} user alert(s) deleted"))
        else:
            logger.info(_("No user alert to delete"))

        # Delete immersion
        deleted = Immersion.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} immersion(s) deleted"))
        else:
            logger.info(_("No immersion to delete"))

        # Delete slot
        deleted = Slot.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} slot(s) deleted"))
        else:
            logger.info(_("No slot to delete"))

        # Delete ENS, LYC, ETU ImmersionUser
        deleted = ImmersionUser.objects.filter(groups__name__in=['ETU', 'LYC', 'ENS', 'VIS']).delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} account(s) deleted"))
        else:
            logger.info(_("No account to delete"))

        # Delete calendar, vacations and holidays
        deleted = Calendar.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} calendar(s) deleted"))
        else:
            logger.info(_("No calendar to delete"))
            
        deleted = Holiday.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} holiday record(s) deleted"))
        else:
            logger.info(_("No holiday record to delete"))

        deleted = Vacation.objects.all().delete()
        if deleted[0]:
            logger.info(_(f"{deleted[0]} vacation record(s) deleted"))
        else:
            logger.info(_("No vacation record to delete"))

        # Update purge date
        updated = UniversityYear.objects.filter(active=True).update(purge_date=today)
        if updated == 0:
            logger.info(_('No university year to update'))
        else:
            logger.info(_('University year updated'))

        # Update course, visitor, event publishement
        updated = Course.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No course to update'))
        else:
            logger.info(_(f'{updated} course(s) updated'))

        updated = Visit.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No visit to update'))
        else:
            logger.info(_(f'{updated} visit(s) updated'))

        updated = OffOfferEvent.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No visit to update'))
        else:
            logger.info(_(f'{updated} visit(s) updated'))


