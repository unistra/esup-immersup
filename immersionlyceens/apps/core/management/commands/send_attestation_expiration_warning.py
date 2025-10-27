#!/usr/bin/env python
"""
Send a warning about records attestation expiration and renewal
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from ...models import Slot, Immersion

from immersionlyceens.apps.core.models import GeneralSettings, ImmersionUser
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecordDocument, VisitorRecordDocument
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send attestation expiration warnings"), _("success"))
        returns = []
        today = timezone.localdate()

        try:
            expiration_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")
        except Exception as e:
            msg = _("ATTESTATION_DOCUMENT_DEPOSIT_DELAY setting is missing, please check your configuration.")
            logger.error(msg, exc_info=e)
            raise CommandError(msg)

        expiration_date = today + datetime.timedelta(days=expiration_delay)

        # Get students and visitors
        users = ImmersionUser.objects\
            .prefetch_related("high_school_student_record__attestation", "visitor_record__attestation")\
            .filter(
                Q(high_school_student_record__attestation__validity_date__lte=expiration_date,
                  high_school_student_record__attestation__renewal_email_sent=False) |
                Q(visitor_record__attestation__validity_date__lte=expiration_date,
                  visitor_record__attestation__renewal_email_sent=False)
            ).distinct()

        for user in users:
            msg = user.send_message(None, 'CPT_DEPOT_PIECE')

            if msg:
                returns.append(
                    _("Error while sending CPT_DEPOT_PIECE email to student '%s' : %s") % (user.email, msg)
                )
            else:
                # Update 'renewal_email_sent' for each attestation that match the expiration delay
                record = user.get_high_school_student_record() or user.get_visitor_record()

                record.attestation\
                    .filter(validity_date__lte=expiration_date)\
                    .update(renewal_email_sent=True)

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)

        logger.info(success)
        return success

