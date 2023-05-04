#!/usr/bin/env python
"""
Send a warning about records attestation expiration and renewal
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from ...models import Slot, Immersion

from immersionlyceens.apps.core.models import GeneralSettings
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecordDocument, VisitorRecordDocument

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = timezone.localdate()

        try:
            expiration_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")
        except:
            logger.error(_("ATTESTATION_DOCUMENT_DEPOSIT_DELAY setting is missing, please check your configuration."))
            return

        expiration_date = today + datetime.timedelta(days=expiration_delay)

        # No union since we have to update Documents 'sent' flags

        # students
        students = HighSchoolStudentRecordDocument.objects.prefetch_related("record__student") \
            .filter(validity_date__lte=expiration_date) \
            .values('record__student') \
            .distinct()

        for user in students:
            msg = user.send_message(None, 'CPT_DEPOT_PIECE')
            if msg:
                logger.error(
                    _("Error while sending CPT_DEPOT_PIECE email to student '%s' : %s") % (user.email, msg)
                )
            else:
                user.high_school_student_record.attestation\
                    .filter(validity_date__lte=expiration_date)\
                    .update(renewal_email_sent=True)

        # visitors
        visitors = VisitorRecordDocument.objects.prefetch_related("record__visitor") \
            .filter(validity_date__lte=expiration_date) \
            .values('record__visitor') \
            .distinct()

        for user in visitors:
            msg = user.send_message(None, 'CPT_DEPOT_PIECE')
            if msg:
                logger.error(
                    _("Error while sending CPT_DEPOT_PIECE email to visitor '%s' : %s") % (user.email, msg)
                )
            else:
                user.visitor_record.attestation \
                    .filter(validity_date__lte=expiration_date) \
                    .update(renewal_email_sent=True)