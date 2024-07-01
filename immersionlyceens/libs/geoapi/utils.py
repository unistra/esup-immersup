import logging
import sys

import requests
from django.conf import settings

from ..api_utils import get_json_from_url

logger = logging.getLogger(__name__)


def get_departments():
    try:
        results = get_json_from_url('%s/departements?fields=nom,code' % settings.GEOAPI_BASE_URL)
        return [(r['code'], r['nom']) for r in results]

    except Exception as e:
        logger.error("Error %s" % (e))
        return ''


def get_cities(dep_code=None):
    try:
        if dep_code:
            results = get_json_from_url(
                f'{settings.GEOAPI_BASE_URL}/departements/{dep_code}/communes/?fields=nom'
            )
            return [(r['nom'].upper(), r['nom'].upper()) for r in results]
        return []

    except Exception as e:
        logger.error("Error %s" % (e))
        return []


def get_zipcodes(dep_code=None, city=None):
    zipcodes = []
    try:
        if city:
            results = get_json_from_url(
                '%s/departements/%s/communes/?fields=nom,codesPostaux'
                % (settings.GEOAPI_BASE_URL, dep_code)
            )
            for r in results:
                if r['nom'].upper() == city.upper():
                    return sorted((i, i) for i in r['codesPostaux'])
        return []
    except Exception as e:
        logger.error("Error %s" % (e))
        return []
