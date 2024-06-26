"""
UAI API Views
"""

import logging

from django.conf import settings
from django.http import JsonResponse

from ..api_utils import get_json_from_url

logger = logging.getLogger(__name__)


def ajax_get_establishments(request, value=None):
    url = settings.UAI_API_URL
    header = settings.UAI_API_AUTH_HEADER
    search_attr = settings.UAI_API_SEARCH_ATTR
    # value = kwargs.get('value')

    results = []

    if not all([url, header, search_attr, value]):
        return JsonResponse(results)

    print(f"settings header : {settings.UAI_API_AUTH_HEADER}")

    # convert headers to dict
    try:
        headers = {header.split(':')[0].strip():header.split(':')[1].strip()}
    except:
        headers = {}

    try:
        results = get_json_from_url(f"{url}/?{search_attr}={value}", headers=headers)

        #FIXME Add a mapping for search results fields in settings ?
        results = {
            r['code']: {
                'label': r['label'],
                'academy':r['academy'],
                'city': r['city']
            } for r in results
        }

    except Exception as e:
        logger.error("Error %s" % (e))

    return JsonResponse(results, safe=False)
