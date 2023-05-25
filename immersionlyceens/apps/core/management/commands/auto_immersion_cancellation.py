#!/usr/bin/env python
"""
Takes Visitor and High School records with obsolete mandatory attestations, and
cancel all immersions within current day + AUTO_SLOT_UNSUBSCRIBE_DELAY with the reason "attestation out of date"
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from ...models import Slot, Immersion

from immersionlyceens.apps.core.models import CancelType, GeneralSettings, Immersion, ImmersionUser
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecordDocument, VisitorRecordDocument

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()

        try:
            slot_unsubscribe_delay = int(GeneralSettings.get_setting("AUTO_SLOT_UNSUBSCRIBE_DELAY"))
        except:
            logger.error(_("AUTO_SLOT_UNSUBSCRIBE_DELAY missing or invalid, please check your configuration."))
            return

        try:
            cancellation_reason = CancelType.objects.get(code='ATT', system=True)  # reserved cancellation type
        except CancelType.DoesNotExist:
            logger.error(
                _("""'ATT' system cancellation type (out of date attestation) is missing, """
                  """please check your configuration""")
            )
            return

        max_unsubscribe_date = today + datetime.timedelta(days=slot_unsubscribe_delay)

        # Get students and visitors
        users = ImmersionUser.objects\
            .prefetch_related("high_school_student_record__attestation", "visitor_record__attestation")\
            .filter(
                Q(high_school_student_record__attestation__validity_date__lt=today,
                  high_school_student_record__attestation__mandatory=True) |
                Q(visitor_record__attestation__validity_date__lt=today,
                  visitor_record__attestation__mandatory=True)
            ).distinct()

        # Cancel immersions
        immersions = Immersion.objects.filter(
            student__in=users,
            date__gte=today,
            date__lte=max_unsubscribe_date,
            cancellation_reason=None
        )

        for immersion in immersions:
            immersion.cancellation_type = cancellation_reason
            immersion.cancellation_date = now
            immersion.save()
            immersion.student.send_message(None, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)