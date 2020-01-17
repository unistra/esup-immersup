import logging

import requests

logger = logging.getLogger(__name__)


def get_json_from_url(url):
    r = requests.get(url)
    return r.json()


def get_departments():
    try:
        results = get_json_from_url(
            'https://geo.api.gouv.fr/departements?fields=nom,code')
        return [(r['code'], r['nom']) for r in results]

    except Exception as e:
        logger.error("Error %s" % (e))
        return ('')


def get_cities(dep_code=None):
    try:
        if dep_code:
            results = get_json_from_url(
                'https://geo.api.gouv.fr/departements/%s/communes/?fields=nom' % dep_code)
            return [(r['nom'].upper(), r['nom'].upper()) for r in results]
        return ('')

    except Exception as e:
        logger.error("Error %s" % (e))
        return ('')


def get_zipcodes(dep_code=None, city=None):
    zipcodes = []
    try:
        if city:
            results = get_json_from_url(
                'https://geo.api.gouv.fr/departements/%s/communes/?fields=nom,codesPostaux' % dep_code
            )
            for r in results:
                if r['nom'].upper() == city:
                    return sorted([(i, i) for i in r['codesPostaux']])

    except Exception as e:
        logger.error("Error %s" % (e))
        return ('')
