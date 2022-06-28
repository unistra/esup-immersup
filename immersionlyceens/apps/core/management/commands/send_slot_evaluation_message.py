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

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.datetime.today().date()
        now = datetime.datetime.now().time() # to filter on slot end_time

        # Email template
        try:
            eval_link = EvaluationFormLink.objects.get(evaluation_type__code='EVA_CRENEAU', active=True)
            logger.debug("Evaluation link found : %s" % eval_link)
        except EvaluationFormLink.DoesNotExist:
            # template code ? it's a copy past ?
            # logger.error("Cannot find an active evaluation link. Please check the Evaluation forms links in admin section.", template_code)
            logger.error("Cannot find an active evaluation link. Please check the Evaluation forms links in admin section.")
            return

        immersions = Immersion.objects.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now),
            cancellation_type__isnull = True,
            survey_email_sent = False
        )

        for immersion in immersions:
            immersion.student.send_message(None, 'EVALUATION_CRENEAU', slot=immersion.slot, immersion=immersion)
            immersion.survey_email_sent=True
            immersion.save()

            # Todo : gestion des erreurs d'envoi ?
