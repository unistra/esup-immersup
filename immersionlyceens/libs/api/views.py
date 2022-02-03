"""
API Views
"""
import csv
import datetime
import importlib
import json
import logging
from functools import reduce
from itertools import chain, permutations
from typing import Any, Dict, List, Optional

import django_filters.rest_framework
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.exceptions import FieldError
from django.core.validators import validate_email
from django.db.models import Q, QuerySet
from django.http import HttpResponse, JsonResponse
from django.template.defaultfilters import date as _date
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.module_loading import import_string
from django.utils.translation import gettext, gettext_lazy as _, pgettext
from django.views import View, generic
from rest_framework import generics, status

"""
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
"""

from immersionlyceens.apps.core.models import (
    Building, Calendar, Campus, CancelType, Course, Establishment, HighSchool,
    HighSchoolLevel, Holiday, Immersion, ImmersionUser, MailTemplate,
    MailTemplateVars, OffOfferEvent, PostBachelorLevel, PublicDocument, Slot,
    Structure, StudentLevel, Training, TrainingDomain, UniversityYear,
    UserCourseAlert, Vacation, Visit,
)
from immersionlyceens.apps.core.serializers import (
    BuildingSerializer, CampusSerializer, CourseSerializer,
    EstablishmentSerializer, HighSchoolLevelSerializer,
    OffOfferEventSerializer, StructureSerializer, TrainingHighSchoolSerializer,
    VisitSerializer,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord, VisitorRecord,
)
from immersionlyceens.decorators import (
    groups_required, is_ajax_request, is_post_request,
)
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting, render_text

logger = logging.getLogger(__name__)


@is_ajax_request
@groups_required("REF-ETAB-MAITRE", "REF-ETAB", "REF-STR", "REF-LYC", 'REF-TEC')
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
@groups_required("REF-ETAB", 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_get_available_vars(request, template_id=None):
    response = {'msg': '', 'data': []}

    if template_id:
        template_vars = MailTemplateVars.objects.filter(mail_templates=template_id)
        response["data"] = [{'id': v.id, 'code': v.code, 'description': v.description} for v in template_vars]
    else:
        response["msg"] = gettext("Error : no template id")

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER', 'REF-TEC')
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
            managed_by = f"{course.structure.establishment.code} - {course.structure.code}"
            has_rights = (Structure.objects.filter(pk=course.structure.id) & allowed_structures).exists()
        elif course.highschool:
            managed_by = f"{course.highschool.city} - {course.highschool.label}"

            has_rights = any([
                request.user.is_master_establishment_manager(),
                request.user.is_operator(),
                course.highschool == request.user.highschool
            ])

        course_data = {
            'id': course.id,
            'published': course.published,
            'training_id': course.training.id,
            'training_label': course.training.label,
            'label': course.label,
            'managed_by': managed_by,
            'establishment_id': course.structure.establishment.id if course.structure else None,
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
@groups_required("REF-ETAB", "REF-STR", 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC')
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


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER', 'REF-TEC')
def slots(request):
    """
    Get slots list according to GET parameters
    :return:
    """
    response = {'msg': '', 'data': []}
    can_update_attendances = False
    today = datetime.datetime.today()
    user = request.user
    user_filter = False
    filters = {}

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
    events = request.GET.get('events', False) == "true"
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

    if user.is_speaker():
        user_filter = True
        filters["speakers"] = user

    if not user_filter:
        if visits and not establishment_id and not structure_id:
            if user.is_high_school_manager():
                filters["visit__highschool__id"] = user.highschool.id
            else:
                try:
                    establishment_id = user.establishment.id
                except Exception as e:
                    response['msg'] = gettext("Error : a valid establishment or structure must be selected")
                    return JsonResponse(response, safe=False)

        elif events and not establishment_id and not highschool_id:
            try:
                establishment_id = user.establishment.id
            except Exception as e:
                pass

            try:
                highschool_id = user.highschool.id
            except Exception as e:
                pass

            if not highschool_id and not establishment_id:
                response['msg'] = gettext("Error : a valid establishment or high school must be selected")
                return JsonResponse(response, safe=False)

        elif not events and not visits and not training_id:
            response['msg'] = gettext("Error : a valid training must be selected")
            return JsonResponse(response, safe=False)

    if visits:
        filters["course__isnull"] = True
        filters["event__isnull"] = True

        if establishment_id:
            filters['visit__establishment__id'] = establishment_id

        if structure_id is not None:
            filters['visit__structure__id'] = structure_id

        slots = Slot.objects.prefetch_related(
            'visit__establishment', 'visit__structure', 'visit__highschool', 'speakers', 'immersions') \
            .filter(**filters)

        user_filter_key = "visit__structure__in"
    elif events:
        filters["course__isnull"] = True
        filters["visit__isnull"] = True

        if establishment_id:
            filters['event__establishment__id'] = establishment_id
            if structure_id is not None:
                filters['event__structure__id'] = structure_id
        elif highschool_id:
            filters['event__highschool__id'] = highschool_id

        slots = Slot.objects.prefetch_related(
            'event__establishment', 'event__structure', 'event__highschool', 'speakers', 'immersions') \
            .filter(**filters)

        user_filter_key = "event__structure__in"
    else:
        filters["visit__isnull"] = True
        filters["event__isnull"] = True

        if training_id is not None:
            filters['course__training__id'] = training_id

        slots = Slot.objects.prefetch_related(
            'course__training__structures', 'course__training__highschool', 'speakers', 'immersions')\
            .filter(**filters)

        user_filter_key = "course__training__structures__in"

    if not user.is_superuser and user.is_structure_manager():
        user_filter = {user_filter_key: user.structures.all()}
        slots = slots.filter(**user_filter)

    if not past_slots:
        slots = slots.filter(
            Q(date__isnull=True)
            | Q(date__gte=today.date())
            | Q(date=today.date(), end_time__gte=today.time())
            | Q(face_to_face=True, immersions__attendance_status=0, immersions__cancellation_type__isnull=True)
        ).distinct()

    all_data = []
    allowed_structures = user.get_authorized_structures()
    user_establishment = user.establishment
    user_highschool = user.highschool

    for slot in slots.order_by('date', 'start_time'):
        establishment = slot.get_establishment()
        structure = slot.get_structure()
        highschool = slot.get_highschool()

        allowed_course_slot_update_conditions = [
            user.is_master_establishment_manager() and slot.course,
            user.is_operator() and slot.course,
            user.is_establishment_manager() and slot.course and slot.course.structure.establishment == user_establishment,
            user.is_structure_manager() and slot.course and slot.course.structure in allowed_structures
        ]

        allowed_visit_slot_update_conditions = [
            user.is_master_establishment_manager(),
            user.is_operator(),
            user.is_establishment_manager() and slot.visit and slot.visit.establishment == user_establishment,
            user.is_structure_manager() and slot.visit and slot.visit.structure in allowed_structures
        ]

        allowed_event_slot_update_conditions = [
            user.is_master_establishment_manager() and slot.event,
            user.is_operator() and slot.event,
            user.is_establishment_manager() and slot.event and slot.event.establishment == user_establishment,
            user.is_structure_manager() and slot.event and slot.event.structure in allowed_structures,
            user.is_high_school_manager() and slot.event and highschool and highschool == user_highschool,
        ]

        registrations_update_conditions = [
            user.is_master_establishment_manager(),
            user.is_operator(),
            user.is_establishment_manager() and establishment == user_establishment,
            slot.published and (
                (user.is_structure_manager() and structure in allowed_structures) or
                ((slot.course or slot.event) and user.is_high_school_manager()
                 and highschool and highschool == user_highschool
                )
            ),
        ]

        update_attendances_conditions = [
            registrations_update_conditions,
            user.is_speaker() and user in slot.speakers.all()
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
            'can_update_course_slot': slot.course and any(allowed_course_slot_update_conditions),
            'can_update_visit_slot': slot.visit and any(allowed_visit_slot_update_conditions),
            'can_update_event_slot': slot.event and any(allowed_event_slot_update_conditions),
            'can_update_registrations': any(registrations_update_conditions),
            'can_update_attendances': can_update_attendances and any(update_attendances_conditions),
            'course': {
               'id': slot.course.id,
               'label': slot.course.label
            } if slot.course else None,
            'training_label': training_label,
            'training_label_full': training_label_full,
            'establishment': {
                'code': establishment.code,
                'short_label': establishment.short_label,
                'label': establishment.label
            } if establishment else None,
            'structure': {
                'code': structure.code,
                'label': structure.label,
                'establishment': structure.establishment.short_label,
                'managed_by_me': structure in allowed_structures,
            } if structure else None,
            'highschool': {
                'city': highschool.city,
                'label': highschool.label,
                'managed_by_me': user.is_master_establishment_manager()\
                    or user.is_operator()\
                    or (user_highschool and highschool == user_highschool),
            } if highschool else None,
            'visit': {
                'id': slot.visit.id,
                'purpose': slot.visit.purpose
            } if slot.visit else None,
            'course_type': slot.course_type.label if slot.course_type is not None else '-',
            'course_type_full': slot.course_type.full_label if slot.course_type is not None else '-',
            'event': {
                'id': slot.event.id,
                'type': slot.event.event_type.label if slot.event.event_type else None,
                'label': slot.event.label,
                'description': slot.event.description
            } if slot.event else None,
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
            'restrictions': {
              'establishment_restrictions': slot.establishments_restrictions,
              'levels_restrictions': slot.levels_restrictions,
              'allowed_establishments': [e.short_label for e in slot.allowed_establishments.all()],
              'allowed_highschools': [f"{h.city} - {h.label}" for h in slot.allowed_highschools.all()],
              'allowed_highschool_levels': [level.label for level in slot.allowed_highschool_levels.all()],
              'allowed_post_bachelor_levels': [level.label for level in slot.allowed_post_bachelor_levels.all()],
              'allowed_student_levels': [level.label for level in slot.allowed_student_levels.all()],
            },
            'additional_information': slot.additional_information,
            'attendances_value': 0,
            'attendances_status': '',
            'is_past': False,
        }

        # Update attendances rights depending on slot data and current user
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
def ajax_get_event_speakers(request, event_id=None):
    response = {'msg': '', 'data': []}

    if not event_id:
        response['msg'] = gettext("Error : a valid event must be selected")
    else:
        speakers = OffOfferEvent.objects.get(id=event_id).speakers.all().order_by('last_name')

        for speaker in speakers:
            speakers_data = {
                'id': speaker.id,
                'first_name': speaker.first_name,
                'last_name': speaker.last_name.upper(),
            }
            response['data'].append(speakers_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
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

        details = []
        is_vacation = Vacation.date_is_inside_a_vacation(formated_date.date())
        is_holiday = Holiday.date_is_a_holiday(formated_date.date())
        is_sunday = formated_date.date().weekday() == 6 # sunday

        if is_vacation:
            details.append(pgettext("vacations", "Holidays"))
        if is_holiday:
            details.append(_("Holiday"))
        if is_sunday:
            details.append(_("Sunday"))

        response['data'] = {
            'date': _date,
            'is_between': is_vacation or is_holiday or is_sunday,
            'details': details
        }
    else:
        response['msg'] = gettext('Error: A date is required')

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required('REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC')
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

            response['data'] = [{
                'id': record.id,
                'first_name': record.student.first_name,
                'last_name': record.student.last_name,
                'birth_date': _date(record.birth_date, "j/m/Y"),
                'level': record.level.label if record.level else None,
                'class_name': record.class_name,
            } for record in records.order_by('student__last_name', 'student__first_name')]
        else:
            response['msg'] = gettext("Error: No high school selected")
    else:
        response['msg'] = gettext("Error: No action selected for AJAX request")

    return JsonResponse(response, safe=False)


# REJECT / VALIDATE STUDENT
@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_validate_reject_student(request, validate):
    """
    Validate or reject student
    """
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

    response = {'data': None, 'msg': ''}

    student_record_id = request.POST.get('student_record_id')
    if student_record_id:
        hs = None
        all_highschools_conditions = [
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
        ]

        if any(all_highschools_conditions):
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
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_validate_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=True)


@is_ajax_request
@is_post_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_reject_student(request):
    """Validate student"""
    return ajax_validate_reject_student(request=request, validate=False)


@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_check_course_publication(request, course_id):
    from immersionlyceens.apps.core.models import Course

    response = {'data': None, 'msg': ''}

    c = Course.objects.get(id=course_id)
    response['data'] = {'published': c.published}

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC')
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

    if send_mail and account.groups.filter(name__in=['LYC', 'ETU', 'VIS']):
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

        elif account.is_student() or account.is_visitor():
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
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'REF-STR', 'VIS')
def ajax_cancel_registration(request):
    """
    Cancel a registration to an immersion slot
    """
    immersion_id = request.POST.get('immersion_id')
    reason_id = request.POST.get('reason_id')
    today = datetime.datetime.today()
    user = request.user
    allowed_structures = user.get_authorized_structures()

    #FIXME : test request.user rights on immersion.slot

    if not immersion_id or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            immersion = Immersion.objects.get(pk=immersion_id)
            if immersion.slot.date < today.date() or (immersion.slot.date == today.date()
                                                      and immersion.slot.start_time < today.time()):
                response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                return JsonResponse(response, safe=False)

            slot_establishment = immersion.slot.get_establishment()
            slot_structure = immersion.slot.get_structure()
            slot_highschool = immersion.slot.get_highschool()

            # Check authenticated user rights on this registration
            valid_conditions = [
                user.is_master_establishment_manager(),
                user.is_operator(),
                user == immersion.student,
                user.is_establishment_manager() and slot_establishment == user.establishment,
                user.is_structure_manager() and slot_structure in allowed_structures,
                user.is_high_school_manager() and (immersion.slot.course or immersion.slot.event)
                    and slot_highschool and user.highschool == slot_highschool,
            ]

            if not any(valid_conditions):
                response = {'error': True, 'msg': _("You don't have enough privileges to cancel this registration")}
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
#TODO: check rights
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC', 'VIS')
def ajax_get_immersions(request, user_id=None):
    """
    Returns students immersions
    GET parameters:
    immersion_type in "future", "past", "cancelled" or None (= all)
    slot_type in "course", "visit", "event" or None (= all)
    """
    all_types = ['course', 'visit', 'event'] # Fixme : do something with this in Slot class

    slot_type = request.GET.get('slot_type') or None
    immersion_type = request.GET.get('immersion_type') or None
    user = request.user
    calendar = None
    slot_semester = None
    remainings = {}
    response = {'msg': '', 'data': []}

    if not user_id:
        response['msg'] = gettext("Error : missing user id")
        return JsonResponse(response, safe=False)

    # Valid conditions to view user's immersions : staff and the user himself
    valid_conditions = [
        user.is_master_establishment_manager(),
        user.is_operator(),
        user.is_establishment_manager(),
        user.is_high_school_manager() and user.highschool and user.highschool.postbac_immersion,
        user.id == user_id
    ]

    if not any(valid_conditions):
        response['msg'] = gettext("Error : invalid user id")
        return JsonResponse(response, safe=False)

    try:
        calendar = Calendar.objects.first()
    except Exception:
        pass

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()
    now = datetime.datetime.today().time()

    try:
        student = ImmersionUser.objects.get(pk=user_id)
        remainings['1'], remainings['2'], remaining_annually = student.remaining_registrations_count()
    except ImmersionUser.DoesNotExist:
        response['msg'] = gettext("Error : no such user")
        return JsonResponse(response, safe=False)

    time = f"{datetime.datetime.now().hour}:{datetime.datetime.now().minute}"

    filters = {
        'student_id': user_id,
    }

    prefetch = [
        'slot__campus',
        'slot__building',
        'slot__speakers'
    ]

    if slot_type:
        filters.update({f'slot__{a}__isnull': True for a in filter(lambda a:a != slot_type, all_types)})
        prefetch.append(f'slot__{slot_type}')

        if slot_type == 'course':
            prefetch += ['slot__course__training', 'slot__course_type']
    else:
        prefetch += [
            'slot__course',
            'slot__course__training',
            'slot__course_type',
            'slot__event',
            'slot__visit',
        ]

    if immersion_type == "cancelled":
        filters["cancellation_type__isnull"] = False
    elif immersion_type:
        filters["cancellation_type__isnull"] = True

    immersions = Immersion.objects\
        .prefetch_related(*prefetch)\
        .filter(**filters)

    if immersion_type == "future":
        immersions = immersions.filter(
            Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gte=time)
        )
    elif immersion_type == "past":
        immersions = immersions.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__start_time__lte=time)
        )

    for immersion in immersions:
        slot = immersion.slot
        highschool = slot.get_highschool()
        establishment = slot.get_establishment()
        structure = slot.get_structure()
        campus = slot.campus.label if slot.campus else ""
        building = slot.building.label if slot.building else ""

        if calendar.calendar_mode == 'SEMESTER':
            slot_semester = calendar.which_semester(immersion.slot.date)

        slot_datetime = datetime.datetime.strptime(
            "%s:%s:%s %s:%s"
            % (
                slot.date.year,
                slot.date.month,
                slot.date.day,
                slot.start_time.hour,
                slot.start_time.minute,
            ),
            "%Y:%m:%d %H:%M",
        )
        # Remote course slot not used for now
        if not slot.face_to_face:
            meeting_place = gettext('Remote')

            if slot.url and slot.can_show_url():
                meeting_place += f"<br><a href='{slot.url}'>%s</a>" % gettext("Login link")
        else:
            meeting_place = " <br> ".join(list(filter(lambda x:x, [building, slot.room])))

        immersion_data = {
            'id': immersion.id,
            'type': slot.get_type(),
            'translated_type': gettext(slot.get_type().title()),
            'label': slot.get_label(),
            'establishment': establishment.label if establishment else "",
            'highschool': f'{highschool.label} - {highschool.city}' if highschool else "",
            'structure': structure.label if structure else "",
            'meeting_place': meeting_place,
            'campus': campus,
            'building': building,
            'room': slot.room,
            'establishments': [],
            'course': {
                'label': slot.course.label,
                'training': slot.course.training.label,
                'type': slot.course_type.label,
                'type_full': slot.course_type.full_label
            } if slot.course else {},
            'event': {
                'label': slot.event.label,
                'type': slot.event.event_type.label
            } if slot.event else {},
            'visit': {
                'label': slot.visit.purpose,
                'purpose': slot.visit.purpose,
            } if slot.visit else {},
            'datetime': slot_datetime,
            'date': date_format(slot.date),
            'start_time': slot.start_time.strftime("%-Hh%M"),
            'end_time': slot.end_time.strftime("%-Hh%M"),
            'speakers': [],
            'info': slot.additional_information,
            'attendance': immersion.get_attendance_status_display(),
            'attendance_status': immersion.attendance_status,
            'cancellable': today < slot.date,
            'cancellation_type': '',
            'slot_id': slot.id,
            'free_seats': 0,
            'can_register': False,
        }

        if slot.date < today or (slot.date == today and slot.start_time < now):
            immersion_data['time_type'] = "past"
        elif slot.date > today or slot.start_time > now:
            immersion_data['time_type'] = "future"

        if slot.n_places:
            immersion_data['free_seats'] = slot.n_places - slot.registered_students()

        if immersion.cancellation_type:
            immersion_data['cancellation_type'] = immersion.cancellation_type.label

            if slot_datetime > datetime.datetime.today() and slot.available_seats() > 0:
                if slot_semester and remainings[str(slot_semester)] or not slot_semester and remaining_annually:
                    immersion_data['can_register'] = True

        for speaker in slot.speakers.all().order_by('last_name', 'first_name'):
            immersion_data['speakers'].append(f"{speaker.last_name} {speaker.first_name}")

        if slot.course:
            establishments = slot.course.training.distinct_establishments()

            for est in establishments:
                immersion_data['establishments'].append(f"{est.label}")

            if not establishments:
                immersion_data['establishments'].append(str(slot.course.get_etab_or_high_school()))

        response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required('LYC', 'ETU', 'VIS')
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
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
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
                immersion_data['profile'] = pgettext("person type", "High school student")
                record = immersion.student.get_high_school_student_record()

                if record:
                    immersion_data['school'] = record.highschool.label
                    immersion_data['city'] = record.highschool.city
                    immersion_data['level'] = record.level.label

            elif immersion.student.is_student():
                immersion_data['profile'] = pgettext("person type", "Student")
                record = immersion.student.get_student_record()

                if record:
                    uai_code, institution = record.home_institution()
                    immersion_data['school'] = institution.label if institution else uai_code
                    immersion_data['level'] = record.level.label

            elif immersion.student.is_visitor():
                immersion_data['profile'] = pgettext("person type", "Visitor")

            response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_set_attendance(request):
    """
    Update immersion attendance status
    """
    immersion_id = request.POST.get('immersion_id', None)
    immersion_ids = request.POST.get('immersion_ids', None)
    user = request.user
    allowed_structures = user.get_authorized_structures()

    # Control if we can cancel an immersion by clicking again on its status
    single_immersion = True

    response = {'success': '', 'error': '', 'data': []}

    if immersion_ids:
        immersion_ids = json.loads(immersion_ids)
        single_immersion = False

    try:
        attendance_value = int(request.POST.get('attendance_value'))
    except:
        attendance_value = None

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
            response['error'] += "<br>" if response['error'] else ""
            response['success'] += "<br>" if response['success'] else ""

            slot_establishment = immersion.slot.get_establishment()
            slot_structure = immersion.slot.get_structure()
            slot_highschool = immersion.slot.get_highschool()

            # Check authenticated user rights on this registration
            valid_conditions = [
                user.is_master_establishment_manager(),
                user.is_operator(),
                user.is_establishment_manager() and slot_establishment == user.establishment,
                user.is_structure_manager() and slot_structure in allowed_structures,
                user.is_speaker() and user in immersion.slot.speakers.all(),
                user.is_high_school_manager() and (immersion.slot.course or immersion.slot.event)
                and slot_highschool and user.highschool == slot_highschool,
            ]

            if any(valid_conditions):
                # current status cancellation ? (= set 0)
                if single_immersion and immersion.attendance_status == attendance_value:
                    immersion.attendance_status = 0
                else:
                    immersion.attendance_status = attendance_value

                immersion.save()
                response['success'] += f"{immersion.student} : {gettext('attendance status updated')}"
            else:
                response['error'] += "%s : %s" % (
                    immersion.student, gettext("you don't have enough privileges to set the attendance status")
                )


    return JsonResponse(response, safe=False)


@is_ajax_request
@login_required
@is_post_request
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'VIS')
def ajax_slot_registration(request):
    """
    Add a registration to an immersion slot
    """
    slot_id = request.POST.get('slot_id', None)
    student_id = request.POST.get('student_id', None)
    user = request.user
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
    can_force_reg = any([user.is_establishment_manager(), user.is_master_establishment_manager(), user.is_operator()])
    today = datetime.datetime.today().date()
    today_time = datetime.datetime.today().time()
    visit_or_off_offer = False

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
        student = user

    if slot_id:
        try:
            slot = Slot.objects.get(pk=slot_id)
            visit_or_off_offer= True if (slot.visit or slot.event) else False
        except Slot.DoesNotExist:
            pass

    if not slot or not student:
        response = {'error': True, 'msg': _("Invalid parameters")}
        return JsonResponse(response, safe=False)

    # Valid user conditions to register a student
    allowed_structures = user.get_authorized_structures()
    user_establishment = user.establishment
    user_highschool = user.highschool

    establishment = slot.get_establishment()
    slot_structure = slot.get_structure()
    slot_highschool = slot.get_highschool()

    # Fixme : add slot restrictions here
    unpublished_slot_update_conditions = [
        user.is_master_establishment_manager(),
        user.is_operator(),
        user.is_establishment_manager() and establishment == user_establishment
    ]

    published_slot_update_conditions = [
        any(unpublished_slot_update_conditions),
        user.is_structure_manager() and slot_structure in allowed_structures,
        slot.course and user.is_high_school_manager() and slot_highschool and slot_highschool == user_highschool,
        user.is_high_school_student(),
        user.is_student(),
        user.is_visitor(),
        user.is_high_school_manager() and (slot.course or slot.event)
            and slot_highschool and user.highschool == slot_highschool,
    ]

    # Check registration rights depending on the (not student) authenticated user

    if not slot.published and not any(unpublished_slot_update_conditions):
        response = {'error': True, 'msg': _("Registering an unpublished slot is forbidden")}
        return JsonResponse(response, safe=False)

    if slot.published and not any(published_slot_update_conditions):
        response = {'error': True, 'msg': _("Sorry, you can't add any registration to this slot")}
        return JsonResponse(response, safe=False)

    # Only valid Highschool students
    if student.is_high_school_student():
        if not student.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to Highschool student account state")}
            return JsonResponse(response, safe=False)

        record = student.get_high_school_student_record()
        if not record or not record.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to Highschool student record state")}
            return JsonResponse(response, safe=False)

    # Only valid Visitors records
    if student.is_visitor():
        if not student.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to visitor account state")}
            return JsonResponse(response, safe=False)

        record = student.get_visitor_record()
        if not record or not record.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to visitor record state")}
            return JsonResponse(response, safe=False)

    can_register_slot, reasons = student.can_register_slot(slot)

    if not can_register_slot:
        if can_force_reg and not force == 'true':
            return JsonResponse({'error': True, 'msg': 'force_update', 'reason': 'restrictions'}, safe=False)
        elif can_force_reg and force == 'true':
            can_register = True
        else:
            response = {'error': True, 'msg': _("Cannot register slot due to slot's restrictions")}
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
                if remaining_regs_count['annually'] > 0 or visit_or_off_offer:
                    can_register = True
                # alert user he can force registering
                elif can_force_reg and not force == 'true':
                    return JsonResponse({'error': True, 'msg': 'force_update', 'reason': 'registrations'}, safe=False)
                # force registering
                elif force == 'true':
                    can_register = True
                    if slot.is_course():
                        student.set_increment_registrations_(type='annual')
                # student request & no more remaining registration count
                elif (user.is_high_school_student() or user.is_student() or user.is_visitor()) and remaining_regs_count['annually'] <= 0:
                    response = {
                        'error': True,
                        'msg': _(
                            "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                        ),
                    }
                    return JsonResponse(response, safe=False)
                # ref str request & no more remaining registration count for student
                elif user.is_structure_manager() and remaining_regs_count['annually'] <= 0:
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
                    if remaining_regs_count['semester1'] > 0 or visit_or_off_offer:
                        can_register = True
                    # alert user he can force registering (js boolean)
                    elif can_force_reg and not force == 'true':
                        return JsonResponse({'error': True, 'msg': 'force_update', 'reason': 'registrations'}, safe=False)
                    # force registering (js boolean)
                    elif force == 'true':
                        can_register = True
                        if slot.is_course():
                            student.set_increment_registrations_(type='semester1')
                    # student request & no more remaining registration count
                    elif (user.is_high_school_student() or user.is_student() or user.is_visitor()) and remaining_regs_count['semester1'] <= 0:
                        response = {
                            'error': True,
                            'msg': _(
                                "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                            ),
                        }
                        return JsonResponse(response, safe=False)
                    # ref str request & no more remaining registration count for student
                    elif user.is_structure_manager() and remaining_regs_count['semester1'] <= 0:
                        response = {
                            'error': True,
                            'msg': _("This student has no more remaining slots to register to"),
                        }
                        return JsonResponse(response, safe=False)

            # Semester 2
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                if calendar.semester2_registration_start_date <= today <= calendar.semester2_end_date:
                    # remaining regs ok
                    if remaining_regs_count['semester2'] > 0 or visit_or_off_offer:
                        can_register = True
                    # alert user he can force registering (js boolean)
                    elif can_force_reg and not force == 'true':
                        return JsonResponse({'error': True, 'msg': 'force_update', 'reason': 'registrations'}, safe=False)
                    # force registering (js boolean)
                    elif force == 'true':
                        can_register = True
                        if slot.is_course():
                            student.set_increment_registrations_(type='semester2')
                    # student request & no more remaining registration count
                    elif (user.is_high_school_student() or user.is_student() or user.is_visitor()) and remaining_regs_count['semester2'] <= 0:
                        response = {
                            'error': True,
                            'msg': _(
                                "You have no more remaining registration available, you should cancel an immersion or contact immersion service"
                            ),
                        }
                        return JsonResponse(response, safe=False)
                    # ref str request & no more remaining registration count for student
                    elif user.is_structure_manager() and remaining_regs_count['semester2'] <= 0:
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

            error = False
            ret = student.send_message(request, 'IMMERSION_CONFIRM', slot=slot)
            if not ret:
                msg = _("Registration successfully added, confirmation email sent")
            else:
                msg = _("Registration successfully added, confirmation email NOT sent : %s") % ret
                error = True

            response = {'error': error, 'msg': msg}

            # TODO: use django messages for errors as well ?
            # this is a js boolean !!!!
            if feedback == True:
                if error:
                    messages.warning(request, msg)
                else:
                    messages.success(request, msg)

            request.session["last_registration_slot_id"] = slot.id
        else:
            response = {'error': True, 'msg': _("Registration is not currently allowed")}

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_get_available_students(request, slot_id):
    """
    Get students list for manual slot registration
    Students must have a valid record and not already registered to the slot
    """
    response = {'data': [], 'msg': ''}
    user = request.user
    students = ImmersionUser.objects\
        .filter(groups__name__in=['LYC', 'ETU', 'VIS'], validation_string__isnull=True)\
        .exclude(immersions__slot__id=slot_id)

    try:
        slot = Slot.objects.get(pk=slot_id)
    except Slot.DoesNotExist:
        response['msg'] = _("Error : slot not found")
        return JsonResponse(response, safe=False)

    # Visit slot : keep only high school students matching the slot's high school
    if slot.is_visit() and slot.visit.highschool:
        students = students.filter(high_school_student_record__highschool=slot.visit.highschool)

    # Restrictions :
    # Some users will only see a warning about restrictions not met (ref-etab, ref-etab-maitre, ref-tec)
    # Others won't even see the filtered participants in the list (ref-lyc, ref-str)
    # if user.is_master_establishment_manager() or user.is_establishment_manager() or user.is_operator():

    if user.is_high_school_manager() or user.is_structure_manager():
        if slot.establishments_restrictions:
            establishment_filter = {}

            if slot.allowed_establishments.exists():
                establishment_filter['establishment__in'] = slot.allowed_establishments.all()

            if slot.allowed_highschools.exists():
                establishment_filter['high_school_student_record__highschool__in'] = slot.allowed_highschools.all()

            if establishment_filter:
                students = students.filter(reduce(lambda x, y: x | y, [
                    Q(**{'%s' % f: value}) for f, value in establishment_filter.items()])
                )

        if slot.levels_restrictions:
            levels_restrictions = {}

            if slot.allowed_highschool_levels.exists():
                levels_restrictions['high_school_student_record__level__in'] = slot.allowed_highschool_levels.all()

            if slot.allowed_post_bachelor_levels.exists():
                levels_restrictions['high_school_student_record__post_bachelor_level__in'] = \
                    slot.allowed_post_bachelor_levels.all()

            if slot.allowed_student_levels.exists():
                levels_restrictions['student_record__level__in'] = slot.allowed_student_levels.all()

            if levels_restrictions:
                students = students.filter(reduce(lambda x, y: x | y, [
                    Q(**{'%s' % f: value}) for f, value in levels_restrictions.items()])
                )

    for student in students:
        record = None

        if student.is_high_school_student():
            record = student.get_high_school_student_record()
        elif student.is_student():
            record = student.get_student_record()
        elif student.is_visitor():
            record = student.get_visitor_record()

        if record and record.is_valid():
            can_register, reasons = student.can_register_slot(slot)

            student_data = {
                'id': student.pk,
                'lastname': student.last_name,
                'firstname': student.first_name,
                'school': '',
                'class': '',
                'level': '',
                'city': '',
                'can_register': can_register,
                'reasons': reasons
            }

            if student.is_high_school_student():
                student_data['profile'] = pgettext("person type", "High school student")
                student_data['school'] = record.highschool.label
                student_data['city'] = record.highschool.city
                student_data['class'] = record.class_name

                if record.level:
                    student_data['level'] = record.level.label

                    if record.level.is_post_bachelor:
                        student_data['level'] += f" {record.level.post_bachelor_level.label}"

            elif student.is_student():
                uai_code, institution = record.home_institution()
                student_data['profile'] = pgettext("person type", "Student")
                student_data['school'] = institution.label if institution else uai_code
                student_data['level'] = record.level.label if record.level else ""

            elif student.is_visitor():
                student_data['profile'] = pgettext("person type", "Visitor")


            response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_get_highschool_students(request, highschool_id=None):
    """
    Retrieve students from a highschool or all students if user is ref-etab manager
    and no highschool id is specified
    """
    no_record_filter: bool = False
    response: Dict[str, Any] = {'data': [], 'msg': ''}

    admin_groups: List[bool] = [
        request.user.is_establishment_manager(),
        request.user.is_master_establishment_manager(),
        request.user.is_operator(),
        request.user.is_high_school_manager() and request.user.highschool and request.user.highschool.postbac_immersion
    ]

    if any(admin_groups):
        no_record_filter = resolve(request.path_info).url_name == 'get_students_without_record'

    if not highschool_id:
        try:
            highschool_id = request.user.highschool.id
        except Exception:
            if not any(admin_groups):
                response: Dict[str, Any] = {'data': [], 'msg': _('Invalid parameters')}
                return JsonResponse(response, safe=False)

    if highschool_id:
        students = ImmersionUser.objects.prefetch_related('high_school_student_record', 'immersions').filter(
            validation_string__isnull=True, high_school_student_record__highschool__id=highschool_id
        )
    else:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record', 'student_record', 'visitor_record', 'immersions'
        ).filter(validation_string__isnull=True, groups__name__in=['ETU', 'LYC', 'VIS'])

    if no_record_filter:
        students = students.filter(
            high_school_student_record__isnull=True,
            student_record__isnull=True,
            visitor_record__isnull=True
        )
    else:
        students = students.filter(Q(high_school_student_record__isnull=False) | Q(student_record__isnull=False) | Q(visitor_record__isnull=False))

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
            elif student.is_student():
                record = student.get_student_record()
                if record:
                    link = reverse('immersion:modify_student_record', kwargs={'record_id': record.id})
                student_type = pgettext("person type", "Student")
            elif student.is_visitor():
                record = student.get_visitor_record()
                if record:
                    link = reverse('immersion:visitor_record_by_id', kwargs={'record_id': record.id})
                student_type = pgettext("person type", "Visitor")

        except Exception:
            pass

        student_data = {
            'id': student.pk,
            'name': f"{student.last_name} {student.first_name}",
            'birthdate': date_format(record.birth_date) if record else '-',
            'institution': '',
            'level': record.level.label if record and "level" in dir(record) and record.level else '-',
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

                if record.level.is_post_bachelor:
                    student_data['bachelor'] = record.get_origin_bachelor_type_display()
                    student_data['post_bachelor_level'] = record.post_bachelor_level.label
                else:
                    student_data['bachelor'] = record.get_bachelor_type_display()

            elif student.is_student():
                uai_code, institution = record.home_institution()
                student_data['bachelor'] = record.get_origin_bachelor_type_display()
                student_data['institution'] = institution.label if institution else uai_code
                student_data['post_bachelor_level'] = record.current_diploma

        response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@method_decorator(groups_required('REF-ETAB', 'REF-STR', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
class AjaxGetRegisteredUsers(View):
    def common_data(self, user: ImmersionUser) -> Dict[str, Any]:
        return {
            'id': user.pk,
            'name': f"{user.last_name} {user.first_name}",
            'registered': user.immersions.exists(),
            'student_type': _('Unknown'),
        }

    def fill_void(self, data: Dict[str, Any]) -> Dict[str, Any]:
        fields_name = [
            'institution', 'level', 'bachelor', 'post_bachelor_level',
            'class', 'registered', 'record_link', 'student_type',
        ]
        for name in fields_name:
            if name not in data:
                data.update({name: "-"})
        return data

    def get_data(self, user: ImmersionUser):
        data = self.common_data(user)
        if user.is_high_school_student():
            data.update(self.hs_data(user))
        elif user.is_student():
            data.update(self.student_data(user))
        else:
            data.update(self.visitor_data(user))
        return self.fill_void(data)

    def hs_data(self, user: ImmersionUser) -> Dict[str, Any]:
        data = {
            "student_type": pgettext("person type", "Student"),
        }
        record = user.get_high_school_student_record()
        if record:
            data["record_link"] = reverse('immersion:modify_hs_record', kwargs={'record_id': record.id})
            data["level"] = record.level.label if record and record.level else "-"
            data["class"] = record.class_name
            data["institution"] = record.highschool.label
            data["birthdate"] = date_format(record.birth_date) if record else "-"

            if record.level.is_post_bachelor:
                data['bachelor'] = record.get_origin_bachelor_type_display()
                data['post_bachelor_level'] = record.post_bachelor_level.label
            else:
                data['bachelor'] = record.get_bachelor_type_display()
        return data

    def student_data(self, user: ImmersionUser) -> Dict[str, Any]:
        data = {
            "student_type": pgettext("person type", "High school student"),
        }
        record = user.get_student_record()
        if record:
            uai_code, institution = record.home_institution()
            data["level"] = record.level.label if record and record.level else "-",
            data["record_link"] = reverse('immersion:modify_student_record', kwargs={'record_id': record.id})
            data["bachelor"] = record.get_origin_bachelor_type_display()
            data["institution"] = institution.label if institution else uai_code
            data["post_bachelor_level"] = record.current_diploma
            data["birthdate"] = date_format(record.birth_date) if record else "-"
        return data

    def visitor_data(self, user: ImmersionUser) -> Dict[str, Any]:
        data = {
            "student_type": pgettext("person type", "Visitor"),
        }
        record = user.get_visitor_record()
        if record:
            data["record_link"] = reverse('immersion:visitor_record_by_id', kwargs={'record_id': record.id})
            data["birthdate"] = date_format(record.birth_date) if record else "-"

        return data

    def get(self, request):
        no_record_filter: bool = False
        highschool_id = self.kwargs.get("highschool_id")
        response: Dict[str, Any] = {'data': [], 'msg': ''}

        admin_groups: List[bool] = [
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ]

        if any(admin_groups):
            no_record_filter = resolve(self.request.path_info).url_name == 'get_students_without_record'

        if not highschool_id:
            try:
                highschool_id = self.request.user.highschool.id
            except Exception:
                if not any(admin_groups):
                    response: Dict[str, Any] = {'data': [], 'msg': _('Invalid parameters')}
                    return JsonResponse(response, safe=False)

        if highschool_id:
            students = ImmersionUser.objects.prefetch_related('high_school_student_record', 'immersions').filter(
                validation_string__isnull=True, high_school_student_record__highschool__id=highschool_id
            )
        else:
            students = ImmersionUser.objects.prefetch_related(
                'high_school_student_record', 'student_record', 'visitor_record', 'immersions'
            ).filter(validation_string__isnull=True, groups__name__in=['ETU', 'LYC', 'VIS'])

        if no_record_filter:
            students = students.filter(
                high_school_student_record__isnull=True,
                student_record__isnull=True,
                visitor_record__isnull=True
            )
        else:
            students = students.filter(Q(high_school_student_record__isnull=False) | Q(student_record__isnull=False) | Q(
                visitor_record__isnull=False))

        # for student in students:
        #     my_data = self.get_data(student)
        #     response['data'].append(my_data.copy())

            response["data"] = [self.get_data(user).copy() for user in students]
        return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
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
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_batch_cancel_registration(request):
    """
    Cancel registrations to immersions slots
    """
    immersion_ids = request.POST.get('immersion_ids')
    reason_id = request.POST.get('reason_id')

    err_msg = None
    warning_msg = ""
    err = False
    today = datetime.datetime.today()
    user = request.user
    allowed_structures = user.get_authorized_structures()

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

                slot_establishment = immersion.slot.get_establishment()
                slot_structure = immersion.slot.get_structure()
                slot_highschool = immersion.slot.get_highschool()

                # Check authenticated user rights on this registration
                valid_conditions = [
                    user.is_master_establishment_manager(),
                    user.is_operator(),
                    user.is_establishment_manager() and slot_establishment == user.establishment,
                    user.is_structure_manager() and slot_structure in allowed_structures,
                    user.is_high_school_manager() and (immersion.slot.course or immersion.slot.event)
                        and slot_highschool and user.highschool == slot_highschool,
                ]

                if not any(valid_conditions):
                    response = {'error': True, 'msg': _("You don't have enough privileges to cancel these registrations")}
                    return JsonResponse(response, safe=False)

                cancellation_reason = CancelType.objects.get(pk=reason_id)
                immersion.cancellation_type = cancellation_reason
                immersion.save()
                ret = immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)
                if ret:
                    warning_msg = _("Warning : some confirmation emails have not been sent : %s") % ret

            except Immersion.DoesNotExist:
                # should not happen !
                err_msg += _("Immersion not found")
            except CancelType.DoesNotExist:
                # should not happen as well !
                response = {'error': True, 'msg': _("Invalid cancellation reason #id")}
                err = True

        if not err:
            msg = _("Immersion(s) cancelled")

            if warning_msg:
                err = True
                msg += f"<br>{warning_msg}"

            response = {'error': err, 'msg': msg, 'err_msg': err_msg}

    return JsonResponse(response, safe=False)


@groups_required('REF-STR')
def get_csv_structures(request, structure_id):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    structure = Structure.objects.get(id=structure_id).label.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{structure}_{today}.csv"'
    slots = Slot.objects.filter(course__structure_id=structure_id, published=True).order_by('date', 'start_time')

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
    hs_records = HighSchoolStudentRecord.objects.filter(highschool__id=high_school_id)\
        .order_by('student__last_name', 'student__first_name')
    for hs in hs_records:
        immersions = Immersion.objects.filter(student=hs.student, cancellation_type__isnull=True)
        if immersions.count() > 0:
            for imm in immersions:
                content.append(
                    [
                        hs.student.last_name,
                        hs.student.first_name,
                        _date(hs.birth_date, 'd/m/Y'),
                        hs.level.label if hs.level else '',
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
                    hs.level.label if hs.level else '',
                    hs.class_name,
                    HighSchoolStudentRecord.BACHELOR_TYPES[hs.bachelor_type - 1][1] if hs.bachelor_type else '',
                ]
            )

    writer = csv.writer(response)
    writer.writerow(header)
    for row in content:
        writer.writerow(row)

    return response


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
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
                        level = record.level.label if record.level else ''
                    except StudentRecord.DoesNotExist:
                        pass
                elif imm.student.is_high_school_student():
                    try:
                        record = HighSchoolStudentRecord.objects.get(student=imm.student)
                        institution = record.highschool.label
                        level = record.level.label if record.level else ''
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
        response['msg'] += gettext("%s : error") % recipient

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
            response['msg'] += gettext("Couldn't send email : %s" % e)

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'SRV-JUR', 'REF-ETAB-MAITRE', 'REF-TEC')
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
@groups_required('ETU', 'LYC', 'VIS')
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
@groups_required("REF-ETAB-MAITRE", 'REF-TEC')
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
@groups_required('REF-ETAB-MAITRE', 'REF-TEC')
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
    filterset_fields = ['training', 'structure', 'highschool', 'published']

    def get_queryset(self):
        queryset = Course.objects.all().order_by('label')
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


@method_decorator(groups_required('REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
class TrainingHighSchoolList(generics.ListAPIView):
    """Training highschool list"""
    serializer_class = TrainingHighSchoolSerializer
    filterset_fields = ("highschool",)

    def get_queryset(self):
        """
        Return user highschool is you are a REF-LYC,
        :return:
        """
        user = self.request.user

        if user.is_authenticated:
            if user.is_master_establishment_manager() or user.is_operator():
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
            if user.is_speaker():
                queryset = queryset.filter(speakers=user)
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


@method_decorator(groups_required('REF-STR', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
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
                user.is_operator(),
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
            if user.is_speaker():
                queryset = queryset.filter(speakers=user)
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
        structure_id = None
        establishment_id = None
        highschool_id = None

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


@method_decorator(groups_required('REF-STR', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC'), name="dispatch")
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
                user.is_master_establishment_manager(),
                user.is_operator(),
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


class HighSchoolLevelList(generics.ListAPIView):
    """
    High school levels list
    """
    serializer_class = HighSchoolLevelSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        queryset = HighSchoolLevel.objects.filter(active=True).order_by('order')
        return queryset


class HighSchoolLevelDetail(generics.RetrieveAPIView):
    """
    High school level detail
    """
    serializer_class = HighSchoolLevelSerializer
    queryset = HighSchoolLevel.objects.all()


class VisitorRecordValidation(View):
    def get(self, request, *args, **kwargs):
        data: Dict[str, Any] = {"msg": "", "data": None}

        operation: str = kwargs['operator']
        visitor_records: Optional[QuerySet] = None

        if operation == "to_validate":
            visitor_records = VisitorRecord.objects.filter(validation=1)
        elif operation == "validated":
            visitor_records = VisitorRecord.objects.filter(validation=2)
        elif operation == "rejected":
            visitor_records = VisitorRecord.objects.filter(validation=3)

        if visitor_records is not None:
            data["data"] = []
            for record in visitor_records:
                data["data"].append({
                    "id": record.id,
                    "first_name": record.visitor.first_name,
                    "last_name": record.visitor.last_name,
                    "birth_date": record.birth_date,
                })
        else:
            data["msg"] = _("No operator given or wrong operator (to_validate, validated, rejected)")

        return JsonResponse(data)


@method_decorator(groups_required("REF-ETAB-MAITRE", "REF-ETAB", "REF-TEC"), name="dispatch")
class VisitorRecordRejectValidate(View):
    def post(self, request, *args, **kwargs):
        data: Dict[str, Any] = {"msg": "", "data": None}

        # cant be none. No routes allowed for that
        record_id: str = self.kwargs["record_id"]
        operation: str = self.kwargs["operation"]
        validation_value: int = 1
        validation_email_template: str = ""

        if operation == "validate":
            validation_value = 2
            validation_email_template = "CPT_MIN_VALIDE_VISITEUR"
        elif operation == "reject":
            validation_value = 3
            validation_email_template = "CPT_MIN_REJET_VISITEUR"
        else:
            data["msg"] = "Error - Bad operation selected. Allowed: validate, reject"
            return JsonResponse(data)

        try:
            record: VisitorRecord = VisitorRecord.objects.get(id=record_id)
        except VisitorRecord.DoesNotExist:
            data["msg"] = f"Error - No record with id: {record_id}."
            return JsonResponse(data)

        record.validation = validation_value
        record.save()
        record.visitor.send_message(self.request, validation_email_template)
        data["data"] = {"record_id": record.id}
        return JsonResponse(data)