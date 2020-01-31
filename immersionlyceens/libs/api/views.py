"""
API Views
"""
import datetime
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext

from immersionlyceens.decorators import (
    groups_required, is_ajax_request, is_post_request)

from immersionlyceens.apps.core.models import MailTemplateVars

logger = logging.getLogger(__name__)


def ajax_get_person(request):
    if settings.ACCOUNTS_CLIENT:
        response = {'msg': '', 'data': []}

        accounts_api = import_string(settings.ACCOUNTS_CLIENT)

        try:
            accounts_client = accounts_api()
        except:
            response['msg'] = gettext("Error : can't query LDAP server")
            return JsonResponse(response, safe=False)

        search_str = request.POST.get("username", None)

        if search_str:
            query_order = request.POST.get("query_order")
            persons_list = [query_order]

            users = accounts_client.search_user(search_str)
            if users != False:
                users = sorted(users, key = lambda u:[u['lastname'], u['firstname']])
                response['data'] = persons_list + users
            else:
                response['msg'] = gettext("Error : can't query LDAP server")

    return JsonResponse(response, safe=False)

@is_ajax_request
def ajax_get_available_vars(request, template_id=None):
    response = {'msg': '', 'data': []}

    # template_id = request.GET.get("template_id", None)

    if template_id:
        template_vars = MailTemplateVars.objects.filter(mail_templates=template_id)
        response["data"] = [ {
            'id':v.id,
            'code':v.code,
            'description':v.description } for v in template_vars ]
    else:
        response["msg"] = gettext("Error : no template id")

    return JsonResponse(response, safe=False)

@is_ajax_request
def get_ajax_documents(request):
    from immersionlyceens.apps.core.models import AccompanyingDocument

    response = {'msg': '', 'data': []}

    documents = AccompanyingDocument.objects.filter(active=True)
    response['data'] = [{
        'id': document.id,
        'label': document.label,
        'url': request.build_absolute_uri(reverse('accompanying_document', args=(document.pk,))),
    } for document in documents]

    return JsonResponse(response, safe=False)


@is_ajax_request
def get_ajax_slots(request, component=None):
    # TODO: auth access test


    response = {'msg': '', 'data': []}
    if component:
        response['data'] = [
            {
                'id': 1,
                'published': True,
                'course_label': 'Super cours',
                'course_type': 'TP',
                'date': 'Mardi 21-01-2020',
                'time': '8:00 - 10:00',
                'building': 'Esplanade - Math-Info',
                'room': '420',
                'teachers': ', '.join(['Alexandre COMBEAU', 'Matthieu FUCHS']),
                'n_register': 24,
                'n_places': 35,
                'additional_information': 'lorem ipsum sit amet dolor'
            },
            {
                'id': 2,
                'published': False,
                'course_label': 'Hyper cours',
                'course_type': 'TP',
                'date': 'jeudi 23-01-2020',
                'time': '8:00 - 10:00',
                'building': 'Esplanade - Math-Info',
                'room': '105',
                'teachers': ', '.join(['Alexandre COMBEAU']),
                'n_register': 15,
                'n_places': 20,
                'additional_information': 'lorem ipsum sit amet dolor'
            }
        ]
    else:
        response['msg'] = gettext('Error : component id')

    return JsonResponse(response, safe=False)





