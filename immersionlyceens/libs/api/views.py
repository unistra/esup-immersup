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

from immersionlyceens.apps.core.models import Course, MailTemplateVars, Training
from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request

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
                users = sorted(users, key=lambda u: [u['lastname'], u['firstname']])
                response['data'] = persons_list + users
            else:
                response['msg'] = gettext("Error : can't query LDAP server")

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_available_vars(request, template_id=None):
    response = {'msg': '', 'data': []}

    if template_id:
        template_vars = MailTemplateVars.objects.filter(mail_templates=template_id)
        response["data"] = [
            {'id': v.id, 'code': v.code, 'description': v.description} for v in template_vars
        ]
    else:
        response["msg"] = gettext("Error : no template id")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_courses(request, component_id=None):
    response = {'msg': '', 'data': []}

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")

    courses = Course.objects.prefetch_related('training').filter(training__components=component_id)

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'teachers': [],
            'published_slots_count': 0,  # TODO
            'registered_students_count': 0,  # TODO
            'alerts_count': 0,  # TODO
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
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
def get_ajax_documents(request):
    from immersionlyceens.apps.core.models import PublicDocument

    response = {'msg': '', 'data': []}

    documents = PublicDocument.objects.filter(active=True)

    response['data'] = [
        {
            'id': document.id,
            'label': document.label,
            'url': request.build_absolute_uri(
                reverse('accompanying_document', args=(document.pk,))
            ),
        }
        for document in documents
    ]

    return JsonResponse(response, safe=False)


@is_ajax_request
def get_ajax_slots(request, component=None):
    # TODO: auth access test

    response = {'msg': '', 'data': []}
    if component:
        # TODO: use real data !!
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
                'additional_information': 'lorem ipsum sit amet dolor',
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
                'additional_information': 'lorem ipsum sit amet dolor',
            },
        ]
    else:
        response['msg'] = gettext('Error : component id')

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_courses(request, component_id=None):
    response = {'msg': '', 'data': []}

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")

    courses = Course.objects.prefetch_related('training').filter(training__components=component_id)

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'teachers': [],
            'published_slots_count': 0,  # TODO
            'registered_students_count': 0,  # TODO
            'alerts_count': 0,  # TODO
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
            course_data['teachers'].append("%s %s" % (teacher.last_name, teacher.first_name))

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('ENS-CH')
def ajax_get_my_courses(request, user_id=None):
    response = {'msg': '', 'data': []}

    if not user_id:
        response['msg'] = gettext("Error : a valid user must be passed")

    courses = Course.objects.prefetch_related('training').filter(teachers=user_id)

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'components': [],
            'training_label': course.training.label,
            'label': course.label,
            'teachers': {},
            'published_slots_count': 0,  # TODO
            'registered_students_count': 0,  # TODO
            'alerts_count': 0,  # TODO
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
            course_data['teachers'].update(
                [("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],
            )

        for component in course.training.components.all().order_by('label'):
            course_data['components'].append(component.label)

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('ENS-CH')
def ajax_get_my_slots(request, user_id=None):
    response = {'msg': '', 'data': []}

    if not user_id:
        response['msg'] = gettext("Error : a valid user must be passed")

    courses = Course.objects.prefetch_related('training').filter(teachers=user_id)

    for course in courses:
        for s in course.training.slots.all():
            course_data = {
                'id': course.id,
                'published': course.published,
                'components': [],
                'training_label': course.training.label,
                'course_type': s.course_type.label,
                'campus': s.campus.label,
                'building': s.building.label,
                'room': s.room,
                'date': s.date,
                'start_time': s.start_time,
                'end_time': s.end_time,

                'label': course.label,
                'teachers': {},
                'published_slots_count': 0,  # TODO
                'registered_students_count': 0,  # TODO
                'additional_information': s.additional_information, # TODO
                'emargements': '', # TODO
            }

            for teacher in course.teachers.all().order_by('last_name', 'first_name'):
                course_data['teachers'].update(
                    [("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],
                )

            for component in course.training.components.all().order_by('label'):
                course_data['components'].append(component.label)

            response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)
