#!/usr/bin/env python
"""
Import higher education institutions from an opendata platform
"""
import logging
import requests
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from immersionlyceens.apps.core.models import HigherEducationInstitution
from django.utils.translation import gettext_lazy as _

from immersionlyceens.libs.api_utils import get_json_from_url

from immersionlyceens.apps.core.models import UAI

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Base import command
    """
    def handle(self, *args, **options):
        url = settings.UAI_API_URL
        header = settings.UAI_API_AUTH_HEADER

        results = []

        if not all([url, header]):
            logger.error("Missing or invalid parameters.")

        # convert headers to dict
        try:
            headers = {header.split(':')[0].strip(): header.split(':')[1].strip()}
        except:
            headers = {}

        try:
            results = get_json_from_url(f"{url}", headers=headers)

            for result in results:
                UAI.objects.update_or_create(
                    uai_code=result['code'],
                    defaults = {
                        'city': None or result['city'],
                        'academy': None or result['academy'],
                        'label': result['label'],
                    }
                )

        except Exception as e:
            logger.error("Error %s" % (e))
