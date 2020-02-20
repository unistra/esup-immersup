#!/usr/bin/env python
"""
Send pending highschool students accounts validations notifications to high school referents
"""
import logging

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from ...models import HighSchool

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """ Import components from Abyla
    """

    def handle(self, *args, **options):
        highschools = HighSchool.objects.filter(student_records__validation=1).distinct()

        for highschool in highschools:
            referents = highschool.highschool_referent.all()

            for referent in referents:
                referent.send_message(None, 'CPT_AVALIDER_LYCEE')