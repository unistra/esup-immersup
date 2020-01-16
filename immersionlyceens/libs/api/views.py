"""
API Views
"""

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.module_loading import import_string

from immersionlyceens.decorators import (
    groups_required, is_ajax_request, is_post_request)

logger = logging.getLogger(__name__)


def ajax_get_person(request):
    if settings.ACCOUNTS_CLIENT:
        accounts_api = import_string(settings.ACCOUNTS_CLIENT)
        accounts_client = accounts_api()

        search_str = request.POST.get("username", None)

        if search_str:
            query_order = request.POST.get("query_order")
            persons_list = [query_order]

            users = accounts_client.search_user(search_str)
            users = sorted(users, key = lambda u:[u['lastname'], u['firstname']])

            return JsonResponse(persons_list + users, safe=False)
            
    return JsonResponse([], safe=False)
