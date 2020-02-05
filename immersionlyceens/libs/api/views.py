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

from immersionlyceens.apps.core.models import (
    MailTemplateVars, Course, Training,
    Building, ImmersionUser)

from immersionlyceens.decorators import groups_required

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
@groups_required('SCUIO-IP','REF-CMP')
def ajax_get_courses(request, component_id=None):
    response = {'msg': '', 'data': []}

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")

    courses = Course.objects.prefetch_related('training').filter(
        training__components=component_id)

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'teachers': [],
            'published_slots_count': 0, # TODO
            'registered_students_count': 0, # TODO
            'alerts_count': 0, # TODO
        }

        for teacher in course.teachers.all().order_by('last_name','first_name'):
            course_data['teachers'].append("%s %s" % (teacher.last_name, teacher.first_name))

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_trainings(request):
    response = {'msg': '', 'data': []}

    component_id = request.POST.get("component_id")

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")
        return JsonResponse(response, safe=False)

    trainings = Training.objects.prefetch_related('training_subdomains')\
        .filter(components=component_id, active=True)

    for training in trainings:
        training_data = {
            'id': training.id,
            'label': training.label,
            'subdomain': [s.label for s in training.training_subdomains.filter(active=True)],
        }

        response['data'].append(training_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP','REF-CMP')
def get_ajax_documents(request):
    from immersionlyceens.apps.core.models import PublicDocument

    response = {'msg': '', 'data': []}

    documents = PublicDocument.objects.filter(active=True)

    response['data'] = [{
        'id': document.id,
        'label': document.label,
        'url': request.build_absolute_uri(reverse('public_document', args=(document.pk,))),
    } for document in documents]

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP','REF-CMP')
def get_ajax_slots(request, component=None):
    from immersionlyceens.apps.core.models import Slot
    # TODO: auth access test

    response = {'msg': '', 'data': []}
    if component:
        slots = Slot.objects.filter(course__training__components__id=component)

        data = [{
            'id': slot.id,
            'published': slot.published,
            'course_label': slot.course.label,
            'course_type': slot.course_type.label,
            'date': slot.date.strftime('%a %d-%d-%Y'),
            'time': '{s} - {e}'.format(
                s=slot.start_time.strftime('%Hh%M'),
                e=slot.end_time.strftime('%Hh%M'),
            ),
            'building': slot.building.label,
            'room': slot.room,
            'teachers': ', '.join([str(e) for e in slot.teachers.all()]),
            'n_register': 10,
            'n_places': slot.n_places,
            'additional_information': slot.additional_information,
        } for slot in slots]

        response['data'] = data
    else:
        response['msg'] = gettext('Error : component id')

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP','REF-CMP')
def ajax_get_courses_by_training(request, training_id=None):
    response = {'msg': '', 'data': []}

    if not training_id:
        response['msg'] = gettext("Error : a valid training must be selected")

    courses = Course.objects.prefetch_related('training').filter(
        training__id=training_id)

    for course in courses:
        course_data = {
            'key': course.id,
            'label': course.label,
        }
        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required('SCUIO-IP','REF-CMP')
def ajax_get_buildings(request, campus_id=None):
    response = {'msg': '', 'data': []}

    if not campus_id:
        response['msg'] = gettext("Error : a valid campus must be selected")

    buildings = Building.objects.filter(campus_id=campus_id)

    for building in buildings:
        buildings_data = {
            'id': building.id,
            'label': building.label,
        }
        response['data'].append(buildings_data.copy())

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required('SCUIO-IP','REF-CMP')
def ajax_get_course_teachers(request, course_id=None):
    response = {'msg': '', 'data': []}

    if not course_id:
        response['msg'] = gettext("Error : a valid course must be selected")
    else:
        teachers = Course.objects.get(id=course_id).teachers.all()

        for teacher in teachers:
            teachers_data = {
                'id': teacher.id,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name.upper(),
            }
            response['data'].append(teachers_data.copy())

    return JsonResponse(response, safe=False)
