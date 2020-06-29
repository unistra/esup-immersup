#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from ...models import ImmersionUser, Immersion, Slot, Calendar, UniversityYear, Course

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()
        # TODO: calculate annual stats

        # Delete user alerts
        deleted = UserCourseAlert.objects.all().delete()
        if deleted[0]:
            logger.info(_("{} alert(s) deleted".format(deleted[0])))
        else:
            logger.info(_("No alert to delete"))

        # Delete immersion
        deleted = Immersion.objects.all().delete()
        if deleted[0]:
            logger.info(_("{} immersion(s) deleted".format(deleted[0])))
        else:
            logger.info(_("No immersion to delete"))

        # Delete slot
        deleted = Slot.objects.all().delete()
        if deleted[0]:
            logger.info(_("{} slot(s) deleted".format(deleted[0])))
        else:
            logger.info(_("No slot to delete"))

        # Delete ENS, LYC, ETU ImmersionUser
        deleted = ImmersionUser.objects.filter(groups__name__in=['ETU', 'LYC', 'ENS']).delete()
        if deleted[0]:
            logger.info(_("{} account(s) deleted".format(deleted[0])))
        else:
            logger.info(_("No account to delete"))

        # Delete calendar
        deleted = Calendar.objects.all().delete()
        if deleted[0]:
            logger.info(_("{} calendar(s) deleted".format(deleted[0])))
        else:
            logger.info(_("No calendar to delete"))

        # Update purge date
        updated = UniversityYear.objects.filter(active=True).update(purge_date=today)
        if updated == 0:
            logger.info(_('No university year to update'))
        else:
            logger.info(_('University year updated'))

        # Update course publishement
        updated = Course.objects.filter(published=True).update(published=False)
        if updated == 0:
            logger.info(_('No course to update'))
        else:
            logger.info(_('{} course(s) updated'.format(updated)))

