#!/usr/bin/env python
"""
Delete unactivated accounts
"""
import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from ...models import ImmersionUser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.today().date()

        deleted = ImmersionUser.objects.filter(
            destruction_date__isnull=False,
            destruction_date__lt=today).delete()

        if deleted[0]:
            logger.info(_('{} account(s) deleted').format(deleted[0]))
        else:
            logger.info(_("No account to delete"))
