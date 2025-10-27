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
from immersionlyceens.views import highschools

from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    Base import command
    """
    def handle(self, *args, **options):
        url = settings.UAI_API_URL
        header = settings.UAI_API_AUTH_HEADER
        headers = {}
        returns = []
        results = []
        creations = 0
        updates = 0

        if not all([url, header]):
            msg = _("UAI update error : missing url and/or header parameters.")
            logger.error(msg)
            return msg

        # convert headers to dict
        for h in header.split(";"):
            try:
                headers.update({
                    h.split(':')[0].strip(): h.split(':')[1].strip()
                })
            except:
                continue

        try:
            results = get_json_from_url(f"{url}", headers=headers)
            if isinstance(results, dict):
                if results.get("http_status_code", None) != 200:
                    raise RuntimeError("Status %s : %s" % (results.get("http_status_code"), results.get("message")))
        except Exception as e:
            logger.error("Error (get_json_from_url) %s" % e)
            returns.append(_("UAI update error (get_json_from_url) : %s") % e)
            return "\n".join(returns)

        if results:
            # Clean unused UAI codes
            deleted = UAI.objects.filter(highschools__isnull=True).delete()
            returns.append(_("%s unused UAI deleted") % deleted[0])

        for result in results:
            code = result.get('code', None)

            data = {
                'city': result.get('city', None),
                'academy': result.get('academy', None),
                'label': result['label'],
            }

            try:
                _obj, created = UAI.objects.update_or_create(
                    code=code,
                    defaults=data
                )

                if created:
                    creations += 1
                else:
                    updates += 1
            except Exception as e:
                logger.error("Error %s" % e)
                data_txt = ", ".join([f"{k}={v}" for k, v in data.items()])

                returns.append(
                    _("UAI update : cannot update_or_create : %(error)s : code %(code)s, %(data)s")
                    % {'error': e, 'code': code, 'data': data_txt}
                )

        returns.append(_("%s UAI created") % creations)
        returns.append(_("%s UAI updated") % updates)

        # Message return for scheduler logs
        return "\n".join(returns)
