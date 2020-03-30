"""
API Views
"""
import csv
import datetime
import json
import logging
from functools import reduce

from immersionlyceens.apps.core.models import (
    Building, Calendar, CancelType, Component, Course, GeneralSettings, HighSchool, Holiday, Immersion, ImmersionUser,
    MailTemplate, MailTemplateVars, PublicDocument, Slot, Training, UniversityYear, Vacation,
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.mails.variables_parser import multisub

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.defaultfilters import date as _date
from django.urls import resolve, reverse
from django.utils.formats import date_format
from django.utils.module_loading import import_string
from django.utils.translation import gettext, ugettext_lazy as _

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
        response["data"] = [{'id': v.id, 'code': v.code, 'description': v.description} for v in template_vars]
    else:
        response["msg"] = gettext("Error : no template id")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_courses(request, component_id=None):
    response = {'msg': '', 'data': []}

    if not component_id:
        response['msg'] = gettext("Error : a valid component must be selected")

    courses = Course.objects.prefetch_related('training', 'component').filter(training__components=component_id)

    for course in courses:
        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'component_code': course.component.code,
            'component_id': course.component.id,
            'teachers': [],
            'slots_count': course.slots_count(),
            'n_places': course.free_seats(),
            'published_slots_count': course.published_slots_count(),
            'registered_students_count': course.registrations_count(),
            'alerts_count': 0,  # TODO
            'can_delete': not course.slots.exists(),
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
            course_data['teachers'].append("%s %s" % (teacher.last_name, teacher.first_name))

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_post_request
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
def ajax_get_documents(request):
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
def ajax_get_slots(request, component=None):
    # TODO: auth access test
    can_update_attendances = False

    today = datetime.datetime.today().date()
    try:
        year = UniversityYear.objects.get(active=True)
        can_update_attendances = today <= year.end_date
    except UniversityYear.DoesNotExist:
        pass

    comp_id = request.GET.get('component_id')
    train_id = request.GET.get('training_id')

    response = {'msg': '', 'data': []}
    slots = []
    if train_id:  # and train_id[0] is not '':
        slots = Slot.objects.prefetch_related('course__training', 'teachers', 'immersions').filter(
            course__training__id=train_id
        )
    elif comp_id:
        slots = Slot.objects.prefetch_related('course__training__components', 'teachers', 'immersions').filter(
            course__training__components__id=comp_id
        )

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
            'component': {'code': slot.course.component.code, 'managed_by_me': slot.course.component in my_components,},
            'course_type': slot.course_type.label if slot.course_type is not None else '-',
            'course_type_full': slot.course_type.full_label if slot.course_type is not None else '-',
            'datetime': datetime.datetime.strptime(
                "%s:%s:%s %s:%s"
                % (slot.date.year, slot.date.month, slot.date.day, slot.start_time.hour, slot.start_time.minute,),
                "%Y:%m:%d %H:%M",
            )
            if slot.date
            else None,
            'date': _date(slot.date, 'l d/m/Y'),
            'time': {
                'start': slot.start_time.strftime('%Hh%M') if slot.start_time else '',
                'end': slot.end_time.strftime('%Hh%M') if slot.end_time else '',
            },
            'location': {
                'campus': slot.campus.label if slot.campus else '',
                'building': slot.building.label if slot.building else '',
            },
            'room': slot.room or '-',
            'teachers': {},
            'n_register': slot.registered_students(),
            'n_places': slot.n_places if slot.n_places is not None else 0,
            'additional_information': slot.additional_information,
            'attendances_value': 0,
            'is_past': False,
        }

        if data['datetime'] and data['datetime'] <= datetime.datetime.today():
            data['is_past'] = True
            if not slot.immersions.all().exists():
                data['attendances_value'] = -1  # nothing
            elif slot.immersions.filter(attendance_status=0, cancellation_type__isnull=True).exists()\
                or can_update_attendances:
                data['attendances_value'] = 1  # to enter
            else:
                data['attendances_value'] = 2  # view only

        for teacher in slot.teachers.all().order_by('last_name', 'first_name'):
            data['teachers'].update([(f"{teacher.last_name} {teacher.first_name}", teacher.email,)],)
        all_data.append(data.copy())

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
            'slots_count': course.slots_count(teacher_id=user_id),
            'n_places': course.free_seats(teacher_id=user_id),
            'published_slots_count': course.published_slots_count(teacher_id=user_id),
            # f'{course.published_slots_count(teacher_id=user_id)} / {course.slots_count(teacher_id=user_id)}',
            'registered_students_count': course.registrations_count(teacher_id=user_id),
            # f'{course.registrations_count(teacher_id=user_id)} / {course.free_seats(teacher_id=user_id)}',
            'alerts_count': 0,  # TODO
        }

        for teacher in course.teachers.all().order_by('last_name', 'first_name'):
            course_data['teachers'].update([("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],)

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('ENS-CH')
def ajax_get_my_slots(request, user_id=None):
    response = {'msg': '', 'data': []}
    can_update_attendances = False

    today = datetime.datetime.today()
    try:
        year = UniversityYear.objects.get(active=True)
        can_update_attendances = today.date() <= year.end_date
    except UniversityYear.DoesNotExist:
        pass

    # TODO: filter on emargement which should be set !
    past_slots = resolve(request.path_info).url_name == 'GetMySlotsAll'

    if not user_id:
        response['msg'] = gettext("Error : a valid user must be passed")

    if past_slots:
        slots = (
            Slot.objects.prefetch_related('course__training', 'course__component', 'teachers', 'immersions')
            .filter(teachers=user_id)
            .exclude(date__lt=today.date(), immersions__isnull=True)
        ).distinct()
    else:
        slots = (
            Slot.objects.prefetch_related('course__training', 'course__component', 'teachers', 'immersions')
            .filter(Q(date__gte=today.date()) | \
                    Q(date=today.date(), end_time__gte=today.time()) | \
                    Q(immersions__attendance_status=0, immersions__cancellation_type__isnull=True), teachers=user_id)
            .distinct()
        )

    for slot in slots:
        campus = ""
        try:
            if slot.campus and slot.building:
                campus = f'{slot.campus.label} - {slot.building.label}'

            slot_data = {
                'id': slot.id,
                'published': slot.published,
                'component': slot.course.component.code,
                'training_label': f'{slot.course.training.label} ({slot.course_type.label})',
                'training_label_full': f'{slot.course.training.label} ({slot.course_type.full_label})',
                'location': {'campus': campus, 'room': slot.room,},
                'schedules': {
                    'date': _date(slot.date, "l d/m/Y"),
                    'time': f'{slot.start_time.strftime("%H:%M")} - {slot.end_time.strftime("%H:%M")}',
                },
                'datetime': datetime.datetime.strptime(
                    "%s:%s:%s %s:%s"
                    % (slot.date.year, slot.date.month, slot.date.day, slot.start_time.hour, slot.start_time.minute,),
                    "%Y:%m:%d %H:%M",
                )
                if slot.date
                else None,
                'start_time': slot.start_time.strftime("%H:%M"),
                'end_time': slot.end_time.strftime("%H:%M"),
                'label': slot.course.label,
                'teachers': {},
                'n_places': slot.n_places if slot.n_places is not None else 0,
                'registered_students_count': {"capacity": slot.n_places, "students_count": slot.registered_students(),},
                'additional_information': slot.additional_information,
                'attendances_status': '',
                'attendances_value': 0,
            }
        except AttributeError:
            # TODO: maybe not usefull
            pass

        if slot_data['datetime'] and slot_data['datetime'] <= today:
            if not slot.immersions.filter(cancellation_type__isnull=True).exists():
                slot_data['attendances_status'] = ""
                slot_data['attendances_value'] = -1
            elif slot.immersions.filter(attendance_status=0, cancellation_type__isnull=True).exists()\
                and can_update_attendances:
                slot_data['attendances_status'] = gettext("To enter")
                slot_data['attendances_value'] = 1
            else:
                slot_data['attendances_status'] = gettext("Entered")
                if can_update_attendances:
                    slot_data['attendances_value'] = 1
                else:
                    slot_data['attendances_value'] = 2
        else:
            slot_data['attendances_status'] = gettext("Future slot")

        for teacher in slot.teachers.all().order_by('last_name', 'first_name'):
            slot_data['teachers'].update([("%s %s" % (teacher.last_name, teacher.first_name), teacher.email,)],)

        response['data'].append(slot_data.copy())

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
                or formated_date.date().weekday() == 6  # sunday
            ),
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
                records = HighSchoolStudentRecord.objects.filter(highschool_id=hs_id, validation=1,)  # TO VALIDATE
            elif action == 'VALIDATED':
                records = HighSchoolStudentRecord.objects.filter(highschool_id=hs_id, validation=2,)  # VALIDATED
            elif action == 'REJECTED':
                records = HighSchoolStudentRecord.objects.filter(highschool_id=hs_id, validation=3,)  # REJECTED

            response['data'] = [
                {
                    'id': record.id,
                    'first_name': record.student.first_name,
                    'last_name': record.student.last_name,
                    'birth_date': _date(record.birth_date, "j/m/Y"),
                    'level': HighSchoolStudentRecord.LEVELS[record.level - 1][1],
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
            'course_type_full': slot.course_type.full_label if slot.course_type is not None else '-',
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
            'teachers': ', '.join(['{} {}'.format(e.first_name, e.last_name.upper()) for e in slot.teachers.all()]),
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
                record = HighSchoolStudentRecord.objects.get(id=student_record_id, highschool__in=hs)
                # 2 => VALIDATED
                # 3 => REJECTED
                record.validation = 2 if validate else 3
                record.save()
                if validate:
                    record.student.send_message(request, 'CPT_MIN_VALIDE_LYCEEN')
                else:
                    record.student.send_message(request, 'CPT_MIN_REJET_LYCEEN')
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


@is_ajax_request
@is_post_request
@groups_required('SCUIO-IP')
def ajax_delete_account(request):
    """
    Completely destroy a student account and all data
    """
    student_id = request.POST.get('student_id')
    send_mail = request.POST.get('send_email', False) == "true"

    if student_id:
        try:
            student = ImmersionUser.objects.get(id=student_id, groups__name__in=['LYC', 'ETU'])

            if send_mail:
                student.send_message(request, 'CPT_DELETE')

            response = {'error': False, 'msg': gettext("Account deleted")}
            student.delete()
        except ImmersionUser.DoesNotExist:
            response = {'error': True, 'msg': gettext("User not found")}
    else:
        response = {'error': True, 'msg': gettext("User not found")}

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('SCUIO-IP', 'LYC', 'ETU')
def ajax_cancel_registration(request):
    """
    Cancel a registration to an immersion slot
    """
    immersion_id = request.POST.get('immersion_id')
    reason_id = request.POST.get('reason_id')

    if not immersion_id or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            immersion = Immersion.objects.get(pk=immersion_id)
            cancellation_reason = CancelType.objects.get(pk=reason_id)
            immersion.cancellation_type = cancellation_reason
            immersion.save()
            immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

            response = {'error': False, 'msg': gettext("Immersion cancelled")}
        except ImmersionUser.DoesNotExist:
            response = {'error': True, 'msg': gettext("User not found")}
        except CancelType.DoesNotExist:
            response = {'error': True, 'msg': gettext("Invalid cancellation reason #id")}

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'LYC', 'ETU', 'REF-LYC')
def ajax_get_immersions(request, user_id=None, immersion_type=None):
    """
    Get (high-school or not) students immersions
    immersion_type in "future", "past", "cancelled" or None
    """
    calendar = None
    slot_semester = None
    remainings = {}
    response = {'msg': '', 'data': []}

    if not user_id:
        response['msg'] = gettext("Error : missing user id")
        return JsonResponse(response, safe=False)

    if (
        not request.user.is_scuio_ip_manager()
        and not request.user.is_high_school_manager()
        and request.user.id != user_id
    ):
        response['msg'] = gettext("Error : invalid user id")
        return JsonResponse(response, safe=False)

    try:
        calendar = Calendar.objects.first()
    except Exception:
        pass

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()

    try:
        student = ImmersionUser.objects.get(pk=user_id)
        remainings['1'], remainings['2'], remaining_annually = student.remaining_registrations_count()
    except ImmersionUser.DoesNotExist:
        response['msg'] = gettext("Error : no such user")
        return JsonResponse(response, safe=False)

    time = "%s:%s" % (datetime.datetime.now().hour, datetime.datetime.now().minute)

    immersions = Immersion.objects.prefetch_related(
        'slot__course__training', 'slot__course_type', 'slot__campus', 'slot__building', 'slot__teachers',
    ).filter(student_id=user_id)

    if immersion_type == "future":
        immersions = immersions.filter(
            Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gte=time), cancellation_type__isnull=True
        )
    elif immersion_type == "past":
        immersions = immersions.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lte=time), cancellation_type__isnull=True
        )
    elif immersion_type == "cancelled":
        immersions = immersions.filter(cancellation_type__isnull=False)

    for immersion in immersions:
        if calendar.calendar_mode == 'SEMESTER':
            slot_semester = calendar.which_semester(immersion.slot.date)

        slot_datetime = datetime.datetime.strptime(
            "%s:%s:%s %s:%s"
            % (
                immersion.slot.date.year,
                immersion.slot.date.month,
                immersion.slot.date.day,
                immersion.slot.start_time.hour,
                immersion.slot.start_time.minute,
            ),
            "%Y:%m:%d %H:%M",
        )

        immersion_data = {
            'id': immersion.id,
            'training': immersion.slot.course.training.label,
            'course': immersion.slot.course.label,
            'type': immersion.slot.course_type.label,
            'type_full': immersion.slot.course_type.full_label,
            'campus': immersion.slot.campus.label,
            'building': immersion.slot.building.label,
            'room': immersion.slot.room,
            'datetime': slot_datetime,
            'date': date_format(immersion.slot.date),
            'start_time': immersion.slot.start_time.strftime("%-Hh%M"),
            'end_time': immersion.slot.end_time.strftime("%-Hh%M"),
            'teachers': [],
            'info': immersion.slot.additional_information,
            'attendance': immersion.get_attendance_status_display(),
            'attendance_status': immersion.attendance_status,
            'cancellable': datetime.datetime.today().date() < immersion.slot.date,
            'cancellation_type': '',
            'slot_id': immersion.slot.id,
            'free_seats': 0,
            'can_register': False,
        }
        if immersion.slot.date < today:
            immersion_data['time_type'] = "past"
        elif immersion.slot.date > today or (
            immersion.slot.date == today and immersion.slot.begin_time > datetime.datetime.today().time()
        ):
            immersion_data['time_type'] = "future"

        if immersion.slot.n_places:
            immersion_data['free_seats'] = immersion.slot.n_places - immersion.slot.registered_students()

        if immersion.cancellation_type:
            immersion_data['cancellation_type'] = immersion.cancellation_type.label

            if slot_datetime > datetime.datetime.today() and immersion.slot.available_seats() > 0:
                if slot_semester and remainings[str(slot_semester)] or not slot_semester and remaining_annually:
                    immersion_data['can_register'] = True

        for teacher in immersion.slot.teachers.all().order_by('last_name', 'first_name'):
            immersion_data['teachers'].append("%s %s" % (teacher.last_name, teacher.first_name))

        response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('LYC', 'ETU')
def ajax_get_other_registrants(request, immersion_id):
    immersion = None
    response = {'msg': '', 'data': []}

    try:
        immersion = Immersion.objects.get(pk=immersion_id, student=request.user)
    except Immersion.DoesNotExists:
        response['msg'] = gettext("Error : invalid user or immersion id")

    if immersion:
        students = (
            ImmersionUser.objects.prefetch_related('high_school_student_record', 'immersions')
            .filter(
                immersions__slot=immersion.slot,
                high_school_student_record__isnull=False,
                high_school_student_record__visible_immersion_registrations=True,
            )
            .exclude(id=request.user.id)
        )

        for student in students:
            student_data = {'name': "%s %s" % (student.last_name, student.first_name), 'email': ""}

            if student.high_school_student_record.visible_email:
                student_data["email"] = student.email

            response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP', 'ENS-CH')
def ajax_get_slot_registrations(request, slot_id):
    slot = None
    response = {'msg': '', 'data': []}

    try:
        slot = Slot.objects.get(pk=slot_id)
    except Slot.DoesNotExists:
        response['msg'] = gettext("Error : invalid slot id")

    if slot:
        immersions = Immersion.objects.prefetch_related('student').filter(slot=slot, cancellation_type__isnull=True)

        for immersion in immersions:
            immersion_data = {
                'id': immersion.id,
                'lastname': immersion.student.last_name,
                'firstname': immersion.student.first_name,
                'profile': '',
                'school': '',
                'level': '',
                'city': '',
                'attendance': immersion.get_attendance_status_display(),
                'attendance_status': immersion.attendance_status,
            }

            if immersion.student.is_high_school_student():
                immersion_data['profile'] = gettext('High-school student')

                record = immersion.student.get_high_school_student_record()

                if record:
                    immersion_data['school'] = record.highschool.label
                    immersion_data['city'] = record.highschool.city
                    immersion_data['level'] = record.get_level_display()

            elif immersion.student.is_student():
                immersion_data['profile'] = gettext('Student')

                record = immersion.student.get_student_record()

                if record:
                    immersion_data['school'] = record.home_institution
                    immersion_data['level'] = record.get_level_display()

            response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('SCUIO-IP', 'REF-CMP', 'ENS-CH')
def ajax_set_attendance(request):
    """
    Update immersion attendance status
    """
    immersion_id = request.POST.get('immersion_id', None)
    immersion_ids = request.POST.get('immersion_ids', None)

    if immersion_ids:
        immersion_ids = json.loads(immersion_ids)

    attendance_value = request.POST.get('attendance_value')

    response = {'success': '', 'error': '', 'data': []}

    if immersion_id and not immersion_ids:
        immersion_ids = [immersion_id]

    for immersion_id in immersion_ids:
        immersion = None
        try:
            immersion = Immersion.objects.get(pk=immersion_id)
        except Immersion.DoesNotExist:
            response['error'] = gettext("Error : query contains some invalid immersion ids")

        if immersion:
            immersion.attendance_status = attendance_value
            immersion.save()
            response['msg'] = gettext("Attendance status updated")

    return JsonResponse(response, safe=False)


@is_ajax_request
@login_required
@is_post_request
@groups_required('SCUIO-IP', 'LYC', 'ETU', 'REF-CMP')
def ajax_slot_registration(request):
    """
    Add a registration to an immersion slot
    """
    slot_id = request.POST.get('slot_id', None)
    student_id = request.POST.get('student_id', None)
    # feedback is used to use or not django message
    # set feedback=false in ajax query when feedback
    # is used in modal or specific form !
    # warning js boolean not python one
    feedback = request.POST.get('feedback', True)
    # Should we force registering ?
    # warning js boolean not python one
    force = request.POST.get('force', False)
    cmp = request.POST.get('cmp', False)
    calendar, slot, student = None, None, None
    can_force_reg = request.user.is_scuio_ip_manager()
    today = datetime.datetime.today().date()

    request.session.pop("last_registration_slot", None)

    try:
        calendar = Calendar.objects.first()
    except Exception:
        response = {'error': True, 'msg': _("Invalid calendar : cannot register")}
        return JsonResponse(response, safe=False)

    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            pass
    else:
        student = request.user

    if slot_id:
        try:
            slot = Slot.objects.get(pk=slot_id)
        except ImmersionUser.DoesNotExist:
            pass

    if not slot or not student:
        response = {'error': True, 'msg': _("Invalid parameters")}
        return JsonResponse(response, safe=False)

    # Check free seat in slot
    if slot.available_seats() == 0:
        response = {'error': True, 'msg': _("No seat available for selected slot")}
        return JsonResponse(response, safe=False)

    # Check current student immersions and valid dates
    if student.immersions.filter(slot=slot, cancellation_type__isnull=True).exists():
        if not cmp:
            msg = _("Already registered to this slot")
        else:
            msg = _("Student already registered for selected slot")

        response = {'error': True, 'msg': msg}
    else:
        remaining_regs_count = student.remaining_registrations_count()
        can_register = False

        # TODO : this has to be factorized somewhere ...
        if calendar and calendar.calendar_mode == 'YEAR':
            if calendar.year_registration_start_date <= today <= calendar.year_end_date:
                # remaining regs ok
                if remaining_regs_count['annually'] > 0:
                    can_register = True
                # alert user he can force registering
                elif can_force_reg and not force == 'true':
                    return JsonResponse({'error': True, 'msg': 'force_update'}, safe=False)
                # force registering
                elif force == 'true':
                    can_register = True
                # student request & no more remaining registration count
                elif (request.user.is_high_school_student() or request.user.is_student()) and remaining_regs_count[
                    'annually'
                ] <= 0:
                    response = {
                        'error': True,
                        'msg': _(
                            "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                        ),
                    }
                    return JsonResponse(response, safe=False)

        # semester mode
        elif calendar:
            # Semester 1
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                if calendar.semester1_registration_start_date <= today <= calendar.semester1_end_date:
                    # remaining regs ok
                    if remaining_regs_count['semester1'] > 0:
                        can_register = True
                    # alert user he can force registering (js boolean)
                    elif can_force_reg and not force == 'true':
                        return JsonResponse({'error': True, 'msg': 'force_update'}, safe=False)
                    # force registering (js boolean)
                    elif force == 'true':
                        can_register = True
                    # student request & no more remaining registration count
                    elif (request.user.is_high_school_student() or request.user.is_student()) and remaining_regs_count[
                        'semester1'
                    ] <= 0:
                        response = {
                            'error': True,
                            'msg': _(
                                "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                            ),
                        }
                        return JsonResponse(response, safe=False)

            # Semester 2
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                if calendar.semester2_registration_start_date <= today <= calendar.semester2_end_date:
                    # remaining regs ok
                    if remaining_regs_count['semester2'] > 0:
                        can_register = True
                    # alert user he can force registering (js boolean)
                    elif can_force_reg and not force == 'true':
                        return JsonResponse({'error': True, 'msg': 'force_update'}, safe=False)
                    # force registering (js boolean)
                    elif force == 'true':
                        can_register = True
                    # student request & no more remaining registration count
                    elif (request.user.is_high_school_student() or request.user.is_student()) and remaining_regs_count[
                        'semester2'
                    ] <= 0:
                        response = {
                            'error': True,
                            'msg': _(
                                "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                            ),
                        }
                        return JsonResponse(response, safe=False)

        if can_register:
            # Cancellation exists re-register
            if student.immersions.filter(slot=slot, cancellation_type__isnull=False).exists():
                student.immersions.filter(slot=slot, cancellation_type__isnull=False).update(
                    cancellation_type=None, attendance_status=0
                )
            # No data exists register
            else:
                Immersion.objects.create(
                    student=student, slot=slot, cancellation_type=None, attendance_status=0,
                )

            student.send_message(request, 'IMMERSION_CONFIRM', slot=slot)
            msg = _("Registration successfully added")
            response = {'error': False, 'msg': msg}
            # TODO: use django messages for errors as well ?
            # this is a js boolean !!!!
            if feedback == True:
                messages.success(request, msg)
            request.session["last_registration_slot_id"] = slot.id
        else:
            response = {'error': True, 'msg': _("Registration is not currently allowed")}

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_get_students(request):

    response = {'data': [], 'msg': ''}

    students = []

    students = ImmersionUser.objects.filter(groups__name__in=['LYC', 'ETU'])

    for student in students:
        student_data = {
            'id': student.pk,
            'lastname': student.last_name,
            'firstname': student.first_name,
            'profile': '',
            'school': '',
            'level': '',
            'city': '',
        }

        if student.is_high_school_student():
            student_data['profile'] = _('High-school student')

            record = student.get_high_school_student_record()

            if record:
                student_data['school'] = record.highschool.label
                student_data['city'] = record.highschool.city
                student_data['class'] = record.class_name

        elif student.is_student():
            student_data['profile'] = _('Student')

            record = student.get_student_record()

            if record:
                student_data['school'] = record.home_institution
                student_data['class'] = ""

        response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('SCUIO-IP', 'REF-CMP', 'REF-LYC')
def ajax_get_highschool_students(request, highschool_id=None):
    """
    Retrieve students from a highschool or all students if user is scuio-ip manager
    and no highschool id is specified
    """
    no_record_filter = False
    response = {'data': [], 'msg': ''}

    if request.user.is_scuio_ip_manager():
        no_record_filter = resolve(request.path_info).url_name == 'get_students_without_record'

    if not highschool_id:
        try:
            highschool_id = request.user.highschool.id
        except Exception:
            if not request.user.is_scuio_ip_manager():
                response = {'data': [], 'msg': _('Invalid parameters')}
                return JsonResponse(response, safe=False)

    if highschool_id:
        students = ImmersionUser.objects.prefetch_related('high_school_student_record', 'immersions').filter(
            validation_string__isnull=True, high_school_student_record__highschool__id=highschool_id
        )
    else:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record', 'student_record', 'immersions'
        ).filter(validation_string__isnull=True, groups__name__in=['ETU', 'LYC'])

    if no_record_filter:
        students = students.filter(high_school_student_record__isnull=True, student_record__isnull=True)
    else:
        students = students.filter(Q(high_school_student_record__isnull=False) | Q(student_record__isnull=False))

    for student in students:
        record = None
        link = ''
        try:
            if student.is_high_school_student():
                record = student.high_school_student_record
                link = reverse('immersion:modify_hs_record', kwargs={'record_id': record.id})
            else:
                record = student.student_record
                link = reverse('immersion:modify_student_record', kwargs={'record_id': record.id})
        except Exception:
            pass

        student_data = {
            'id': student.pk,
            'name': "%s %s" % (student.last_name, student.first_name),
            'birthdate': date_format(record.birth_date) if record else '-',
            'institution': '',
            'level': record.get_level_display() if record else '-',
            'bachelor': '',
            'post_bachelor_level': '',
            'class': '',
            'registered': student.immersions.exists(),
            'record_link': link,
        }

        if record:
            if student.is_high_school_student():
                student_data['class'] = record.class_name
                student_data['institution'] = record.highschool.label

                if record.level == 3:
                    student_data['bachelor'] = record.get_origin_bachelor_type_display()
                    student_data['post_bachelor_level'] = record.get_post_bachelor_level_display()
                else:
                    student_data['bachelor'] = record.get_bachelor_type_display()

            elif student.is_student():
                student_data['bachelor'] = record.get_origin_bachelor_type_display()
                student_data['institution'] = record.home_institution
                student_data['post_bachelor_level'] = record.current_diploma

        response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('SCUIO-IP', 'REF-COMP', 'ENS-CH')
def ajax_send_email(request):
    """
    Send an email to all students registered to a specific slot
    """
    slot_id = request.POST.get('slot_id', None)
    send_copy = request.POST.get('send_copy', False) == "true"
    subject = request.POST.get('subject', "")
    body = request.POST.get('body', "")

    response = {'error': False, 'msg': ''}

    if not slot_id or not body.strip() or not subject.strip():
        response = {'error': True, 'msg': gettext("Invalid parameters")}
        return JsonResponse(response, safe=False)

    immersions = Immersion.objects.filter(slot_id=slot_id)

    for immersion in immersions:
        recipient = immersion.student.email
        try:
            send_email(recipient, subject, body)
        except Exception:
            response['error'] = True
            response['msg'] += _("%s : error") % recipient

    # Send a copy to the sender if requested - append "(copy)" to the subject
    if send_copy:
        subject = "%s (%s)" % (subject, _("copy"))
        recipient = request.user.email
        try:
            send_email(recipient, subject, body)
        except Exception:
            response['error'] = True
            response['msg'] += _("%s : error") % recipient

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('SCUIO-IP', 'REF-CMP')
def ajax_batch_cancel_registration(request):
    """
    Cancel registrations to immersions slots
    """
    immersion_ids = request.POST.get('immersion_ids')
    reason_id = request.POST.get('reason_id')

    err_msg = None
    err = False

    if not immersion_ids or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        for immersion_id in json.loads(immersion_ids):

            try:
                immersion = Immersion.objects.get(pk=immersion_id)
                if immersion.slot.date <= datetime.datetime.today().date():
                    response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                    return JsonResponse(response, safe=False)
                cancellation_reason = CancelType.objects.get(pk=reason_id)
                immersion.cancellation_type = cancellation_reason
                immersion.save()
                immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

            except ImmersionUser.DoesNotExist:
                # should not happen !
                err_msg += _("User not found")
            except CancelType.DoesNotExist:
                # should not happen as well !
                response = {'error': True, 'msg': _("Invalid cancellation reason #id")}
                err = True

        if not err:
            response = {'error': False, 'msg': _("Immersion(s) cancelled"), 'err_msg': err_msg}

    return JsonResponse(response, safe=False)


@groups_required('REF-CMP')
def get_csv_components(request, component_id):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    component = Component.objects.get(id=component_id).label.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{component}_{today}.csv"'
    slots = Slot.objects.filter(course__component_id=component_id, published=True)

    infield_separator = '|'

    header = [
        _('domain'),
        _('subdomain'),
        _('training'),
        _('course'),
        _('course type'),
        _('date'),
        _('start_time'),
        _('end_time'),
        _('campus'),
        _('building'),
        _('room'),
        _('teachers'),
        _('registration number'),
        _('place number'),
        _('additional information'),
    ]
    content = []
    for slot in slots:
        line = [
            infield_separator.join([sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]),
            infield_separator.join([sub.label for sub in slot.course.training.training_subdomains.all()]),
            slot.course.training.label,
            slot.course.label,
            slot.course_type.label,
            _date(slot.date, 'l d/m/Y'),
            slot.start_time.strftime('%H:%M'),
            slot.end_time.strftime('%H:%M'),
            slot.campus.label,
            slot.building.label,
            slot.room,
            '|'.join([f'{t.first_name} {t.last_name}' for t in slot.teachers.all()]),
            slot.registered_students(),
            slot.n_places,
            slot.additional_information,
        ]
        content.append(line.copy())

    writer = csv.writer(response)
    writer.writerow(header)
    for row in content:
        writer.writerow(row)

    return response


@groups_required('REF-LYC',)
def get_csv_highschool(request, high_school_id):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    h_name = HighSchool.objects.get(id=high_school_id).label.replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{h_name}_{today}.csv"'

    infield_separator = '|'

    header = [
        _('last name'),
        _('first name'),
        _('birthdate'),
        _('level'),
        _('class name'),
        _('bachelor type'),
        _('training domain'),
        _('training subdomain'),
        _('training'),
        _('course'),
    ]

    content = []
    hs_records = HighSchoolStudentRecord.objects.filter(highschool__id=high_school_id)
    for hs in hs_records:
        immersions = Immersion.objects.filter(student=hs.student, cancellation_type__isnull=True)
        if immersions.count() > 0:
            for imm in immersions:
                content.append(
                    [
                        hs.student.last_name,
                        hs.student.first_name,
                        _date(hs.birth_date, 'd/m/Y'),
                        HighSchoolStudentRecord.LEVELS[hs.level - 1][1],
                        hs.class_name,
                        HighSchoolStudentRecord.BACHELOR_TYPES[hs.bachelor_type - 1][1],
                        infield_separator.join([s.training_domain.label for s in imm.slot.course.training.training_subdomains.all()]),
                        infield_separator.join([s.label for s in imm.slot.course.training.training_subdomains.all()]),
                        imm.slot.course.training.label,
                        imm.slot.course.label,
                    ]
                )
        else:
            content.append(
                [
                    hs.student.last_name,
                    hs.student.first_name,
                    _date(hs.birth_date, 'd/m/Y'),
                    HighSchoolStudentRecord.LEVELS[hs.level - 1][1] if hs.level else '',
                    hs.class_name,
                    HighSchoolStudentRecord.BACHELOR_TYPES[hs.bachelor_type - 1][1] if hs.bachelor_type else '',
                ]
            )

    writer = csv.writer(response)
    writer.writerow(header)
    for row in content:
        writer.writerow(row)

    return response


@groups_required('SCUIO-IP',)
def get_csv_anonymous_immersion(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    trad = _('anonymous_immersion')
    response['Content-Disposition'] = f'attachment; filename="{trad}_{today}.csv"'

    infield_separator = '|'

    header = [
        _('component'),
        _('training domain'),
        _('training subdomain'),
        _('training'),
        _('course'),
        _('course_type'),
        _('date'),
        _('start_time'),
        _('end_time'),
        _('campus'),
        _('building'),
        _('room'),
        _('registration number'),
        _('place number'),
        _('additional information'),
        _('origin institution'),
        _('student level'),
    ]

    content = []

    slots = Slot.objects.filter(published=True)
    for slot in slots:
        immersions = Immersion.objects.filter(slot=slot, cancellation_type__isnull=True)
        if immersions.count() > 0:
            for imm in immersions:
                institution = ''
                level = ''
                if imm.student.is_student():
                    record = StudentRecord.objects.get(student=imm.student)
                    institution = record.home_institution
                    level = StudentRecord.LEVELS[record.level - 1][1]
                elif imm.student.is_high_school_student():
                    record = HighSchoolStudentRecord.objects.get(student=imm.student)
                    institution = record.highschool.label
                    level = HighSchoolStudentRecord.LEVELS[record.level - 1][1]

                content.append(
                    [
                        slot.course.component.label,
                        infield_separator.join([sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]),
                        infield_separator.join([sub.label for sub in slot.course.training.training_subdomains.all()]),
                        slot.course.training.label,
                        slot.course.label,
                        slot.course_type.label,
                        _date(slot.date, 'd/m/Y'),
                        slot.start_time.strftime('%H:%M'),
                        slot.end_time.strftime('%H:%M'),
                        slot.campus.label,
                        slot.building.label,
                        slot.room,
                        slot.registered_students(),
                        slot.n_places,
                        slot.additional_information,
                        institution,
                        level,
                    ]
                )
        else:
            content.append([
                    slot.course.component.label,
                    infield_separator.join([sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]),
                    infield_separator.join([sub.label for sub in slot.course.training.training_subdomains.all()]),
                    slot.course.training.label,
                    slot.course.label,
                    slot.course_type.label,
                    _date(slot.date, 'd/m/Y'),
                    slot.start_time.strftime('%H:%M'),
                    slot.end_time.strftime('%H:%M'),
                    slot.campus.label,
                    slot.building.label,
                    slot.room,
                    slot.registered_students(),
                    slot.n_places,
                    slot.additional_information,
                ])

    writer = csv.writer(response)
    writer.writerow(header)
    for row in content:
        writer.writerow(row)

    return response


@is_ajax_request
@is_post_request
def ajax_send_email_contact_us(request):
    """
    Send an email to SCUO-IP mail address
    email address is set in general settings
    """

    subject = request.POST.get('subject', "")
    body = request.POST.get('body', "")
    lastname = request.POST.get('lastname', "").capitalize()
    firstname = request.POST.get('firstname', "").capitalize()
    email = request.POST.get('email', "")

    try:
        # TODO: Maybe use an util getter method for General settings
        recipient = GeneralSettings.objects.get(setting='MAIL_CONTACT_SCUIO_IP').value
    except Exception:
        logger.error('MAIL_CONTACT_SCUIO_IP missing parameter')
        response = {'error': True, 'msg': gettext("Config parameter not found")}
        return JsonResponse(response, safe=False)

    response = {'error': False, 'msg': ''}

    if not subject.strip or not body.strip() or not lastname.strip() or not firstname.strip() or not email.strip():
        response = {'error': True, 'msg': gettext("Invalid parameters")}
        return JsonResponse(response, safe=False)

    # Scuio-ip mail sending
    try:
        send_email(recipient, subject, body, f'{firstname} {lastname} <{email}>')
    except Exception:
        response['error'] = True
        response['msg'] += _("%s : error") % recipient

    try:
        template = MailTemplate.objects.get(code='CONTACTUS_NOTIFICATION', active=True)
        logger.debug("Template found : %s" % template)
    except MailTemplate.DoesNotExist:
        msg = _("Email not sent : template %s not found or inactive" % template_code)
        logger.error(msg)

    # Contacting user mail notification
    try:
        vars = [
            ('${nom}', lastname),
            ('${prenom}', firstname),
        ]

        message_body = multisub(vars, template.body)
        send_email(email, template.subject, message_body)
    except Exception as e:
        logger.exception(e)
        msg = _("Error while sending mail : %s" % e)

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('SCUIO-IP', 'SRV-JUR')
def ajax_get_student_presence(request, date_from=None, date_until=None):
    response = {'data': [], 'msg': ''}

    filters = {}

    if date_from and date_from != "None":
        filters["slot__date__gte"] = date_from

    if date_until and date_until != "None":
        filters["slot__date__lte"] = date_until

    immersions = Immersion.objects.prefetch_related('slot', 'student').filter(**filters)

    for immersion in immersions:
        institution = ''

        if immersion.student.is_high_school_student():
            record = immersion.student.get_high_school_student_record()
            institution = record.highschool.label if record else ''
        elif immersion.student.get_student_record():
            record = immersion.student.get_student_record()
            institution = record.home_institution if record else ''

        immersion_data = {
            'id': immersion.pk,
            'date': _date(immersion.slot.date, 'l d/m/Y'),
            'time': {
                'start': immersion.slot.start_time.strftime('%Hh%M') if immersion.slot.start_time else '',
                'end': immersion.slot.end_time.strftime('%Hh%M') if immersion.slot.end_time else '',
            },
            'datetime': datetime.datetime.strptime(
                "%s:%s:%s %s:%s"
                % (immersion.slot.date.year, immersion.slot.date.month, immersion.slot.date.day,
                   immersion.slot.start_time.hour, immersion.slot.start_time.minute,),
                "%Y:%m:%d %H:%M",
            )
            if immersion.slot.date
            else None,
            'name': "%s %s" % (immersion.student.last_name, immersion.student.first_name),
            'institution': institution,
            'phone': record.phone if record and record.phone else '',
            'email': immersion.student.email,
            'campus': immersion.slot.campus.label,
            'building': immersion.slot.building.label,
            'room': immersion.slot.room,
        }

        response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)