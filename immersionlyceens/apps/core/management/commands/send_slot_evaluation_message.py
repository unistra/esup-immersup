#!/usr/bin/env python
"""
Send a message containing a survey link
"""
import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ...models import EvaluationFormLink, Immersion, Slot
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send slot evaluation message"), _("success"))
        returns = []
        today = datetime.datetime.today().date()
        now = datetime.datetime.now().time() # to filter on slot end_time

        # Email template
        try:
            eval_link = EvaluationFormLink.objects.get(evaluation_type__code='EVA_CRENEAU', active=True)
            logger.debug("Evaluation link found : %s" % eval_link)
        except EvaluationFormLink.DoesNotExist:
            msg = _("Cannot find an active evaluation link. Please check the Evaluation forms links in admin section.")
            logger.error(msg)
            raise CommandError(msg)

        immersions = Immersion.objects.prefetch_related("slot").filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now),
            cancellation_type__isnull = True,
            survey_email_sent = False
        )

        for immersion in immersions:
            msg = immersion.student.send_message(None, 'EVALUATION_CRENEAU', slot=immersion.slot, immersion=immersion)

            # Keep mail errors
            if msg:
                returns.append(msg)
            else:
                immersion.survey_email_sent=True
                immersion.save()

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)


        logger.info(success)
        return success




