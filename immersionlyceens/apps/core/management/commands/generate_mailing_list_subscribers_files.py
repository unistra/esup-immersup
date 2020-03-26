#!/usr/bin/env python
"""
Generate files containing mailing-lists subscribers
- one file for the global mailing-list (every student registered to a slot)
- one file for each component (every student registered to at list one slot under the component)
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from ...models import GeneralSettings, Slot, Immersion, Component, Vacation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        all_registered_fd = open(settings.ML_ALL, "w")

        for component in Component.objects.all():
