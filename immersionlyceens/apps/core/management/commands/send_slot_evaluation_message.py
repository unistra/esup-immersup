#!/usr/bin/env python
"""
Send a message containing a survey link
"""
import logging

import datetime
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from ...models import GeneralSettings, Slot, Immersion

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        today = datetime.datetime.today().date()
        now = datetime.datetime.now().time() # to filter on slot end_time

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