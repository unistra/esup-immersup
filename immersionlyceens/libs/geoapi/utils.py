import logging
import sys

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_json_from_url(url):
    connect_timeout = 1.0
    read_timeout = 10.0

    try:
        r = requests.get(url, timeout=(connect_timeout, read_timeout))
        return r.json()
    except Exception:
        logger.error("Cannot connect to url : %s", sys.exc_info()[0])
        raise


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
                '%s/departements/%s/communes/?fields=nom' % (settings.GEOAPI_BASE_URL, dep_code)
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
                    return sorted([(i, i) for i in r['codesPostaux']])
        return []
    except Exception as e:
        logger.error("Error %s" % (e))
        return []
