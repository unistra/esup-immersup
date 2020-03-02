"""
API Views
"""
import datetime
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.http import JsonResponse
from django.template.defaultfilters import date as _date
from django.urls import resolve, reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext

from immersionlyceens.apps.core.models import (
    Building,
    Calendar,
    Course,
    HighSchool,
    Holiday,
    ImmersionUser,
    MailTemplateVars,
    PublicDocument,
    Slot,
    Training,
    Vacation,
)
from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request

logger = logging.getLogger(__name__)


@is_ajax_request
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

    courses = Course.objects.prefetch_related('training', 'component').filter(
        training__components=component_id
    )

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'component_code': course.component.code,
            'component_id': course.component.id,
            'teachers': [],
            'published_slots_count': 0,  # TODO
            'registered_students_count': 0,  # TODO
            'alerts_count': 0,  # TODO
            'can_delete': not course.slots.exists(),
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

    trainings = (
        Training.objects.prefetch_related('training_subdomains')
        .filter(components=component_id, active=True)
        .order_by('label')
    )

    for training in trainings:
        training_data = {
            'id': training.id,
            'label': training.label,
            'subdomain': [s.label for s in training.training_subdomains.filter(active=True)],
        }

        response['data'].append(training_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def get_ajax_documents(request):
    response = {'msg': '', 'data': []}

    documents = PublicDocument.objects.filter(active=True)

    response['data'] = [
        {
            'id': document.id,
            'label': document.label,
            'url': request.build_absolute_uri(reverse('public_document', args=(document.pk,))),
        }
        for document in documents
    ]

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def get_ajax_slots(request, component=None):
    from immersionlyceens.apps.core.models import Slot, Component

    # TODO: auth access test

    comp_id = request.GET.get('component_id')
    train_id = request.GET.get('training_id')

    response = {'msg': '', 'data': []}
    slots = []
    if train_id or train_id is not '' and train_id[0] is not '':
        slots = Slot.objects.filter(course__training__id=train_id)
    elif comp_id or comp_id is not '':
        slots = Slot.objects.filter(course__training__components__id=comp_id)

    all_data = []
    my_components = []
    if request.user.is_scuio_ip_manager():
        my_components = Component.objects.all()
    elif request.user.is_component_manager():
        my_components = request.user.components.all()

    for slot in slots:
        data = {
            'id': slot.id,
            'published': slot.published,
            'course_label': slot.course.label,
            'component': {
                'code': slot.course.component.code,
                'managed_by_me': slot.course.component in my_components,
            },
            'course_type': slot.course_type.label if slot.course_type is not None else '-',
            'date': slot.date.strftime('%a %d-%m-%Y') if slot.date is not None else '-',
            'time': '{s} - {e}'.format(
                s=slot.start_time.strftime('%Hh%M') or '', e=slot.end_time.strftime('%Hh%M') or '',
            )
            if slot.start_time is not None and slot.end_time is not None
            else '-',
            'building': '{} - {}'.format(slot.building.label, slot.campus.label)
            if slot.building is not None and slot.campus is not None
            else '-',
            'room': slot.room if slot.room is not None else '-',
            'teachers': ', '.join(
                ['{} {}'.format(e.first_name, e.last_name.upper()) for e in slot.teachers.all()]
            ),
            'n_register': 10,  # todo: registration count
            'n_places': slot.n_places if slot.n_places is not None and slot.n_places > 0 else '-',
            'additional_information': slot.additional_information,
        }
        all_data.append(data)

    response['data'] = all_data

    return JsonResponse(response, safe=False)


@is_ajax_request
# Should be public used by public page !!!
# @groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_courses_by_training(request, component_id=None, training_id=None):
    response = {'msg': '', 'data': []}

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")
    if not training_id:
        response['msg'] = gettext("Error : a valid training must be selected")

    courses = (
        Course.objects.prefetch_related('training')
        .filter(training__id=training_id, component__id=component_id,)
        .order_by('label')
    )

    for course in courses:
        course_data = {
            'key': course.id,
            'label': course.label,
            'url': course.url,
            'slots': Slot.objects.filter(course__training__id=training_id).count(),
        }
        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_buildings(request, campus_id=None):
    response = {'msg': '', 'data': []}

    if not campus_id or campus_id == '':
        response['msg'] = gettext("Error : a valid campus must be selected")

    buildings = Building.objects.filter(campus_id=campus_id, active=True).order_by('label')

    for building in buildings:
        buildings_data = {
            'id': building.id,
            'label': building.label,
        }
        response['data'].append(buildings_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_course_teachers(request, course_id=None):
    response = {'msg': '', 'data': []}

    if not course_id:
        response['msg'] = gettext("Error : a valid course must be selected")
    else:
        teachers = Course.objects.get(id=course_id).teachers.all().order_by('last_name')

        for teacher in teachers:
            teachers_data = {
                'id': teacher.id,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name.upper(),
            }
            response['data'].append(teachers_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_delete_course(request):
    response = {'msg': '', 'error': ''}
    course_id = request.POST.get('course_id')

    if not course_id:
        response['error'] = gettext("Error : a valid course must be selected")
        return JsonResponse(response, safe=False)

    # Check rights
    if not request.user.has_course_rights(course_id):
        response['error'] = gettext("Error : you can't delete this course")
        return JsonResponse(response, safe=False)

    try:
        course = Course.objects.get(pk=course_id)
        if not course.slots.exists():
            course.delete()
            response['msg'] = gettext("Course successfully deleted")
        else:
            response['error'] = gettext("Error : slots are linked to this course")
    except Course.DoesNotExist:
        pass

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
            'component': course.component.code,
            'training_label': course.training.label,
            'label': course.label,
            'teachers': {},
            'published_slots_count': f'{course.published_slots_count()} / {course.slots_count()}',
            'registered_students_count': 0,  # TODO
            'alerts_count': 0,  # TODO
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
            course_data['teachers'].update(
                [("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],
            )

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('ENS-CH')
def ajax_get_my_slots(request, user_id=None):
    response = {'msg': '', 'data': []}
    # TODO: filter on emargement which should be set !
    past_slots = resolve(request.path_info).url_name == 'GetMySlotsAll'

    if not user_id:
        response['msg'] = gettext("Error : a valid user must be passed")

    courses = Course.objects.prefetch_related('training').filter(teachers=user_id)

    for course in courses:
        slots = (
            course.slots.all()
            if past_slots
            else course.slots.filter(date__gte=datetime.datetime.now())
        )
        for s in slots:
            campus = ""
            try:
                if s.campus and s.building:
                    campus = f'{s.campus.label} - {s.building.label}'

                course_data = {
                    'id': course.id,
                    'published': course.published,
                    'component': course.component.code,
                    'training_label': f'{course.training.label} ({s.course_type.label})',
                    'campus': campus,
                    'room': s.room,
                    'date': _date(s.date, "l d/m/Y"),
                    'time': f'{s.start_time.strftime("%H:%M")} - {s.end_time.strftime("%H:%M")}',
                    'start_time': s.start_time.strftime("%H:%M"),
                    'end_time': s.end_time.strftime("%H:%M"),
                    'label': course.label,
                    'teachers': {},
                    'registered_students_count': {
                        "capacity": s.n_places,
                        "students_count": 4,
                    },  # TODO
                    'additional_information': s.additional_information,
                    'emargements': '',  # TODO
                }
            except AttributeError:
                # TODO: maybe not usefull
                pass

            for teacher in course.teachers.all().order_by('last_name', 'first_name'):
                course_data['teachers'].update(
                    [("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],
                )

            response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_agreed_highschools(request):
    response = {'msg': '', 'data': []}
    try:
        response['data'].append(list(HighSchool.agreed.all().order_by('city').values()))
    except:
        # Bouhhhh
        pass

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_check_date_between_vacation(request):
    response = {'data': [], 'msg': ''}

    _date = request.GET.get('date')

    if _date:
        # two format date
        try:
            formated_date = datetime.datetime.strptime(_date, '%Y/%m/%d')
        except ValueError:
            formated_date = datetime.datetime.strptime(_date, '%d/%m/%Y')

        response['data'] = {
            'is_between': (
                Vacation.date_is_inside_a_vacation(formated_date.date())
                or Holiday.date_is_a_holiday(formated_date.date())
            )
        }
    else:
        response['msg'] = gettext('Error: A date is required')

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required('SCUIO-IP', 'REF-LYC')
def ajax_get_student_records(request):
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

    # high_school_validation
    response = {'data': [], 'msg': ''}

    # @@@
    action = request.POST.get('action')
    hs_id = request.POST.get('high_school_id')
    actions = ['TO_VALIDATE', 'VALIDATED', 'REJECTED']

    if action and action.upper() in actions:

        if hs_id:
            action = action.upper()
            records = []
            if action == 'TO_VALIDATE':
                records = HighSchoolStudentRecord.objects.filter(
                    highschool_id=hs_id, validation=1,  # TO VALIDATE
                )
            elif action == 'VALIDATED':
                records = HighSchoolStudentRecord.objects.filter(
                    highschool_id=hs_id, validation=2,  # VALIDATED
                )
            elif action == 'REJECTED':
                records = HighSchoolStudentRecord.objects.filter(
                    highschool_id=hs_id, validation=3,  # REJECTED
                )

            response['data'] = [
                {
                    'id': record.id,
                    'first_name': record.student.first_name,
                    'last_name': record.student.last_name,
                    'birth_date': record.birth_date,
                    'level': record.level,
                    'class_name': record.class_name,
                }
                for record in records
            ]
        else:
            response['msg'] = gettext("Error: No high school selected")
    else:
        response['msg'] = gettext("Error: No action selected for AJAX request")
    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_slots_by_course(request, course_id=None):
    """ Public get"""
    from immersionlyceens.apps.core.models import Slot

    response = {'msg': '', 'data': []}
    slots = []

    if not course_id:
        response['msg'] = gettext("Error : a valid course is requested")
    else:
        calendar = Calendar.objects.first()
        # TODO: poc for now maybe refactor dirty code in a model method !!!!
        today = datetime.datetime.today().date()
        reg_start_date = reg_end_date = datetime.date(1, 1, 1)
        if calendar.calendar_mode == 'YEAR':
            reg_start_date = calendar.year_registration_start_date
            reg_end_date = calendar.year_end_date
        else:
            # Year mode
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                reg_start_date = calendar.semester1_start_date
                reg_end_date = calendar.semester1_end_date
            # semester mode
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                reg_start_date = calendar.semester2_start_date
                reg_end_date = calendar.semester2_end_date

        slots = Slot.objects.filter(
            course__id=course_id, published=True, date__gte=reg_start_date, date__lte=reg_end_date
        )

    all_data = []
    for slot in slots:
        data = {
            'id': slot.id,
            'published': slot.published,
            'course_label': slot.course.label,
            'course_type': slot.course_type.label if slot.course_type is not None else '-',
            'date': _date(slot.date, "l j F Y") if slot.date is not None else '-',
            'time': '{s} - {e}'.format(
                s=slot.start_time.strftime('%Hh%M') or '', e=slot.end_time.strftime('%Hh%M') or '',
            )
            if slot.start_time is not None and slot.end_time is not None
            else '-',
            'building': '{} - {}'.format(slot.building.label, slot.campus.label)
            if slot.building is not None and slot.campus is not None
            else '-',
            'room': slot.room if slot.room is not None else '-',
            'teachers': ', '.join(
                ['{} {}'.format(e.first_name, e.last_name.upper()) for e in slot.teachers.all()]
            ),
            'n_register': 10,  # todo: registration count
            'n_places': slot.n_places if slot.n_places is not None and slot.n_places > 0 else '-',
            'additional_information': slot.additional_information,
        }
        all_data.append(data)

    response['data'] = all_data

    return JsonResponse(response, safe=False)


# REJECT / VALIDATE STUDENT
@is_ajax_request
def ajax_validate_reject_student(request, validate):
    """
    Validate or reject student
    """
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

    response = {'data': None, 'msg': ''}

    student_record_id = request.POST.get('student_record_id')
    if student_record_id:
        hs = None
        if request.user.is_scuio_ip_manager():
            hs = HighSchool.objects.all()
        else:
            hs = HighSchool.objects.filter(id=request.user.highschool.id)

        if hs:
            try:
                record = HighSchoolStudentRecord.objects.get(
                    id=student_record_id, highschool__in=hs
                )
                # 2 => VALIDATED
                # 3 => REJECTED
                record.validation = 2 if validate else 3
                record.save()
                response['data'] = {'ok': True}

            except HighSchoolStudentRecord.DoesNotExist:
                response['msg'] = "Error: No student record"
        else:
            response['msg'] = "Error: No high school"
    else:
        response['msg'] = "Error: No student selected"

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-LYC', 'SCUIO-IP')
def ajax_validate_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=True)


@is_ajax_request
@is_post_request
@groups_required('REF-LYC', 'SCUIO-IP')
def ajax_reject_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=False)


@is_ajax_request
@is_post_request
@groups_required('REF-LYC', 'SCUIO-IP')
def ajax_check_course_publication(request, course_id):
    from immersionlyceens.apps.core.models import Course

    response = {'data': None, 'msg': ''}

    c = Course.objects.get(id=course_id)
    response['data'] = {'published': c.published}

    return JsonResponse(response, safe=False)
