"""
API Views
"""
import csv
import datetime
import importlib
import json
import logging
from itertools import chain, permutations
import django_filters.rest_framework
from functools import reduce


import django_filters.rest_framework
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.exceptions import FieldError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.defaultfilters import date as _date
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.module_loading import import_string
from django.utils.translation import gettext, pgettext, gettext_lazy as _
from rest_framework import generics, status

"""
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
"""

from immersionlyceens.apps.core.models import (
    Building, Calendar, Campus, CancelType, Course, Establishment, HighSchool,
    Holiday, Immersion, ImmersionUser, MailTemplate, MailTemplateVars,
    PublicDocument, Slot, Structure, Training, TrainingDomain, UniversityYear,
    UserCourseAlert, Vacation, Visit, OffOfferEvent
)
from immersionlyceens.apps.core.serializers import (
    BuildingSerializer, CampusSerializer, EstablishmentSerializer, StructureSerializer, CourseSerializer,
    TrainingHighSchoolSerializer, VisitSerializer, OffOfferEventSerializer
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord,
)
from immersionlyceens.decorators import (
    groups_required, is_ajax_request, is_post_request,
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting, render_text

logger = logging.getLogger(__name__)


@is_ajax_request
@groups_required("REF-ETAB-MAITRE", "REF-ETAB", "REF-STR", "REF-LYC")
def ajax_get_person(request):
    response = {'msg': '', 'data': []}
    search_str = request.POST.get("username", None)
    query_order = request.POST.get("query_order")
    establishment_id = request.POST.get('establishment_id', None)
    structure_id = request.POST.get('structure_id', None)
    highschool_id = request.POST.get('highschool_id', None)

    users_queryset = None
    establishment = None
    highschool = None

    if not search_str:
        response['msg'] = gettext("Search string is empty")
        return JsonResponse(response, safe=False)

    try:
        structure_id = int(structure_id)
    except (ValueError, TypeError):
        structure_id = None

    try:
        highschool_id = int(highschool_id)
    except (ValueError, TypeError):
        highschool_id = None

    if establishment_id is None and highschool_id is None:
        response['msg'] = gettext("Please select an establishment or a high school first")
        return JsonResponse(response, safe=False)

    if establishment_id:
        try:
            establishment = Establishment.objects.get(pk=establishment_id)
        except Establishment.DoesNotExist:
            response['msg'] = gettext("Sorry, establishment not found")
            return JsonResponse(response, safe=False)
    elif highschool_id:
        try:
            highschool = HighSchool.objects.get(pk=highschool_id)
        except HighSchool.DoesNotExist:
            response['msg'] = gettext("Sorry, high school not found")
            return JsonResponse(response, safe=False)

    if establishment:
        if establishment.data_source_plugin:
            try:
                module_name = settings.ACCOUNTS_PLUGINS[establishment.data_source_plugin]
                source = importlib.import_module(module_name, package=None)
                account_api = source.AccountAPI(establishment)

                persons_list = [query_order]

                users = account_api.search_user(search_str)

                if users != False:
                    users = sorted(users, key=lambda u: [u['lastname'], u['firstname']])
                    response['data'] = persons_list + users
                else:
                    response['msg'] = gettext("Error : can't query establishment accounts data source")

            except KeyError:
                pass
            except Exception as e:
                response['msg'] = gettext("Error : %s" % e)
        else:
            filters = {
                'groups__name': 'INTER',
                'last_name__istartswith': search_str
            }

            if structure_id is not None:
                Q_filter = Q(establishment=establishment)|Q(structures=structure_id)
            else:
                Q_filter = Q(establishment=establishment)
                filters["establishment"] = establishment

            users_queryset = ImmersionUser.objects.filter(Q_filter, **filters)

    elif highschool:
        users_queryset = ImmersionUser.objects.filter(
            highschool=highschool,
            groups__name='INTER',
            last_name__istartswith=search_str
        )

    if users_queryset:
        response['data'] = [query_order] + [{
            'username': user.username,
            'firstname': user.first_name,
            'lastname': user.last_name,
            'email': user.email,
            'display_name': f"{user.last_name} {user.first_name}"
        } for user in users_queryset]

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", 'REF-ETAB-MAITRE')
def ajax_get_available_vars(request, template_id=None):
    response = {'msg': '', 'data': []}

    if template_id:
        template_vars = MailTemplateVars.objects.filter(mail_templates=template_id)
        response["data"] = [{'id': v.id, 'code': v.code, 'description': v.description} for v in template_vars]
    else:
        response["msg"] = gettext("Error : no template id")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER')
def ajax_get_courses(request):
    response = {'msg': '', 'data': []}

    structure_id = request.GET.get('structure')
    highschool_id = request.GET.get('highschool')
    filters = {}
    speaker_filter = {}
    user_filter = False

    if request.user.is_speaker():
        user_filter = True
        filters["speakers"] = request.user
        speaker_filter["speaker_id"] = request.user

    try:
        int(structure_id)
        filters["training__structures"] = structure_id
    except (TypeError, ValueError):
        structure_id = None

    try:
        int(highschool_id)
        filters["training__highschool"] = highschool_id
    except (TypeError, ValueError):
        highschool_id = None

    if not user_filter and not structure_id and not highschool_id:
        response['msg'] = gettext("Error : a valid structure or high school must be selected")
        return JsonResponse(response, safe=False)

    courses = Course.objects.prefetch_related('training', 'highschool', 'structure').filter(**filters)

    allowed_structures = request.user.get_authorized_structures()

    for course in courses:
        managed_by = None
        has_rights = False

        if course.structure:
            managed_by = f"{course.structure.code} ({course.structure.establishment.short_label})"
            has_rights = (course.structures.all() & allowed_structures).exists()
        elif course.highschool:
            managed_by = f"{course.highschool.city} - {course.highschool.label}"
            has_rights = request.user.is_master_establishment_manager() or course.highschool == request.user.highschool

        course_data = {
            'id': course.id,
            'published': course.published,
            'training_label': course.training.label,
            'label': course.label,
            'managed_by': managed_by,
            'structure_code': course.structure.code if course.structure else None,
            'structure_id': course.structure.id if course.structure else None,
            'highschool_id': course.highschool.id if course.highschool else None,
            'highschool_label': f"{course.highschool.city} - {course.highschool.label}" if course.highschool else None,
            'speakers': [],
            'slots_count': course.slots_count(**speaker_filter),
            'n_places': course.free_seats(**speaker_filter),
            'published_slots_count': course.published_slots_count(**speaker_filter),
            'registered_students_count': course.registrations_count(**speaker_filter),
            'alerts_count': course.get_alerts_count(),
            'has_rights': has_rights,
            'can_delete': not course.slots.exists(),
        }

        for speaker in course.speakers.all().order_by('last_name', 'first_name'):
            course_data['speakers'].append({
                'name': f"{speaker.last_name} {speaker.first_name}",
                'email': speaker.email
            })

        response['data'].append(course_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", "REF-STR", 'REF-ETAB-MAITRE', 'REF-LYC')
def ajax_get_trainings(request):
    """
    Get trainings linked to a structure or a highschool
    GET params :
    - 'type' : 'highschool' or 'structure'
    - 'object_id' : highschool or structure id
    """

    response = {'msg': '', 'data': []}

    object_type = request.GET.get("type")
    object_id = request.GET.get("object_id")

    if object_type == 'structure':
        filters = {'structures': object_id, 'active':True}
    elif object_type == 'highschool':
        filters = {'highschool': object_id, 'active': True}
    else:
        response['msg'] = gettext("Error : invalid parameter 'object_type' value")
        return JsonResponse(response, safe=False)

    if not object_id:
        response['msg'] = gettext("Error : a valid structure or high school must be selected")
        return JsonResponse(response, safe=False)

    try:
        trainings = (
            Training.objects.prefetch_related('training_subdomains')
            .filter(**filters)
            .order_by('label')
        )
    except FieldError:
        # Not implemented yet
        trainings = Training.objects.none()

    for training in trainings:
        training_data = {
            'id': training.id,
            'label': training.label,
            'subdomain': [s.label for s in training.training_subdomains.filter(active=True)],
        }

        response['data'].append(training_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER')
def ajax_get_slots(request):
    """
    Get slots list according to GET parameters
    :return:
    """
    response = {'msg': '', 'data': []}
    can_update_attendances = False
    today = datetime.datetime.today()
    user_filter = False
    filters = {}
    slots = []

    try:
        year = UniversityYear.objects.get(active=True)
        can_update_attendances = today.date() <= year.end_date
    except UniversityYear.DoesNotExist:
        pass

    training_id = request.GET.get('training_id')
    structure_id = request.GET.get('structure_id')
    highschool_id = request.GET.get('highschool_id')
    establishment_id = request.GET.get('establishment_id')
    visits = request.GET.get('visits', False) == "true"
    past_slots = request.GET.get('past', False) == "true"

    try:
        int(establishment_id)
    except (TypeError, ValueError):
        establishment_id = None

    try:
        int(structure_id)
    except (TypeError, ValueError):
        structure_id = None

    try:
        int(highschool_id)
    except (TypeError, ValueError):
        highschool_id = None

    try:
        int(training_id)
    except (TypeError, ValueError):
        training_id = None

    if request.user.is_speaker():
        user_filter = True
        filters["speakers"] = request.user

    if not user_filter and visits and not establishment_id:
        response['msg'] = gettext("Error : a valid establishment must be selected")
        return JsonResponse(response, safe=False)

    if not user_filter and not visits and not structure_id and not highschool_id:
        response['msg'] = gettext("Error : a valid structure or high school must be selected")
        return JsonResponse(response, safe=False)

    if visits:
        filters["course__isnull"] = True
        filters['visit__establishment__id'] = establishment_id

        if structure_id is not None:
            filters['visit__structure__id'] = structure_id

        slots = Slot.objects.prefetch_related(
            'visit__establishment', 'visit__structure', 'visit__highschool', 'speakers', 'immersions') \
            .filter(**filters)

        user_filter_key = "visit__structure__in"
    else:
        filters["visit__isnull"] = True

        if training_id is not None:
            filters['course__training__id'] = training_id
        elif structure_id is not None:
            filters['course__training__structures__id'] = structure_id
        elif highschool_id is not None:
            filters['course__training__highschool__id'] = highschool_id

        slots = Slot.objects.prefetch_related(
            'course__training__structures', 'course__training__highschool', 'speakers', 'immersions')\
            .filter(**filters)

        user_filter_key = "course__structure__in"

    if not request.user.is_superuser and request.user.is_structure_manager():
        user_filter = {user_filter_key: request.user.structures.all()}
        slots = slots.filter(**user_filter)

    if user_filter:
        if past_slots:
            slots = slots.exclude(date__lt=today.date(), immersions__isnull=True).distinct()
        else:
            slots = slots.filter(
                Q(date__gte=today.date())
                | Q(date=today.date(), end_time__gte=today.time())
                | Q(immersions__attendance_status=0, immersions__cancellation_type__isnull=True)
            ).distinct()

    all_data = []
    allowed_structures = request.user.get_authorized_structures()
    user_establishment = request.user.establishment
    user_highschool = request.user.highschool

    for slot in slots:
        structure = slot.get_structure()
        highschool = slot.get_highschool()

        allowed_visit_slot_update_conditions = [
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and slot.visit and slot.visit.establishment == user_establishment,
            request.user.is_structure_manager() and slot.visit and slot.visit.structure in allowed_structures
        ]

        if slot.course:
            training_label = f'{slot.course.training.label} ({slot.course_type.label})'
            training_label_full = f'{slot.course.training.label} ({slot.course_type.full_label})'
        else:
            training_label = None
            training_label_full = None

        data = {
            'id': slot.id,
            'published': slot.published,
            'can_update_visit_slot': any(allowed_visit_slot_update_conditions),
            'course_label': slot.course.label if slot.course else None,
            'training_label': training_label,
            'training_label_full': training_label_full,
            'structure': {
                'code': structure.code,
                'establishment': structure.establishment.short_label,
                'managed_by_me': structure in allowed_structures,
            } if structure else None,
            'highschool': {
                'label': f"{highschool.city} - {highschool.label}",
                'managed_by_me': request.user.is_master_establishment_manager()\
                    or (user_highschool and highschool == user_highschool),
            } if highschool else None,
            'purpose': slot.visit.purpose if slot.visit else None,
            'course_type': slot.course_type.label if slot.course_type is not None else '-',
            'course_type_full': slot.course_type.full_label if slot.course_type is not None else '-',
            'datetime': datetime.datetime.strptime(
                "%s:%s:%s %s:%s"
                % (slot.date.year, slot.date.month, slot.date.day, slot.start_time.hour, slot.start_time.minute,),
                "%Y:%m:%d %H:%M",
            ) if slot.date else None,
            'date': _date(slot.date, 'l d/m/Y'),
            'time': {
                'start': slot.start_time.strftime('%Hh%M') if slot.start_time else '',
                'end': slot.end_time.strftime('%Hh%M') if slot.end_time else '',
            },
            'location': {
                'campus': slot.campus.label if slot.campus else '',
                'building': slot.building.label if slot.building else '',
            },
            'face_to_face': slot.face_to_face,
            'url': slot.url,
            'room': slot.room or '-',
            'speakers': {},
            'n_register': slot.registered_students(),
            'n_places': slot.n_places if slot.n_places is not None else 0,
            'additional_information': slot.additional_information,
            'attendances_value': 0,
            'attendances_status': '',
            'is_past': False,
        }

        if data['datetime'] and data['datetime'] <= today:
            data['is_past'] = True
            if not slot.immersions.filter(cancellation_type__isnull=True).exists():
                data['attendances_value'] = -1  # nothing
            elif (
                slot.immersions.filter(attendance_status=0, cancellation_type__isnull=True).exists()
                or can_update_attendances
            ):
                data['attendances_value'] = 1  # to enter
                data['attendances_status'] = gettext("To enter")
            else:
                data['attendances_value'] = 2  # view only
                data['attendances_status'] = gettext("Entered")
        else:
            data['attendances_status'] = gettext("Future slot")

        for speaker in slot.speakers.all().order_by('last_name', 'first_name'):
            data['speakers'].update([(f"{speaker.last_name} {speaker.first_name}", speaker.email,)],)

        all_data.append(data.copy())

    response['data'] = all_data

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_courses_by_training(request, structure_id=None, training_id=None):
    response = {'msg': '', 'data': []}

    if not structure_id:
        response['msg'] = gettext("Error : a valid structure must be selected")
    if not training_id:
        response['msg'] = gettext("Error : a valid training must be selected")

    courses = (
        Course.objects.prefetch_related('training')
        .filter(training__id=training_id, structure__id=structure_id,)
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def ajax_get_course_speakers(request, course_id=None):
    response = {'msg': '', 'data': []}

    if not course_id:
        response['msg'] = gettext("Error : a valid course must be selected")
    else:
        speakers = Course.objects.get(id=course_id).speakers.all().order_by('last_name')

        for speaker in speakers:
            speakers_data = {
                'id': speaker.id,
                'first_name': speaker.first_name,
                'last_name': speaker.last_name.upper(),
            }
            response['data'].append(speakers_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def ajax_get_visit_speakers(request, visit_id=None):
    response = {'msg': '', 'data': []}

    if not visit_id:
        response['msg'] = gettext("Error : a valid visit must be selected")
    else:
        speakers = Visit.objects.get(id=visit_id).speakers.all().order_by('last_name')

        for speaker in speakers:
            speakers_data = {
                'id': speaker.id,
                'first_name': speaker.first_name,
                'last_name': speaker.last_name.upper(),
            }
            response['data'].append(speakers_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def ajax_delete_course(request):
    response = {'msg': '', 'error': ''}
    course_id = request.GET.get('course_id')

    if course_id is None:
        response['error'] = gettext("Error : a valid course must be selected")
        return JsonResponse(response, safe=False)

    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        response['error'] = gettext("Error : a valid course must be selected")
        return JsonResponse(response, safe=False)

    # Check rights
    if not request.user.has_course_rights(course_id):
        response['error'] = gettext("Error : you can't delete this course")
        return JsonResponse(response, safe=False)

    course = Course.objects.get(pk=course_id)
    if not course.slots.exists():
        course.delete()
        response['msg'] = gettext("Course successfully deleted")
    else:
        response['error'] = gettext("Error : slots are linked to this course")

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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def ajax_check_date_between_vacation(request):
    response = {'data': {}, 'msg': ''}

    _date = request.GET.get('date')

    if _date:
        # two format date
        error = False
        try:
            formated_date = datetime.datetime.strptime(_date, '%Y/%m/%d')
        except ValueError:
            error = True
        if error:
            try:
                formated_date = datetime.datetime.strptime(_date, '%d/%m/%Y')
            except ValueError:
                response['msg'] = gettext('Error: bad date format')
                return JsonResponse(response, safe=False)

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
@groups_required('REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE')
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


# REJECT / VALIDATE STUDENT
@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def ajax_validate_reject_student(request, validate):
    """
    Validate or reject student
    """
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

    response = {'data': None, 'msg': ''}

    student_record_id = request.POST.get('student_record_id')
    if student_record_id:
        hs = None
        if request.user.is_establishment_manager():
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
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def ajax_validate_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=True)


@is_ajax_request
@is_post_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def ajax_reject_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=False)


@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def ajax_check_course_publication(request, course_id):
    from immersionlyceens.apps.core.models import Course

    response = {'data': None, 'msg': ''}

    c = Course.objects.get(id=course_id)
    response['data'] = {'published': c.published}

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE')
def ajax_delete_account(request):
    """
    Completely destroy a student account and all data
    """
    account_id = request.POST.get('account_id')
    send_mail = request.POST.get('send_email', False) == "true"

    if not account_id:
        response = {'error': True, 'msg': gettext("Missing parameter")}
        return JsonResponse(response, safe=False)

    try:
        account = ImmersionUser.objects.get(id=account_id) # , groups__name__in=['LYC', 'ETU'])
    except ImmersionUser.DoesNotExist:
        response = {'error': True, 'msg': gettext("Account not found")}
        return JsonResponse(response, safe=False)

    if send_mail and account.groups.filter(name__in=['LYC', 'ETU']):
        account.send_message(request, 'CPT_DELETE')

    if not request.user.is_superuser:
        if account.is_speaker():
            if account.slots.exists():
                response = {'error': True, 'msg': gettext("You can't delete this account (this user has slots)")}
                return JsonResponse(response, safe=False)

            if request.user.is_high_school_manager():
                if not request.user.highschool or request.user.highschool != account.highschool:
                    response = {'error': True, 'msg': gettext("You can't delete this account (insufficient privileges)")}
                    return JsonResponse(response, safe=False)

            if request.user.is_establishment_manager():
                if not request.user.establishment or request.user.establishment != account.establishment:
                    response = {'error': True, 'msg': gettext("You can't delete this account (insufficient privileges)")}
                    return JsonResponse(response, safe=False)

        elif account.is_high_school_student():
            record = account.get_high_school_student_record()
            if record:
                HighSchoolStudentRecord.clear_duplicate(record.id)

        elif account.is_student():
            pass

        else:
            response = {'error': True, 'msg': gettext("You can't delete this account (invalid group)")}
            return JsonResponse(response, safe=False)

    account.delete()

    messages.success(request, _("User deleted successfully"))

    response = {'error': False, 'msg': gettext("Account deleted")}
    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-ETAB-MAITRE')
def ajax_cancel_registration(request):
    """
    Cancel a registration to an immersion slot
    """
    immersion_id = request.POST.get('immersion_id')
    reason_id = request.POST.get('reason_id')
    today = datetime.datetime.today()

    if not immersion_id or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            immersion = Immersion.objects.get(pk=immersion_id)
            if immersion.slot.date < today.date() or (immersion.slot.date == today.date()
                                                      and immersion.slot.start_time < today.time()):
                response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                return JsonResponse(response, safe=False)

            cancellation_reason = CancelType.objects.get(pk=reason_id)
            immersion.cancellation_type = cancellation_reason
            immersion.save()
            immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

            response = {'error': False, 'msg': gettext("Immersion cancelled")}
        except Immersion.DoesNotExist:
            response = {'error': True, 'msg': gettext("User not found")}
        except CancelType.DoesNotExist:
            response = {'error': True, 'msg': gettext("Invalid cancellation reason #id")}

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-LYC', 'REF-ETAB-MAITRE')
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
        not request.user.is_establishment_manager()
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

    time = f"{datetime.datetime.now().hour}:{datetime.datetime.now().minute}"

    immersions = Immersion.objects.prefetch_related(
        'slot__course__training', 'slot__course_type', 'slot__campus', 'slot__building', 'slot__speakers',
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
            'speakers': [],
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
            immersion.slot.date == today and immersion.slot.start_time > datetime.datetime.today().time()
        ):
            immersion_data['time_type'] = "future"

        if immersion.slot.n_places:
            immersion_data['free_seats'] = immersion.slot.n_places - immersion.slot.registered_students()

        if immersion.cancellation_type:
            immersion_data['cancellation_type'] = immersion.cancellation_type.label

            if slot_datetime > datetime.datetime.today() and immersion.slot.available_seats() > 0:
                if slot_semester and remainings[str(slot_semester)] or not slot_semester and remaining_annually:
                    immersion_data['can_register'] = True

        for speaker in immersion.slot.speakers.all().order_by('last_name', 'first_name'):
            immersion_data['speakers'].append(f"{speaker.last_name} {speaker.first_name}")

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
            student_data = {'name': f"{student.last_name} {student.first_name}", 'email': ""}

            if student.high_school_student_record.visible_email:
                student_data["email"] = student.email

            response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-LYC')
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
                    uai_code, institution = record.home_institution()
                    immersion_data['school'] = institution.label if institution else uai_code
                    immersion_data['level'] = record.get_level_display()

            response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE')
def ajax_set_attendance(request):
    """
    Update immersion attendance status
    """
    immersion_id = request.POST.get('immersion_id', None)
    immersion_ids = request.POST.get('immersion_ids', None)

    response = {'success': '', 'error': '', 'data': []}

    if immersion_ids:
        immersion_ids = json.loads(immersion_ids)

    attendance_value = request.POST.get('attendance_value')
    if not attendance_value:
        response['error'] = gettext("Error: no attendance status set in parameter")
        return JsonResponse(response, safe=False)

    if not immersion_id and not immersion_ids:
        response['error'] = gettext("Error: missing immersion id parameter")
        return JsonResponse(response, safe=False)

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
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-STR', 'REF-ETAB-MAITRE')
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
    structure = request.POST.get('structure', False)
    calendar, slot, student = None, None, None
    can_force_reg = request.user.is_establishment_manager()
    today = datetime.datetime.today().date()
    today_time = datetime.datetime.today().time()

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
        except Slot.DoesNotExist:
            pass

    if not slot or not student:
        response = {'error': True, 'msg': _("Invalid parameters")}
        return JsonResponse(response, safe=False)

    # Check slot is published for no ref-etab user
    if not request.user.is_establishment_manager() and not slot.published:
        response = {'error': True, 'msg': _("Registering an unpublished slot is forbidden")}
        return JsonResponse(response, safe=False)

    # Only valid Highschool students
    if student.is_high_school_student and not student.is_valid():
        record = student.get_high_school_student_record()
        if not record or (record and not record.is_valid()):
            response = {'error': True, 'msg': _("Cannot register slot due to Highschool student account state")}
            return JsonResponse(response, safe=False)

    # Check if slot is not past
    if slot.date < today or (slot.date == today and today_time > slot.start_time):
        response = {'error': True, 'msg': _("Register to past slot is not available")}
        return JsonResponse(response, safe=False)

    # Check free seat in slot
    if slot.available_seats() == 0:
        response = {'error': True, 'msg': _("No seat available for selected slot")}
        return JsonResponse(response, safe=False)

    # Check current student immersions and valid dates
    if student.immersions.filter(slot=slot, cancellation_type__isnull=True).exists():
        if not structure:
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
                    student.set_increment_registrations_(type='annual')
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
                # ref str request & no more remaining registration count for student
                elif request.user.is_structure_manager and remaining_regs_count['annually'] <= 0:
                    response = {
                        'error': True,
                        'msg': _("This student has no more remaining slots to register to"),
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
                        student.set_increment_registrations_(type='semester1')
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
                    # ref str request & no more remaining registration count for student
                    elif request.user.is_structure_manager and remaining_regs_count['semester1'] <= 0:
                        response = {
                            'error': True,
                            'msg': _("This student has no more remaining slots to register to"),
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
                        student.set_increment_registrations_(type='semester2')
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
                    # ref str request & no more remaining registration count for student
                    elif request.user.is_structure_manager and remaining_regs_count['semester2'] <= 0:
                        response = {
                            'error': True,
                            'msg': _("This student has no more remaining slots to register to"),
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def ajax_get_available_students(request, slot_id):
    """
    Get students list for manual slot registration
    Students must have a valid record and not already registered to the slot
    """
    response = {'data': [], 'msg': ''}
    students = ImmersionUser.objects.filter(groups__name__in=['LYC', 'ETU']).exclude(immersions__slot__id=slot_id)

    for student in students:
        record = None

        if student.is_high_school_student():
            record = student.get_high_school_student_record()
        elif student.is_student():
            record = student.get_student_record()

        if record and record.is_valid():
            student_data = {
                'id': student.pk,
                'lastname': student.last_name,
                'firstname': student.first_name,
                'school': '',
                'class': '',
                'level': '',
                'city': '',
            }

            if student.is_high_school_student():
                student_data['profile'] = pgettext("person type", "High school student")
                student_data['school'] = record.highschool.label
                student_data['city'] = record.highschool.city
                student_data['class'] = record.class_name
            elif student.is_student():
                uai_code, institution = record.home_institution()
                student_data['profile'] = pgettext("person type", "Student")
                student_data['school'] = institution.label if institution else uai_code

            response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-LYC', 'REF-ETAB-MAITRE')
def ajax_get_highschool_students(request, highschool_id=None):
    """
    Retrieve students from a highschool or all students if user is ref-etab manager
    and no highschool id is specified
    """
    no_record_filter = False
    response = {'data': [], 'msg': ''}

    if request.user.is_establishment_manager():
        no_record_filter = resolve(request.path_info).url_name == 'get_students_without_record'

    if not highschool_id:
        try:
            highschool_id = request.user.highschool.id
        except Exception:
            if not request.user.is_establishment_manager():
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
        student_type = _('Unknown')
        link = ''
        try:
            if student.is_high_school_student():
                record = student.get_high_school_student_record()
                if record:
                    link = reverse('immersion:modify_hs_record', kwargs={'record_id': record.id})
                student_type = pgettext("person type", "High school student")
            else:
                record = student.get_student_record()
                if record:
                    link = reverse('immersion:modify_student_record', kwargs={'record_id': record.id})
                student_type = pgettext("person type", "Student")
        except Exception:
            pass

        student_data = {
            'id': student.pk,
            'name': f"{student.last_name} {student.first_name}",
            'birthdate': date_format(record.birth_date) if record else '-',
            'institution': '',
            'level': record.get_level_display() if record else '-',
            'bachelor': '',
            'post_bachelor_level': '',
            'class': '',
            'registered': student.immersions.exists(),
            'record_link': link,
            'student_type': student_type,
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
                uai_code, institution = record.home_institution()
                student_data['bachelor'] = record.get_origin_bachelor_type_display()
                student_data['institution'] = institution.label if institution else uai_code
                student_data['post_bachelor_level'] = record.current_diploma

        response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE')
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

    immersions = Immersion.objects.filter(slot_id=slot_id, cancellation_type__isnull=True)

    for immersion in immersions:
        recipient = immersion.student.email
        try:
            send_email(recipient, subject, body)
        except Exception:
            response['error'] = True
            response['msg'] += _("%s : error") % recipient

    # Send a copy to the sender if requested - append "(copy)" to the subject
    if send_copy:
        subject = "{} ({})".format(subject, _("copy"))
        recipient = request.user.email
        try:
            send_email(recipient, subject, body)
        except Exception:
            response['error'] = True
            response['msg'] += _("%s : error") % recipient

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def ajax_batch_cancel_registration(request):
    """
    Cancel registrations to immersions slots
    """
    immersion_ids = request.POST.get('immersion_ids')
    reason_id = request.POST.get('reason_id')

    err_msg = None
    err = False
    today = datetime.datetime.today()

    if not immersion_ids or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            json_data = json.loads(immersion_ids)
        except json.decoder.JSONDecodeError:
            response = {'error': True, 'msg': gettext("Invalid json decoding")}
            return JsonResponse(response, safe=False)
        for immersion_id in json_data:
            try:
                immersion = Immersion.objects.get(pk=immersion_id)
                if immersion.slot.date < today.date() or (immersion.slot.date == today.date() and
                                                          immersion.slot.start_time < today.time()):
                    response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                    return JsonResponse(response, safe=False)
                cancellation_reason = CancelType.objects.get(pk=reason_id)
                immersion.cancellation_type = cancellation_reason
                immersion.save()
                immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

            except Immersion.DoesNotExist:
                # should not happen !
                err_msg += _("Immersion not found")
            except CancelType.DoesNotExist:
                # should not happen as well !
                response = {'error': True, 'msg': _("Invalid cancellation reason #id")}
                err = True

        if not err:
            response = {'error': False, 'msg': _("Immersion(s) cancelled"), 'err_msg': err_msg}

    return JsonResponse(response, safe=False)


@groups_required('REF-STR')
def get_csv_structures(request, structure_id):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    structure = Structure.objects.get(id=structure_id).label.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{structure}_{today}.csv"'
    slots = Slot.objects.filter(course__structure_id=structure_id, published=True)

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
        _('speakers'),
        _('registration number'),
        _('place number'),
        _('additional information'),
    ]
    content = []
    for slot in slots:
        line = [
            infield_separator.join(
                [sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]
            ),
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
            '|'.join([f'{t.first_name} {t.last_name}' for t in slot.speakers.all()]),
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
                        infield_separator.join(
                            [s.training_domain.label for s in imm.slot.course.training.training_subdomains.all()]
                        ),
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


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE')
def get_csv_anonymous_immersion(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    trad = _('anonymous_immersion')
    response['Content-Disposition'] = f'attachment; filename="{trad}_{today}.csv"'

    infield_separator = '|'

    header = [
        _('structure')+ " / " + _("highschool"),
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
        _('emargement'),
    ]

    content = []

    slots = Slot.objects.filter(published=True)
    for slot in slots:
        managed_by = ""
        if slot.course.structure:
            managed_by = slot.course.structure.label
        elif slot.course.highschool:
            managed_by = f"{slot.course.highschool.city} - {slot.course.highschool.label}"

        immersions = Immersion.objects.prefetch_related('slot').filter(slot=slot, cancellation_type__isnull=True)
        if immersions.count() > 0:
            for imm in immersions:
                institution = ''
                level = ''
                record = None

                if imm.student.is_student():
                    try:
                        record = StudentRecord.objects.get(student=imm.student)
                        uai_code, institution = record.home_institution()
                        institution = institution.label if institution else uai_code
                        level = StudentRecord.LEVELS[record.level - 1][1]
                    except StudentRecord.DoesNotExist:
                        pass
                elif imm.student.is_high_school_student():
                    try:
                        record = HighSchoolStudentRecord.objects.get(student=imm.student)
                        institution = record.highschool.label
                        level = HighSchoolStudentRecord.LEVELS[record.level - 1][1]
                    except HighSchoolStudentRecord.DoesNotExist:
                        pass

                if record:
                    content.append([
                        managed_by,
                        infield_separator.join(
                            [sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]
                        ),
                        infield_separator.join(
                            [sub.label for sub in slot.course.training.training_subdomains.all()]
                        ),
                        slot.course.training.label,
                        slot.course.label,
                        slot.course_type.label,
                        _date(slot.date, 'd/m/Y'),
                        slot.start_time.strftime('%H:%M'),
                        slot.end_time.strftime('%H:%M'),
                        slot.campus.label if slot.campus else None,
                        slot.building.label if slot.building else None,
                        slot.room,
                        slot.registered_students(),
                        slot.n_places,
                        slot.additional_information,
                        institution,
                        level,
                        imm.get_attendance_status(),
                    ])
        else:
            content.append([
                managed_by,
                infield_separator.join(
                    [sub.training_domain.label for sub in slot.course.training.training_subdomains.all()]
                ),
                infield_separator.join([sub.label for sub in slot.course.training.training_subdomains.all()]),
                slot.course.training.label,
                slot.course.label,
                slot.course_type.label,
                _date(slot.date, 'd/m/Y'),
                slot.start_time.strftime('%H:%M'),
                slot.end_time.strftime('%H:%M'),
                slot.campus.label if slot.campus else None,
                slot.building.label if slot.building else None,
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
    notify_user = False

    try:
        recipient = get_general_setting('MAIL_CONTACT_REF_ETAB')
    except (NameError, ValueError):
        logger.error('MAIL_CONTACT_REF_ETAB not configured properly in settings')
        response = {'error': True, 'msg': gettext("Config parameter not found")}
        return JsonResponse(response, safe=False)

    response = {'error': False, 'msg': ''}

    if not all([subject.strip, body.strip(), lastname.strip(), firstname.strip(), email.strip()]):
        response = {'error': True, 'msg': gettext("Invalid parameters")}
        return JsonResponse(response, safe=False)

    # ref-etab mail sending
    try:
        send_email(recipient, subject, body, f'{firstname} {lastname} <{email}>')
    except Exception as e:
        response['error'] = True
        response['msg'] += _("%s : error") % recipient

    try:
        template = MailTemplate.objects.get(code='CONTACTUS_NOTIFICATION', active=True)
        notify_user = True
    except MailTemplate.DoesNotExist:
        pass

    # Contacting user mail notification
    if notify_user:
        try:
            vars = {
                "nom": lastname,
                "prenom": firstname,
            }
            message_body = render_text(template_data=template.body, data=vars)

            send_email(email, template.subject, message_body)
        except Exception as e:
            logger.exception(e)
            msg = _("Error while sending mail : %s" % e)

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'SRV-JUR', 'REF-ETAB-MAITRE')
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
            if record:
                uai_code, institution = record.home_institution()
                institution = institution.label if institution else uai_code

        immersion_data = {
            'id': immersion.pk,
            'date': _date(immersion.slot.date, 'l d/m/Y'),
            'time': {
                'start': immersion.slot.start_time.strftime('%Hh%M') if immersion.slot.start_time else '',
                'end': immersion.slot.end_time.strftime('%Hh%M') if immersion.slot.end_time else '',
            },
            'datetime': datetime.datetime.strptime(
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
            if immersion.slot.date
            else None,
            'name': f"{immersion.student.last_name} {immersion.student.first_name}",
            'institution': institution,
            'phone': record.phone if record and record.phone else '',
            'email': immersion.student.email,
            'campus': immersion.slot.campus.label,
            'building': immersion.slot.building.label,
            'room': immersion.slot.room,
        }

        response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
def ajax_set_course_alert(request):
    """
    Add on alert on a course availability
    """
    email = request.POST.get('email', '').lower()
    course_id = request.POST.get('course_id')
    response = {'data': [], 'msg': '', 'error': False}

    # Check parameters:
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        response['error'] = True
        response['msg'] = gettext('Invalid parameter : course not found')
        return JsonResponse(response, safe=False)

    try:
        validate_email(email)
    except:
        response['error'] = True
        response['msg'] = gettext('Invalid email format')
        return JsonResponse(response, safe=False)

    # Check unicity:
    try:
        alert = UserCourseAlert.objects.get(email=email, course=course)

        if not alert.email_sent:
            response['error'] = True
            response['msg'] = gettext('You have already set an alert on this course')
            return JsonResponse(response, safe=False)
        else:
            alert.email_sent = False
            alert.save()
    except UserCourseAlert.DoesNotExist:
        # Set alert:
        UserCourseAlert.objects.create(email=email, course=course)

    response['msg'] = gettext('Alert successfully set')
    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('ETU', 'LYC')
def ajax_get_alerts(request):
    """
    Get alerts list
    """
    response = {'data': [], 'msg': ''}

    alerts = UserCourseAlert.objects.prefetch_related('course__training__training_subdomains__training_domain').filter(
        email=request.user.email
    )

    for alert in alerts:
        subdomains = alert.course.training.training_subdomains.all().order_by('label').distinct()
        domains = TrainingDomain.objects.filter(Subdomains__in=subdomains).distinct().order_by('label')

        alert_data = {
            'id': alert.id,
            'course': alert.course.label,
            'training': alert.course.training.label,
            'subdomains': [subdomain.label for subdomain in subdomains],
            'domains': [domain.label for domain in domains],
            'email_sent': alert.email_sent,
        }

        response['data'].append(alert_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('ETU', 'LYC')
def ajax_cancel_alert(request):
    """
    Remove an alert
    """
    response = {'data': [], 'msg': '', 'error': ''}
    alert_id = request.POST.get('alert_id')

    try:
        alert = UserCourseAlert.objects.get(pk=alert_id, email=request.user.email)
        alert.delete()
        response['msg'] = gettext("Alert successfully cancelled")
    except UserCourseAlert.DoesNotExist:
        response['error'] = gettext("Invalid parameter")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", 'REF-ETAB-MAITRE')
def ajax_get_duplicates(request):
    """
    Get duplicates lists
    """
    response = {'data': [], 'msg': ''}
    id = 0
    for t in HighSchoolStudentRecord.get_duplicate_tuples():
        records = []

        for record_id in t:
            try:
                record = HighSchoolStudentRecord.objects.get(pk=record_id)
                records.append(record)
            except HighSchoolStudentRecord.DoesNotExist:
                continue

        if len(records) > 1:
            dupes_data = {
                "id": id,
                "record_ids": [r.id for r in records],
                'names': [str(r.student) for r in records],
                'birthdates': [_date(r.birth_date) for r in records],
                "highschools": [f"{r.highschool.label}, {r.class_name}" for r in records],
                "emails": [r.student.email for r in records],
                "record_links": [reverse('immersion:modify_hs_record', kwargs={'record_id': r.id}) for r in records],
            }

            id += 1

            response['data'].append(dupes_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-ETAB-MAITRE')
def ajax_keep_entries(request):
    """
    Remove duplicates ids from high school student records
    """
    response = {'data': [], 'msg': '', 'error': ''}
    entries = request.POST.getlist('entries[]', [])

    try:
        l = list(permutations(entries))
    except Exception:
        response['error'] = gettext("Invalid parameter")
        return JsonResponse(response, safe=False)

    for couple in l:
        logger.debug("Duplicates : remove %s from %s", couple[0], couple[1])
        try:
            record = HighSchoolStudentRecord.objects.get(pk=int(couple[0]))
            record.remove_duplicate(id=couple[1])
        except (HighSchoolStudentRecord.DoesNotExist, ValueError):
            response['error'] = gettext("An error occurred while clearing duplicates data")

        try:
            record = HighSchoolStudentRecord.objects.get(pk=int(couple[1]))
            record.remove_duplicate(id=couple[0])
        except (HighSchoolStudentRecord.DoesNotExist, ValueError):
            response['error'] = gettext("An error occurred while clearing duplicates data")

    response['msg'] = gettext("Duplicates data cleared")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-LYC')
def ajax_get_highschool_speakers(request, highschool_id=None):
    """
    get highschool speakers
    """
    response = {'data': [], 'msg': '', 'error': ''}

    if request.user.highschool and highschool_id and request.user.highschool.id == highschool_id:
        for speaker in ImmersionUser.objects.filter(groups__name='INTER', highschool=request.user.highschool):
            has_courses = speaker.courses.exists()
            has_slots = speaker.slots.exists() # useless ?

            response["data"].append({
                'id': speaker.id,
                'last_name': speaker.last_name,
                'first_name': speaker.first_name,
                'email': speaker.email,
                'is_active': _("Yes") if speaker.is_active else _("No"),
                'has_courses': _("Yes") if has_courses else _("No"),
                'can_delete': not has_courses
            })

    return JsonResponse(response, safe=False)


class CampusList(generics.ListAPIView):
    """
    Campus list
    """
    serializer_class = CampusSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', ]

    def get_queryset(self):
        queryset = Campus.objects.filter(active=True).order_by('label')
        user = self.request.user

        if not user.is_superuser and user.is_establishment_manager():
            queryset = queryset.filter(establishment=user.establishment)

        return queryset


class EstablishmentList(generics.ListAPIView):
    """
    Establishments list
    """
    serializer_class = EstablishmentSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        queryset = Establishment.activated.order_by('label')
        user = self.request.user

        if not user.is_superuser and user.is_establishment_manager():
            queryset = queryset.filter(id=user.establishment.id)

        return queryset


class StructureList(generics.ListAPIView):
    """
    Structures list
    """
    serializer_class = StructureSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', ]

    def get_queryset(self):
        queryset = Structure.activated.order_by('code', 'label')
        user = self.request.user

        if not user.is_superuser:
            if user.is_structure_manager():
                return user.structures.order_by('code', 'label')
            if user.is_establishment_manager() and user.establishment:
                return user.establishment.structures.order_by('code', 'label')

        return queryset


class CourseList(generics.ListAPIView):
    """
    Courses list
    """
    serializer_class = CourseSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['training', 'structure', 'highschool']

    def get_queryset(self):
        queryset = Course.objects.filter(published=True).order_by('label')
        user = self.request.user

        if not user.is_superuser:
            if user.is_structure_manager():
                return queryset.filter(structure__in=user.structures.all()).order_by('label')
            if user.is_establishment_manager() and user.establishment:
                return Course.objects.filter(structure__in=user.establishment.structures.all()).order_by('label')

        return queryset


class BuildingList(generics.ListAPIView):
    """
    Buildings list
    """
    serializer_class = BuildingSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['campus', ]

    def get_queryset(self):
        user = self.request.user
        queryset = Building.objects.order_by('label')

        if not user.is_superuser:
            if user.is_structure_manager():
                return queryset.filter(campus__establishment__structures__in=user.structures.all()).distinct()

            if user.is_establishment_manager() and user.establishment:
                return queryset.filter(campus__establishment=user.establishment)

        return queryset


class GetEstablishment(generics.RetrieveAPIView):
    """
    Single establishment
    """
    serializer_class = EstablishmentSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    queryset = Establishment.objects.all()
    lookup_field = "id"


@method_decorator(groups_required('REF-LYC', 'REF-ETAB-MAITRE'), name="dispatch")
class TrainingHighSchoolList(generics.ListAPIView):
    """Training highschool list"""
    serializer_class = TrainingHighSchoolSerializer
    filterset_fields = ("highschool",)

    def get_queryset(self):
        """
        Return user highschool is you are a REF-LYC,
        :return:
        """
        if self.request.user.is_authenticated:
            if self.request.user.is_master_establishment_manager():
                if "pk" in self.kwargs:
                    return Training.objects.filter(highschool_id=self.kwargs.get("pk"))
                else:
                    return Training.objects.filter(highschool__isnull=False)
            else:
                return Training.objects.filter(highschool=self.request.user.highschool)


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingView(generics.DestroyAPIView):
    """Training hs delete class"""
    serializer_class = TrainingHighSchoolSerializer

    def delete(self, request, *args, **kwargs):
        if Course.objects.filter(training_id=kwargs.get("pk")).exists():
            return JsonResponse(data={
                "error": _("Some courses are attached to this training: delete not allowed")
            })

        super().delete(request, *args, **kwargs)
        return JsonResponse(data={
            "msg": _("Training #%s deleted") % kwargs["pk"],
        })

    def get_queryset(self):
        return Training.objects.filter(highschool=self.request.user.highschool)


@is_ajax_request
def ajax_get_immersions_proposal_establishments(request):
    response = {'msg': '', 'data': []}
    try:
        establishments=Establishment.activated.all().values('city', 'label', 'email')
        highschools=HighSchool.immersions_proposal.all().values('city', 'label', 'email')
        results = list(establishments.union(highschools).order_by('city'))
        response['data'].append(results)
    except:
        # Bouhhhh
        pass

    return JsonResponse(response, safe=False)


class VisitList(generics.ListAPIView):
    """
    Visits list
    """
    serializer_class = VisitSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', 'structure', 'highschool']

    def get_queryset(self):
        queryset = Visit.objects.all()
        user = self.request.user

        if not user.is_superuser:
            if user.is_structure_manager():
                queryset = queryset.filter(structure__in=user.structures.all())
            if user.is_establishment_manager() and user.establishment:
                queryset = Visit.objects.filter(
                    Q(establishment=user.establishment)|Q(structure__in=user.establishment.structures.all()))\
                    .distinct()

        return queryset.order_by('establishment', 'structure', 'highschool', 'purpose')

    def filter_queryset(self, queryset):
        filters = {}
        if "structure" in self.request.query_params:
            structure_id = self.request.query_params.get("structure", None) or None
            filters["structure"] = structure_id

        if "establishment" in self.request.query_params:
            establishment_id = self.request.query_params.get("establishment", None) or None
            filters["establishment"] = establishment_id

        if "highschool" in self.request.query_params:
            highschool_id = self.request.query_params.get("highschool", None) or None
            filters["highschool"] = highschool_id

        return queryset.filter(**filters)


@method_decorator(groups_required('REF-STR', 'REF-ETAB', 'REF-ETAB-MAITRE'), name="dispatch")
class VisitDetail(generics.DestroyAPIView):
    """
    Visit detail
    """
    serializer_class = VisitSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    lookup_fields = ['id']
    queryset = Visit.objects.all()

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        user = self.request.user

        if not obj:
            return JsonResponse(data={"msg": _("Nothing to delete")})

        if not user.is_superuser:
            valid_conditions = [
                user.is_master_establishment_manager(),
                user.is_establishment_manager() and obj.establishment == user.establishment,
                user.is_structure_manager() and obj.structure_id and obj.structure in user.get_authorized_structures(),
            ]

            if not any(valid_conditions):
                return JsonResponse(
                    data={"msg": _("Insufficient privileges")},
                    status=status.HTTP_403_FORBIDDEN
                )

        if obj.slots.exists():
            return JsonResponse(
                data={"error": _("Some slots are attached to this visit: it can't be deleted")},
                status=status.HTTP_403_FORBIDDEN
            )

        super().delete(request, *args, **kwargs)

        return JsonResponse(data={"msg": _("Visit successfully deleted")})


class OffOfferEventList(generics.ListAPIView):
    """
    Off offer events list
    """
    serializer_class = OffOfferEventSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', 'structure', 'highschool']

    def get_queryset(self):
        queryset = OffOfferEvent.objects.all()
        user = self.request.user

        if not user.is_superuser:
            if user.is_high_school_manager():
                queryset = queryset.filter(highschool=user.highschool)
            if user.is_structure_manager():
                queryset = queryset.filter(structure__in=user.structures.all())
            if user.is_establishment_manager() and user.establishment:
                queryset = OffOfferEvent.objects.filter(
                    Q(establishment=user.establishment)|Q(structure__in=user.establishment.structures.all()))\
                    .distinct()

        return queryset.order_by('establishment', 'structure', 'highschool', 'label')

    def filter_queryset(self, queryset):
        filters = {}
        if "structure" in self.request.query_params:
            structure_id = self.request.query_params.get("structure", None) or None
            filters["structure"] = structure_id

        if "establishment" in self.request.query_params:
            establishment_id = self.request.query_params.get("establishment", None) or None
            filters["establishment"] = establishment_id

        if "highschool" in self.request.query_params:
            highschool_id = self.request.query_params.get("highschool", None) or None
            filters["highschool"] = highschool_id

        return queryset.filter(**filters)


@method_decorator(groups_required('REF-STR', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-LYC'), name="dispatch")
class OffOfferEventDetail(generics.DestroyAPIView):
    """
    Off offer event detail
    """
    serializer_class = OffOfferEventSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    lookup_fields = ['id']
    queryset = OffOfferEvent.objects.all()

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        user = self.request.user

        if not obj:
            return JsonResponse(data={"msg": _("Nothing to delete")})

        if not user.is_superuser:
            valid_conditions = [
                user.is_master_establishment_manager() and not obj.highschool,
                user.is_high_school_manager() and obj.highschool == user.highschool,
                user.is_establishment_manager() and obj.establishment == user.establishment,
                user.is_structure_manager() and obj.structure_id and obj.structure in user.get_authorized_structures(),
            ]

            if not any(valid_conditions):
                return JsonResponse(
                    data={"msg": _("Insufficient privileges")},
                    status=status.HTTP_403_FORBIDDEN
                )

        if obj.slots.exists():
            return JsonResponse(
                data={"error": _("Some slots are attached to this event: it can't be deleted")},
                status=status.HTTP_403_FORBIDDEN
            )

        super().delete(request, *args, **kwargs)

        return JsonResponse(data={"msg": _("Off offer event successfully deleted")})