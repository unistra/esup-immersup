#!/usr/bin/env python
"""
Takes Visitor and High School records with obsolete mandatory attestations, and
cancel all immersions within current day + AUTO_SLOT_UNSUBSCRIBE_DELAY with the reason "attestation out of date"
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils import timezone
from . import Schedulable

from immersionlyceens.apps.core.models import CancelType, GeneralSettings, Immersion, ImmersionUser

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def handle(self, *args, **options):
        success = "%s : %s" % (_("Immersion cancellations"), _("success"))
        today = timezone.localdate()
        now = timezone.now()

        try:
            slot_unsubscribe_delay = int(GeneralSettings.get_setting("AUTO_SLOT_UNSUBSCRIBE_DELAY"))
        except:
            msg = _("AUTO_SLOT_UNSUBSCRIBE_DELAY missing or invalid, please check your configuration.")
            logger.error(msg)
            raise CommandError(msg)

        try:
            cancellation_reason = CancelType.objects.get(code='ATT', system=True)  # reserved cancellation type
        except CancelType.DoesNotExist:
            msg = _("""'ATT' system cancellation type (out of date attestation) is missing, """
                  """please check your configuration""")
            logger.error(msg)
            raise CommandError(msg)

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
        immersions = Immersion.objects.prefetch_related("slot").filter(
            student__in=users,
            slot__date__gte=today,
            slot__date__lte=max_unsubscribe_date,
            cancellation_type__isnull=True
        )

        for immersion in immersions:
            immersion.cancellation_type = cancellation_reason
            immersion.cancellation_date = now
            immersion.save()
            immersion.student.send_message(None, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

        logger.info(success)
        return success