#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _
from django.db.models import Count

from . import Schedulable

from ...models import (
    Course, History, Holiday, Immersion, ImmersionUser, OffOfferEvent, Slot,
    Period, UniversityYear, UserCourseAlert, Vacation
)

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()

        returns = []

        # Run annual stats first
        try:
            call_command('annual_statistics')
        except CommandError:
            logger.error(_("Could not finish 'annual_statistics' command, purge cancelled"))
            raise

        # Delete user alerts
        deleted = UserCourseAlert.objects.all().delete()
        if deleted[0]:
            returns.append(_('{} user alert(s) deleted').format(deleted[0]))
        else:
            returns.append(_("No user alert to delete"))

        # Delete immersion
        deleted = Immersion.objects.all().delete()
        if deleted[0]:
            returns.append(_('{} immersion(s) deleted').format(deleted[0]))
        else:
            returns.append(_("No immersion to delete"))

        # Delete slot
        deleted = Slot.objects.all().delete()
        if deleted[0]:
            try:
                slots_deleted = deleted[1]["core.Slot"]
                returns.append(_('{} slot(s) deleted').format(slots_deleted))
            except (IndexError, KeyError):
                returns.append(_('Slot(s) deleted'))
        else:
            returns.append(_("No slot to delete"))

        # Delete ENS, LYC, ETU ImmersionUser
        deleted = ImmersionUser.objects.filter(groups__name__in=['ETU', 'LYC', 'VIS']).delete()
        if deleted[0]:
            try:
                accounts_deleted = deleted[1]["core.ImmersionUser"]
                returns.append(_('{} account(s) deleted').format(accounts_deleted))
            except (IndexError, KeyError):
                returns.append(_('Account(s) deleted'))
        else:
            returns.append(_("No account to delete"))

        # Delete periods, vacations and holidays
        deleted = Period.objects.all().delete()
        if deleted[0]:
            try:
                periods_deleted = deleted[1]["core.Period"]
                returns.append(_('{} period(s) deleted').format(periods_deleted))
            except (IndexError, KeyError):
                returns.append(_('Period(s) deleted'))
        else:
            returns.append(_("No period to delete"))

        deleted = Holiday.objects.all().delete()
        if deleted[0]:
            returns.append(_('{} holiday record(s) deleted').format(deleted[0]))
        else:
            returns.append(_("No holiday record to delete"))

        deleted = Vacation.objects.all().delete()
        if deleted[0]:
            returns.append(_('{} vacation record(s) deleted').format(deleted[0]))
        else:
            returns.append(_("No vacation record to delete"))

        # Update purge date
        updated = UniversityYear.objects.filter(active=True).update(purge_date=today)
        if updated == 0:
            returns.append(_('No university year to update'))
        else:
            returns.append(_('University year updated'))


        # Update course, and event publishement
        updated = Course.objects.filter(published=True).update(published=False)
        if updated == 0:
            returns.append(_('No course to update'))
        else:
            returns.append(_('{} course(s) updated').format(updated))

        updated = OffOfferEvent.objects.filter(published=True).update(published=False)
        if updated == 0:
            returns.append(_('No event to update'))
        else:
            returns.append(_('{} event(s) updated').format(updated))


        # delete immersion users with group INTER and in an establishment with plugin set
        deleted = ImmersionUser.objects.annotate(cnt=Count('groups__name')).filter(
            cnt=1,
            groups__name='INTER',
            establishment__data_source_plugin__isnull = False
        ).delete()

        if deleted[0]:
            returns.append(_('{} user(s) with group INTER and with LDAP establishment deleted').format(deleted[0]))
        else:
            returns.append(_("no user with group INTER and with LDAP establishment to delete"))


        # Deactivate immersion user with group INTER and in an establishment without SI
        updated = ImmersionUser.objects.annotate(cnt=Count('groups__name')).filter(
            cnt=1,
            groups__name__in=("INTER",),
            establishment__data_source_plugin__isnull=True
        ).update(is_active=False)

        if updated:
            returns.append(_('{} user(s) with group INTER and with establishment without SI deactivated').format(updated))
        else:
            returns.append(_("no user with group INTER and with LDAP establishment to deactivate"))

        try:
            call_command('delete_account_not_in_ldap')
        except Exception as e:
            returns.append(_("Could not finish 'delete_account_not_in_ldap' command : %s") % e)

        # Clean History
        History.objects.all().delete()

        # Log all
        for line in returns:
            logger.info(line)

        # Message return for scheduler logs
        return "\n".join(returns)