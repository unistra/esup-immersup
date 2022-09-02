#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from ...models import (
    Calendar, Course, Holiday, Immersion, ImmersionUser, OffOfferEvent, Slot,
    UniversityYear, UserCourseAlert, Vacation, Visit,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()

        # Run annual stats first
        try:
            call_command('annual_statistics')
        except CommandError:
            logger.error(_("Could not finish 'annual_statistics' command, purge cancelled"))
            raise

        # Delete user alerts
        deleted = UserCourseAlert.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} user alert(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No user alert to delete"))

        # Delete immersion
        deleted = Immersion.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} immersion(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No immersion to delete"))

        # Delete slot
        deleted = Slot.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} slot(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No slot to delete"))

        # Delete ENS, LYC, ETU ImmersionUser
        deleted = ImmersionUser.objects.filter(groups__name__in=['ETU', 'LYC', 'ENS', 'VIS']).delete()
        if deleted[0]:
            logger.info(_('{} account(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No account to delete"))

        # Delete calendar, vacations and holidays
        deleted = Calendar.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} calendar(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No calendar to delete"))

        deleted = Holiday.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} holiday record(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No holiday record to delete"))

        deleted = Vacation.objects.all().delete()
        if deleted[0]:
            logger.info(_('{} vacation record(s) deleted').format(deleted[0]))
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
            logger.info(_('{} course(s) updated').format(updated))

        updated = Visit.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No visit to update'))
        else:
            logger.info(_('{} visit(s) updated').format(updated))

        updated = OffOfferEvent.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No visit to update'))
        else:
            logger.info(_('{} visit(s) updated').format(updated))


        # deactivate immersion users with group INTER and in an establishment with plugin set
        deleted = ImmersionUser.objects.filter(
            groups__name__in=("INTER",),
            establishment__data_source_plugin__isnull=False
        ).delete()
        if deleted[0]:
            logger.info(_('{} user(s) with group INTER and with LDAP establishment deleted').format(deleted[0]))
        else:
            logger.info(_("no user with group INTER and with LDAP establishment to delete"))


        # Delete immersion user with group INTER and in an establishment without SI
        updated = ImmersionUser.objects.filter(
            groups__name__in=("INTER",),
            establishment__data_source_plugin__isnull=True
        ).update(is_active=False)
        if updated:
            logger.info(_('{} user(s) with group INTER and with establishment without SI deactivated').format(updated))
        else:
            logger.info(_("no user with group INTER and with LDAP establishment to deactivate"))

        try:
            call_command('delete_account_not_in_ldap')
        except CommandError:
            logger.error("Could not finish 'delete_account_not_in_ldap' command")
