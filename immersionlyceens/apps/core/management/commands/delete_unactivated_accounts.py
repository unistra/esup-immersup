#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from ...models import ImmersionUser
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()

        deleted = ImmersionUser.objects.filter(
            destruction_date__isnull=False,
            destruction_date__lt=today).delete()

        if deleted[0]:
            msg = _('%s account(s) deleted') % deleted[0]
        else:
            msg = _("No account to delete")

        logger.info(msg)
        return msg