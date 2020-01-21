"""
GEOAPI Views

TODO: use a decorator ie login_required
when all auth methods are implemented !
"""

import logging

from django.http import JsonResponse

from .utils import get_cities, get_departments, get_zipcodes

logger = logging.getLogger(__name__)


def ajax_get_departments(request):
    return JsonResponse(get_departments(), safe=False)


def ajax_get_cities(request, dep=None):
    return JsonResponse(get_cities(dep), safe=False)


def ajax_get_zipcodes(request, dep=None, city=None):
    return JsonResponse(get_zipcodes(dep, city), safe=False)
