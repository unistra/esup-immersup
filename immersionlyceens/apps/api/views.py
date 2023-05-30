"""
API Views
"""
import csv
import datetime
import importlib
import json
import logging
import time
from functools import reduce
from itertools import chain, permutations
from typing import Any, Dict, List, Optional, Tuple, Union

import django_filters.rest_framework
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import StringAgg
from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.core.validators import validate_email
from django.db.models import (
    Case, CharField, Count, DateField, Exists, ExpressionWrapper, F, Func,
    OuterRef, Q, QuerySet, Subquery, Value, When,
)
from django.db.models.functions import Coalesce, Concat, Greatest
from django.http import Http404, HttpResponse, JsonResponse
from django.template import TemplateSyntaxError
from django.template.defaultfilters import date as _date
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.translation import gettext, gettext_lazy as _, pgettext
from django.views import View
from faker import Faker
from rest_framework import generics, serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from immersionlyceens.apps.core.models import (
    Building, Campus, CancelType, Course, Establishment, GeneralSettings,
    HigherEducationInstitution, HighSchool, HighSchoolLevel, Holiday,
    Immersion, ImmersionUser, ImmersionUserGroup, MailTemplate,
    MailTemplateVars, OffOfferEvent, Period, PublicDocument,
    RefStructuresNotificationsSettings, Slot, Structure, Training,
    TrainingDomain, TrainingSubdomain, UniversityYear, UserCourseAlert,
    Vacation, Visit,
)
from immersionlyceens.apps.core.serializers import (
    BuildingSerializer, CampusSerializer, CourseSerializer,
    EstablishmentSerializer, HighSchoolLevelSerializer, HighSchoolSerializer,
    OffOfferEventSerializer, SlotSerializer, SpeakerSerializer,
    StructureSerializer, TrainingDomainSerializer, TrainingSerializer,
    TrainingSubdomainSerializer, UserCourseAlertSerializer, VisitSerializer,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument, StudentRecord,
    VisitorRecord, VisitorRecordDocument,
)
from immersionlyceens.decorators import (
    groups_required, is_ajax_request, is_post_request, timer,
)
from immersionlyceens.libs.api.accounts import AccountAPI
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting, render_text

from .permissions import (
    CustomDjangoModelPermissions, HighSchoolReadOnlyPermissions,
    IsEstablishmentManagerPermissions, IsHighSchoolStudentPermissions,
    IsMasterEstablishmentManagerPermissions, IsRefLycPermissions,
    IsSpeakerPermissions, IsStructureConsultantPermissions,
    IsStructureManagerPermissions, IsStudentPermissions, IsTecPermissions,
    IsVisitorPermissions, SpeakersReadOnlyPermissions,
)

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

                if users is not False:
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
                Q_filter = Q(establishment=establishment) | Q(structures=structure_id)
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


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER', 'REF-TEC', 'CONS-STR')
def slots(request):
    """
    Get slots list according to GET parameters
    :return:
    """

    """
    @TODO : rewrite this with a ListCreateAPIView and a nice serializer
    """

    response = {'msg': '', 'data': []}
    can_update_attendances = False
    today = datetime.datetime.today()
    user = request.user
    user_filter = False
    user_slots = request.GET.get('user_slots', False) == 'true'
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
    courses = not (visits or events) # unused, still useful somewhere ?
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

    force_user_filter = [
        user_slots,
        user.is_speaker() and not any([
            user.is_master_establishment_manager(),
            user.is_establishment_manager(),
            user.is_high_school_manager() and visits,
            user.is_structure_manager(),
            user.is_structure_consultant(),
            user.is_operator()
        ])
    ]

    if any(force_user_filter):
        user_filter = True
        filters["speakers__in"] = user.linked_users()

    if not user_filter:
        if visits and not establishment_id and not structure_id:
            if user.is_high_school_manager() and user.highschool:
                filters["visit__highschool__id"] = user.highschool.id
            else:
                try:
                    establishment_id = user.establishment.id
                except:
                    response['msg'] = gettext("Error : a valid establishment or structure must be selected")
                    return JsonResponse(response, safe=False)

        elif events and not establishment_id and not highschool_id:
            try:
                establishment_id = user.establishment.id
            except:
                pass

            try:
                highschool_id = user.highschool.id
            except:
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
            'course__training__structures', 'course__training__highschool', 'speakers', 'immersions') \
            .filter(**filters)

        user_filter_key = "course__training__structures__in"

    if not user.is_superuser and (user.is_structure_manager() or user.is_structure_consultant()):
        user_filter = {
            user_filter_key: user.structures.all()
        }
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
                    (user.is_structure_consultant() and structure in allowed_structures) or
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

        if slot.course and slot.course.training and slot.course_type:
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
                'managed_by_me': user.is_master_establishment_manager()
                or user.is_operator()
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
                'bachelors_restrictions': slot.bachelors_restrictions,
                'allowed_bachelor_types': [btype.label for btype in slot.allowed_bachelor_types.all()],
                'allowed_bachelor_mentions': [mention.label for mention in slot.allowed_bachelor_mentions.all()],
                'allowed_bachelor_teachings': [teaching.label for teaching in slot.allowed_bachelor_teachings.all()],
            },
            'additional_information': slot.additional_information,
            'attendances_value': 0,
            'attendances_status': '',
            'is_past': False,
        }

        # Update attendances rights depending on slot data and current user
        if data['datetime'] and data['datetime'] <= today:
            data['is_past'] = True

            if not can_update_attendances or ((events or visits) and not slot.face_to_face):
                # University year end date < now
                data['attendances_value'] = 2  # view only
                if not can_update_attendances:
                    data['attendances_status'] = gettext("University year is over")

            elif not slot.immersions.filter(cancellation_type__isnull=True).exists():
                # Nothing to do
                data['attendances_value'] = -1  # nothing to do

            elif slot.immersions.filter(attendance_status=0, cancellation_type__isnull=True).exists():
                data['attendances_value'] = 1  # to enter
                data['attendances_status'] = gettext("To enter")

            else:
                data['attendances_value'] = 1  # enter or update

        else:
            data['attendances_status'] = gettext("Future slot")

        for speaker in slot.speakers.all().order_by('last_name', 'first_name'):
            data['speakers'].update([(f"{speaker.last_name} {speaker.first_name}", speaker.email,)], )

        all_data.append(data.copy())

    response['data'] = all_data

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
def validate_slot_date(request):
    """
    Check if a date:
      - is in a vacation period
      - belongs to a valid immersions period
    :param request: the request.
    :return: a dict with data about the date
    """
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
        is_sunday = formated_date.date().weekday() == 6  # sunday

        if is_vacation:
            details.append(pgettext("vacations", "Holidays"))
        if is_holiday:
            details.append(_("Holiday"))
        if is_sunday:
            details.append(_("Sunday"))

        # Period
        try:
            period = Period.from_date(formated_date)
            if not period:
                details.append(_("Outside valid period"))
        except Period.MultipleObjectsReturned:
            response['msg'] = gettext('Configuration error, please check your immersions periods dates')
            return JsonResponse(response, safe=False)


        response['data'] = {
            'date': _date,
            'is_between': is_vacation or is_holiday or is_sunday,
            'details': details,
            'valid_period': period is not None,
        }
    else:
        response['msg'] = gettext('Error: A date is required')

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required('REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_get_student_records(request):
    """
    Get high school student lists depending on their record status
    """
    today = timezone.localdate()

    # high_school_validation
    response = {'data': [], 'msg': ''}

    # @@@
    action = request.POST.get('action', '').upper()
    hs_id = request.POST.get('high_school_id')
    with_convention = request.POST.get('with_convention')

    # TODO : get these values from HighSchoolStudentRecord class
    actions = {
        'TO_VALIDATE': 1,
        'VALIDATED': 2,
        'REJECTED': 3,
        'TO_REVALIDATE': 4,
    }

    if not action in actions.keys():
        response['msg'] = gettext("Error: No action selected for AJAX request")
        return JsonResponse(response, safe=False)

    filter = {
        "validation": actions[action]
    }

    # Highschool : accept an int or 'all'
    try:
        hs_id = int(hs_id)
        filter['highschool_id'] = hs_id
    except (ValueError, TypeError):
        if hs_id != 'all':
            response['msg'] = gettext("Error: No high school selected")
            return JsonResponse(response, safe=False)

    # Conventions
    if with_convention in [0, 1, "0", "1"]:
        filter['highschool__with_convention'] = with_convention in (1, "1")

    if not hs_id:
        response['msg'] = gettext("Error: No high school selected")
        return JsonResponse(response, safe=False)

    # Store filters in session
    request.session["highschool_filter"] = hs_id
    request.session["convention_filter"] = with_convention

    attestations = HighSchoolStudentRecordDocument.objects\
        .filter(
            Q(validity_date__lt=today)|Q(validity_date__isnull=True),
            archive=False,
            record=OuterRef("pk"),
            requires_validity_date=True,
        ) \
        .exclude(mandatory=False, document='')\
        .order_by()\
        .annotate(count=Func(F('id'), function='Count'))\
        .values('count')

    records = HighSchoolStudentRecord.objects.prefetch_related('highschool')\
        .filter(**filter)\
        .annotate(
            user_first_name=F("student__first_name"),
            user_last_name=F("student__last_name"),
            record_level=F("level__label"),
            invalid_dates=Subquery(attestations),
        ).values("id", "user_first_name", "user_last_name", "birth_date", "record_level",
                 "class_name", "creation_date", "validation_date", "rejected_date",
                 "invalid_dates", "highschool__city", "highschool__label",
                 "highschool__with_convention")

    response['data'] = list(records)

    return JsonResponse(response, safe=False)


# REJECT / VALIDATE STUDENT
@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_validate_reject_student(request, validate):
    """
    Validate or reject student
    """
    today = timezone.localdate()
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
                record = HighSchoolStudentRecord.objects\
                    .prefetch_related('attestation')\
                    .get(id=student_record_id, highschool__in=hs)

                # Check documents
                attestations = record.attestation.filter(
                    Q(validity_date__lt=today) | Q(validity_date__isnull=True),
                    archive=False,
                    requires_validity_date=True,
                ).exclude(mandatory=False, document='')

                if validate and attestations.exists():
                    response['msg'] = _("Error: record has missing or invalid attestation dates")
                    return JsonResponse(response, safe=False)

                # 2 => VALIDATED
                # 3 => REJECTED
                record.set_status("VALIDATED" if validate else "REJECTED")
                record.validation_date = timezone.now() if validate else None
                record.rejected_date = None if validate else timezone.now()
                record.save()

                # Todo : test send_message return value
                if validate:
                    record.student.send_message(request, 'CPT_MIN_VALIDE')
                else:
                    record.student.send_message(request, 'CPT_MIN_REJET')

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
        account = ImmersionUser.objects.get(id=account_id)  # , groups__name__in=['LYC', 'ETU'])
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

    # FIXME : test request.user rights on immersion.slot

    if not immersion_id or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            immersion = Immersion.objects.get(pk=immersion_id)
            if immersion.slot.date < today.date() or (immersion.slot.date == today.date()
                                                      and immersion.slot.start_time < today.time()):
                response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                return JsonResponse(response, safe=False)

            if immersion.slot.cancellation_limit_date < timezone.now():
                response = {'error': True, 'msg': _("Slot cancellation deadline has passed")}
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
            immersion.cancellation_date = datetime.datetime.now()
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
    response = {'msg': '', 'data': []}

    if not user_id:
        response['msg'] = gettext("Error : missing user id")
        return JsonResponse(response, safe=False)

    # Valid conditions to view user's immersions : staff and the user himself
    valid_conditions = [
        user.is_master_establishment_manager(),
        user.is_operator(),
        user.is_establishment_manager(),
        user.is_high_school_manager() and user.highschool,
        user.id == user_id
    ]

    if not any(valid_conditions):
        response['msg'] = gettext("Error : invalid user id")
        return JsonResponse(response, safe=False)

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = timezone.localdate()
    now = timezone.now()

    try:
        student = ImmersionUser.objects.get(pk=user_id)
        remaining_registrations = student.remaining_registrations_count()
    except ImmersionUser.DoesNotExist:
        response['msg'] = gettext("Error : no such user")
        return JsonResponse(response, safe=False)

    if user.is_high_school_manager() and not student.accept_to_share_immersions() and student.is_high_school_student():
        response['msg'] = gettext("Error : user don't share his immersions with his highschool")
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
            'cancellable': timezone.now() <= slot.cancellation_limit_date if slot.cancellation_limit_date else True,
            'cancellation_limit_date': slot.cancellation_limit_date,
            'cancellation_type': '',
            'slot_id': slot.id,
            'free_seats': 0,
            'can_register': False,
            'face_to_face': slot.face_to_face,
            'registration_date': immersion.registration_date,
            'cancellation_date': immersion.cancellation_date if immersion.cancellation_date else "",
        }

        if slot.date < today or (slot.date == today and slot.start_time < now.time()):
            immersion_data['time_type'] = "past"
        elif slot.date > today or slot.start_time > now.time():
            immersion_data['time_type'] = "future"

        if slot.n_places:
            immersion_data['free_seats'] = slot.n_places - slot.registered_students()

        if immersion.cancellation_type:
            immersion_data['cancellation_type'] = immersion.cancellation_type.label

            # Check user quota for this period
            if slot.registration_limit_date > now and slot.available_seats() > 0:
                try:
                    period = Period.from_date(date=slot.date)
                except Period.MultipleObjectsReturned:
                    raise

                if period and remaining_registrations[period.pk] > 0:
                    immersion_data['can_register'] = True

        for speaker in slot.speakers.all().order_by('last_name', 'first_name'):
            immersion_data['speakers'].append(f"{speaker.last_name} {speaker.first_name}")

        if slot.course:
            establishments = slot.course.training.distinct_establishments()

            for est in establishments:
                immersion_data['establishments'].append(f"{est.label}")

            if not establishments:
                immersion_data['establishments'].append(str(slot.course.get_etab_or_high_school()))

        immersion_data['establishments'] = ', '.join(immersion_data['establishments'])

        response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required('LYC', 'ETU', 'VIS')
def ajax_get_other_registrants(request, immersion_id):
    immersion = None
    response = {'msg': '', 'data': []}

    try:
        immersion = Immersion.objects.get(pk=immersion_id, student=request.user)
    except ObjectDoesNotExist:
        response['msg'] = gettext("Error : invalid user or immersion id")

    if immersion:
        students = (
            ImmersionUser.objects.prefetch_related('high_school_student_record', 'immersions')
            .filter(
                immersions__slot=immersion.slot,
                high_school_student_record__isnull=False,
                high_school_student_record__visible_immersion_registrations=True,
                immersions__cancellation_type__isnull=True
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
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC', 'CONS-STR')
def ajax_get_slot_registrations(request, slot_id):
    #TODO: should be optimized to avoid loops on queryset
    slot = None
    response = {'msg': '', 'data': []}

    try:
        slot = Slot.objects.get(pk=slot_id)
    except ObjectDoesNotExist:
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
                'registration_date': immersion.registration_date,
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
                    immersion_data['school'] = record.institution.label if record.institution else record.uai_code
                    immersion_data['level'] = record.level.label

            elif immersion.student.is_visitor():
                immersion_data['profile'] = pgettext("person type", "Visitor")

            response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'CONS-STR')
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
                user.is_high_school_manager() and slot_highschool and user.highschool == slot_highschool,
                user.is_structure_consultant() and slot_structure in allowed_structures,
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
    force = request.POST.get('force', False) == "true"
    structure = request.POST.get('structure', False)
    slot, student = None, None
    today = datetime.datetime.today().date()
    today_time = datetime.datetime.today().time()
    visit_or_off_offer = False

    request.session.pop("last_registration_slot", None)

    can_force_reg = any([
        user.is_establishment_manager(),
        user.is_master_establishment_manager(),
        user.is_operator()]
    )

    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            # FIXME ?
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

    # Check if slot date is not passed
    if slot.date < today or (slot.date == today and today_time > slot.start_time):
        response = {'error': True, 'msg': _("Register to past slot is not possible")}
        return JsonResponse(response, safe=False)

    # Slot restrictions validation
    can_register_slot, reasons = student.can_register_slot(slot)
    passed_registration_date = timezone.now() > slot.registration_limit_date

    if not can_register_slot or passed_registration_date:
        if can_force_reg:
            if not force:
                if not can_register_slot:
                    return JsonResponse({
                        'error': True,
                        'msg': 'force_update',
                        'reason': 'restrictions'
                    }, safe=False)

                if passed_registration_date:
                    return JsonResponse({
                        'error': True,
                        'msg': 'force_update',
                        'reason': 'passed_registration_date'
                    }, safe=False)
            else:
                can_register = True
        else:
            if not can_register_slot:
                response = {'error': True, 'msg': _("Cannot register slot due to slot's restrictions")}
                return JsonResponse(response, safe=False)
            if passed_registration_date:
                response = {'error': True, 'msg': _("Cannot register slot due to passed registration date")}
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
        remaining_registrations = student.remaining_registrations_count()
        can_register = False

        try:
            period = Period.from_date(slot.date)
            available_registrations = remaining_registrations.get(period.pk, 0)
        except Period.MultipleObjectsReturned as e:
            raise Exception(_("Multiple periods found for slot %s : please check periods settings") % slot)

        if visit_or_off_offer or available_registrations > 0:
            can_register = True
        elif can_force_reg and not force:
            return JsonResponse({
                'error': True,
                'msg': 'force_update',
                'reason': 'registrations'
            }, safe=False)
        elif force:
            can_register = True
            if slot.is_course():
                # Get slot period
                period = Period.from_date(slot.date)
                student.set_increment_registrations_(period=period)
        elif (user.is_high_school_student() or user.is_student() or user.is_visitor()) and available_registrations <= 0:
            response = {
                'error': True,
                'msg': _(
                    """You have no more remaining registration available for this period, """
                    """you should cancel an immersion or contact immersion service"""
                ),
            }
            return JsonResponse(response, safe=False)
        elif (user.is_structure_manager() or user.is_high_school_manager()) \
                and available_registrations <= 0:
            response = {
                'error': True,
                'msg': _("This student has no more remaining slots to register to for this period"),
            }
            return JsonResponse(response, safe=False)

        if can_register:
            # Cancelled immersion exists : re-register
            if student.immersions.filter(slot=slot, cancellation_type__isnull=False).exists():
                student.immersions.filter(slot=slot, cancellation_type__isnull=False).update(
                    cancellation_type=None, attendance_status=0, cancellation_date=None
                )
            else:
                # New registration
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

    try:
        slot = Slot.objects.get(pk=slot_id)
    except Slot.DoesNotExist:
        response['msg'] = _("Error : slot not found")
        return JsonResponse(response, safe=False)

    # Secondary query needed in exclude : we need to see students who have cancelled their registration to
    # keep the possibility to readd them
    students = ImmersionUser.objects \
        .filter(groups__name__in=['LYC', 'ETU', 'VIS'], validation_string__isnull=True) \
        .exclude(immersions__in=(Immersion.objects.filter(slot__id=slot_id, cancellation_type__isnull=True)))

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

                    if record.level.is_post_bachelor and record.post_bachelor_level:
                        student_data['level'] += f" - {record.post_bachelor_level.label}"

            elif student.is_student():
                student_data['profile'] = pgettext("person type", "Student")
                student_data['school'] = record.institution.label if record.institution else record.uai_code
                student_data['level'] = record.level.label if record.level else ""

            elif student.is_visitor():
                student_data['profile'] = pgettext("person type", "Visitor")

            response['data'].append(student_data.copy())

    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_get_highschool_students(request):
    """
    Retrieve students from a highschool or all students if user is ref-etab manager
    and no highschool id is specified
    """
    highschool_id = None
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

    if request.user.is_high_school_manager() and request.user.highschool\
            and not request.user.highschool.postbac_immersion:
        highschool_id = request.user.highschool.id

    if highschool_id:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record__highschool',
            'high_school_student_record__post_bachelor_level',
            'high_school_student_record__bachelor_type',
            'high_school_student_record__origin_bachelor_type',
            'immersions', 'groups'
        ).filter(
            validation_string__isnull=True, high_school_student_record__highschool__id=highschool_id
        )
    else:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record__level', 'high_school_student_record__highschool',
            'high_school_student_record__post_bachelor_level',
            'high_school_student_record__origin_bachelor_type',
            'student_record__level', 'student_record__institution',
            'student_record__origin_bachelor_type', 'visitor_record',
            'immersions', 'groups'
        ).filter(validation_string__isnull=True, groups__name__in=['ETU', 'LYC', 'VIS'])

    if no_record_filter:
        students = students.filter(
            high_school_student_record__isnull=True,
            student_record__isnull=True,
            visitor_record__isnull=True
        )
    else:
        students = students.filter(
            Q(high_school_student_record__isnull=False) |
            Q(student_record__isnull=False) |
            Q(visitor_record__isnull=False)
        )

    students = students.annotate(
        high_school_record_id=F('high_school_student_record__id'),
        student_record_id=F('student_record__id'),
        visitor_record_id=F('visitor_record__id'),
        user_type=Case(
            When(
                high_school_student_record__isnull=False,
                then=Value(pgettext("person type", "High school student"))
            ),
            When(student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
            When(visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
            default=Value(gettext("Unknown"))
        ),
        level=Coalesce(
            F('high_school_student_record__level__label'),
            F('student_record__level__label')
        ),
        birth_date=Coalesce(
            F('student_record__birth_date'),
            F('high_school_student_record__birth_date'),
            F('visitor_record__birth_date')
        ),
        class_name=F('high_school_student_record__class_name'),
        high_school_id=F('high_school_student_record__highschool__id'),
        institution=Coalesce(
            F('high_school_student_record__highschool__label'),
            F('student_record__institution__label'),
        ),
        uai_code=F('student_record__uai_code'),
        high_school_student_level=F('high_school_student_record__level__label'),
        post_bachelor_level=Coalesce(
            F('student_record__current_diploma'),
            F('high_school_student_record__post_bachelor_level__label')
        ),
        is_post_bachelor=F('high_school_student_record__level__is_post_bachelor'),
        student_origin_bachelor=F('student_record__origin_bachelor_type__label'),
        hs_origin_bachelor=F('high_school_student_record__origin_bachelor_type__label'),
        bachelor=F('high_school_student_record__bachelor_type__label'),
        registered=Count(F('immersions')),
        allow_high_school_consultation=Case(
            When(
                high_school_student_record__highschool__with_convention=True,
                then=F('high_school_student_record__allow_high_school_consultation'),
            ),
            default=True
        )
    ).values()

    response['data'] = [l for l in students]

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'CONS-STR')
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

    if immersions:
        # Add slot label, date and time to email's subject
        s = immersions.first().slot
        slot_label = s.get_label()
        date = date_format(s.date, format='l d F Y', use_l10n=True)
        start_time = s.start_time.isoformat(timespec='minutes')
        end_time = s.end_time.isoformat(timespec='minutes')
        subject = f"{slot_label} : {date} ({start_time}-{end_time}) - {subject}"

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


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
def get_csv_structures(request):
    filters = {}
    Q_filters = Q()
    content = []
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')

    structures = request.user.get_authorized_structures()
    structure_label = structures[0].label.replace(' ', '_') if structures.count() == 1 else 'structures'
    t = request.GET.get('type')
    infield_separator = '|'

    if not t:
        raise Http404

    registered_students_count= Immersion.objects\
        .filter(slot=OuterRef("pk"), cancellation_type__isnull=True) \
        .order_by() \
        .annotate(
            count=Func(F('id'), function='Count')
        ) \
        .values('count')

    # Export courses
    if t == 'course':

        label = _('courses')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
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
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'establishment', 'structure', 'domains', 'subdomains', 'training_label',
                'course_label', 'slot_course_type', 'slot_date', 'slot_start_time', 'slot_end_time',
                'slot_campus', 'slot_building', 'slot_room', 'slot_speakers', 'registered',
                'slot_n_places', 'info'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
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
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            filters[
                'course__structure__in'
            ] = request.user.establishment.structures.all()


            fields = [
                'structure', 'domains', 'subdomains', 'training_label',
                'course_label', 'slot_course_type', 'slot_date', 'slot_start_time', 'slot_end_time',
                'slot_campus', 'slot_building', 'slot_room', 'slot_speakers', 'registered',
                'slot_n_places', 'info'
            ]

        elif request.user.is_high_school_manager():

            header = [
                _('training domain'),
                _('training subdomain'),
                _('training'),
                _('course'),
                _('course_type'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]
            filters[
                'course__highschool'
            ] = request.user.highschool

            fields = [
                'domains', 'subdomains', 'training_label', 'course_label', 'slot_course_type',
                'slot_date', 'slot_start_time', 'slot_end_time', 'slot_room', 'slot_speakers',
                'registered', 'slot_n_places', 'info'
            ]

        elif request.user.is_structure_manager():
            header = [
                _('structure'),
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
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]
            filters[
                'course__structure__in'
            ] = structures

            fields = [
                'structure', 'domains', 'subdomains', 'training_label', 'course_label',
                'slot_course_type', 'slot_date', 'slot_start_time', 'slot_end_time',
                'slot_campus', 'slot_building', 'slot_room', 'slot_speakers', 'registered',
                'slot_n_places', 'info'
            ]

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','course', 'course__establishment', 'course__structure',
            'course__highschool', 'course__training__training_subdomains'
        ).filter(**filters, published=True, course__isnull=False, immersions__cancellation_type__isnull=True
        ).order_by('date', 'start_time')

        content = slots.annotate(
            establishment=Coalesce(
                F('course__structure__establishment__label'),
                Concat(F('course__highschool__label'),
                       Value(' - '),
                       F('course__highschool__city'),
                       output_field=CharField()
                    )
            ),
            structure=F('course__structure__label'),
            domains=StringAgg(
                F('course__training__training_subdomains__training_domain__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            subdomains=StringAgg(
                F('course__training__training_subdomains__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            training_label=F('course__training__label'),
            course_label=F('course__label'),
            slot_course_type=F('course_type__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(
            *fields
        )

    # Export visits
    if t == 'visit':

        label = _('visits')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
                _('highschool'),
                _('purpose'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'establishment', 'structure', 'highschool', 'purpose', 'meeting_place',
                'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('highschool'),
                _('purpose'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'structure', 'highschool', 'purpose', 'meeting_place', 'slot_date', 'slot_start_time',
                'slot_end_time', 'slot_speakers', 'registered', 'slot_n_places', 'info'
            ]

            Q_filters = Q(visit__establishment=request.user.establishment) | Q(
                visit__structure__in=request.user.establishment.structures.all()
            )

        elif request.user.is_structure_manager():

            header = [
                _('structure'),
                _('highschool'),
                _('purpose'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'structure', 'highschool', 'purpose', 'meeting_place', 'slot_date', 'slot_start_time',
                'slot_end_time', 'slot_speakers', 'registered', 'slot_n_places', 'info'
            ]

            filters[
                'visit__structure__in'
            ] = structures

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','visit', 'visit__establishment', 'visit__structure',
            'visit__highschool'
        ).filter(
            Q_filters, **filters, published=True, visit__isnull=False, immersions__cancellation_type__isnull=True
        ).order_by('date', 'start_time')

        content = slots.annotate(
            establishment=F('visit__establishment__label'),
            structure=F('visit__structure__label'),
            highschool=F('visit__highschool__label'),
            purpose=F('visit__purpose'),
            meeting_place=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(
            *fields
        )

    # Export events
    if t == 'event':

        label = _('events')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
                _('event type'),
                _('label'),
                _('description'),
                _('campus'),
                _('building'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),

            ]

            fields = [
                'establishment', 'structure', 'type', 'label', 'desc', 'slot_campus', 'slot_building',
                'slot_room', 'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('event type'),
                _('label'),
                _('description'),
                _('campus'),
                _('building'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            Q_filters = Q(event__establishment=request.user.establishment) | Q(
                event__structure__in=request.user.establishment.structures.all()
            )

            fields = [
                'structure', 'type', 'label', 'desc', 'slot_campus', 'slot_building',
                'slot_room', 'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info'
            ]

        elif request.user.is_structure_manager():

            header = [
                _('structure'),
                _('event type'),
                _('label'),
                _('description'),
                _('campus'),
                _('building'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            filters[
                'event__structure__in'
            ] = structures

            fields = [
                'structure', 'type', 'label', 'desc', 'slot_campus', 'slot_building',
                'slot_room', 'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info'
            ]

        elif request.user.is_high_school_manager():

            header = [
                _('event type'),
                _('label'),
                _('description'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            filters[
                'event__highschool'
            ] = request.user.highschool

            fields = [
                'type', 'label', 'desc', 'slot_room', 'slot_date', 'slot_start_time',
                'slot_end_time', 'slot_speakers', 'registered', 'slot_n_places', 'info'
            ]

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','event', 'event__establishment', 'event__structure',
            'event__highschool'
        ).filter(Q_filters, **filters, published=True, event__isnull=False, immersions__cancellation_type__isnull=True
        ).order_by('date', 'start_time')

        content = slots.annotate(
            establishment=Coalesce(
                F('event__establishment__label'),
                Concat(F('event__highschool__label'), Value(' - '), F('event__highschool__city'), output_field=CharField())
            ),
            structure=F('event__structure__label'),
            type=F('event__event_type__label'),
            label=F('event__label'),
            desc=F('event__description'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(
            *fields
        )

    # Forge CSV file
    response['Content-Disposition'] = f'attachment; filename="{structure_label}_{label}_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(content)

    return response


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def get_csv_highschool(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    hs = request.user.highschool
    h_name = hs.label.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{h_name}_{today}.csv"'
    infield_separator = '|'
    header = [
        _('last name'),
        _('first name'),
        _('birthdate'),
        _('level'),
        _('class name'),
        _('bachelor type'),
        _('establishment'),
        _('type'),
        _('training domain'),
        _('training subdomain'),
        _('training'),
        _('course/event/visit label'),
        _('date'),
        _('start_time'),
        _('end_time'),
        _('campus'),
        _('building'),
        _('meeting place'),
        _('attendance status'),
        _('additional information'),
        _('high school consultancy agreement'),
        _('registrations visibility agreement')
    ]

    Q_filters = Q(immersions__cancellation_type__isnull=True)

    students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record__level', 'high_school_student_record__highschool',
            'high_school_student_record__bachelor_type', 'immersions',
            'immersions__slot'
        ).filter(
            Q_filters,
            groups__name='LYC',
            high_school_student_record__highschool__id=hs.id,
        ).order_by('last_name', 'first_name')

    attendance_status_choices = dict(Immersion._meta.get_field('attendance_status').flatchoices)
    attendance_status_whens = [
        When(
            immersions__attendance_status=k,
            then=Value(str(v))
        ) for k, v in attendance_status_choices.items()
    ]

    agreed_students = students.filter(high_school_student_record__allow_high_school_consultation=True).annotate(
        student_last_name=F('last_name'),
        student_first_name=F('first_name'),
        student_birth_date=ExpressionWrapper(
            Func(F('high_school_student_record__birth_date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
        ),
        student_bachelor_type=F('high_school_student_record__bachelor_type__label'),
        slot_establishment=Coalesce(
            F('immersions__slot__course__structure__establishment__label'),
            F('immersions__slot__visit__establishment__label'),
            F('immersions__slot__event__establishment__label'),
        ),
        slot_type=Case(
            When(immersions__slot__course__isnull=False,then=Value(pgettext("slot type", "Course"))),
            When(immersions__slot__visit__isnull=False, then=Value(pgettext("slot type", "Visit"))),
            When(immersions__slot__event__isnull=False, then=Value(pgettext("slot type", "Event"))),
            When(immersions__isnull=False, then=Value("")),
        ),
        domains=StringAgg(
            F('immersions__slot__course__training__training_subdomains__training_domain__label'),
             infield_separator, default=Value(''), output_field=CharField(), distinct=True
        ),
        subdomains=StringAgg(
            F('immersions__slot__course__training__training_subdomains__label'),
             infield_separator, default=Value(''), output_field=CharField(), distinct=True
        ),
        training_label=F('immersions__slot__course__training__label'),
        slot_label=Coalesce(
            F('immersions__slot__course__label'),
            F('immersions__slot__visit__purpose'),
            F('immersions__slot__event__label'),
        ),
        slot_date=ExpressionWrapper(
            Func(F('immersions__slot__date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
        ),
        slot_start_time=F('immersions__slot__start_time'),
        slot_end_time=F('immersions__slot__end_time'),
        slot_campus_label=F('immersions__slot__campus__label'),
        slot_building=F('immersions__slot__building__label'),
        slot_room=Case(
            When(immersions__slot__face_to_face=True,then=F('immersions__slot__room')),
            When(immersions__slot__face_to_face=False, then=Value(gettext('Remote'))),
        ),
        attendance=Case(*attendance_status_whens, output_field=CharField()),
        informations=F('immersions__slot__additional_information'),
        detail_consultancy=Case(
            When(high_school_student_record__allow_high_school_consultation=True,then=Value(gettext('Yes'))),
            When(high_school_student_record__allow_high_school_consultation=False,then=Value(gettext('No'))),
        ),
        detail_registrations=Case(
            When(high_school_student_record__visible_immersion_registrations=True,then=Value(gettext('Yes'))),
            When(high_school_student_record__visible_immersion_registrations=False,then=Value(gettext('No'))),
        ),
    ).values_list(
        'student_last_name', 'student_first_name', 'student_birth_date', 'high_school_student_record__level__label',
        'high_school_student_record__class_name', 'student_bachelor_type', 'slot_establishment',
        'slot_type', 'domains', 'subdomains', 'training_label', 'slot_label', 'slot_date', 'slot_start_time',
        'slot_end_time', 'slot_campus_label', 'slot_building', 'slot_room', 'attendance', 'informations',
        'detail_consultancy', 'detail_registrations'
    )

    not_agreed_students = students.filter(high_school_student_record__allow_high_school_consultation=False).annotate(
        student_last_name=F('last_name'),
        student_first_name=F('first_name'),
        student_birth_date=ExpressionWrapper(
            Func(F('high_school_student_record__birth_date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
        ),
        student_bachelor_type=F('high_school_student_record__bachelor_type__label'),
        slot_establishment=Value(''),
        slot_type=Value(''),
        domains=Value(''),
        subdomains=Value(''),
        training_label=Value(''),
        slot_label=Value(''),
        slot_date=Value(''),
        slot_start_time=Value(''),
        slot_end_time=Value(''),
        slot_campus_label=Value(''),
        slot_building=Value(''),
        slot_room=Value(''),
        attendance=Value(''),
        informations=Value(''),
        detail_consultancy=Case(
            When(high_school_student_record__allow_high_school_consultation=True,then=Value(gettext('Yes'))),
            When(high_school_student_record__allow_high_school_consultation=False,then=Value(gettext('No'))),
        ),
        detail_registrations=Case(
            When(high_school_student_record__visible_immersion_registrations=True,then=Value(gettext('Yes'))),
            When(high_school_student_record__visible_immersion_registrations=False,then=Value(gettext('No'))),
        ),
    ).values_list(
        'student_last_name', 'student_first_name', 'student_birth_date', 'high_school_student_record__level__label',
        'high_school_student_record__class_name', 'student_bachelor_type', 'slot_establishment',
        'slot_type', 'domains', 'subdomains', 'training_label', 'slot_label', 'slot_date', 'slot_start_time',
        'slot_end_time', 'slot_campus_label', 'slot_building', 'slot_room', 'attendance', 'informations',
        'detail_consultancy', 'detail_registrations'
    )

    # Forge csv file and return it
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(list(chain(agreed_students, not_agreed_students.distinct())))

    return response


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def get_csv_anonymous(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today = _date(datetime.datetime.today(), 'Ymd')
    infield_separator = '|'
    t = request.GET.get('type')
    filters = {}
    Q_filters = Q()
    if not t:
        raise Http404

    registered_students_count= Immersion.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True) \
                                .order_by().annotate(
                                    count=Func(F('id'), function='Count')
                                ).values('count')

    attendance_status_choices = dict(Immersion._meta.get_field('attendance_status').flatchoices)
    attendance_status_whens = [
        When(
            immersions__attendance_status=k,
            then=Value(str(v))
        ) for k, v in attendance_status_choices.items()
    ]

    # Export courses
    if t == 'course':

        label = _('anonymous_courses')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
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
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('registrant profile'),
                _('origin institution'),
                _('student level'),
                _('attendance status'),
            ]

            fields = [
                'establishment', 'structure', 'domains', 'subdomains', 'training_label',
                'course_label', 'slot_course_type', 'slot_date', 'slot_start_time', 'slot_end_time',
                'slot_campus', 'slot_building', 'slot_room', 'slot_speakers', 'registered',
                'slot_n_places', 'info', 'registrant_profile', 'origin_institution',
                'level', 'attendance'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
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
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('registrant profile'),
                _('origin institution'),
                _('student level'),
                _('attendance status'),
            ]

            fields = [
                'structure', 'domains', 'subdomains', 'training_label', 'course_label', 'slot_course_type',
                'slot_date', 'slot_start_time', 'slot_end_time', 'slot_campus', 'slot_building',
                'slot_room', 'slot_speakers', 'registered', 'slot_n_places', 'info',
                'registrant_profile', 'origin_institution', 'level', 'attendance'
            ]

            filters[
                'course__structure__in'
            ] = request.user.establishment.structures.all()

        content = []

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','course', 'course__establishment', 'course__structure',
            'course__highschool', 'student__visitor_record', 'student__student_record',
            'student__high_school_student_record', 'course__training__training_subdomains'
        ).filter(**filters, published=True, course__isnull=False, immersions__cancellation_type__isnull=True)

        content = slots.annotate(
            establishment=Coalesce(
                F('course__structure__establishment__label'),
                Concat(F('course__highschool__label'), Value(' - '), F('course__highschool__city'), output_field=CharField())
            ),
            structure=F('course__structure__label'),
            domains=StringAgg(
                F('course__training__training_subdomains__training_domain__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            subdomains=StringAgg(
                F('course__training__training_subdomains__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            training_label=F('course__training__label'),
            course_label=F('course__label'),
            slot_course_type=F('course_type__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
            registrant_profile=Case(
                When(
                    immersions__student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student"))
                ),
                When(immersions__student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(immersions__student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value('')
            ),
            origin_institution=Coalesce(
                F('immersions__student__high_school_student_record__highschool__label'),
                F('immersions__student__student_record__institution__label'),
                F('immersions__student__student_record__uai_code'),
            ),
            level=Coalesce(
                F('immersions__student__high_school_student_record__level__label'),
                F('immersions__student__student_record__level__label'),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
        ).values_list(
            *fields
        )

    # Export visits
    if t == 'visit':

        label = _('anonymous_visits')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
                _('highschool'),
                _('purpose'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('student level'),
                _('attendance status'),
            ]

            fields = [
                'establishment', 'structure', 'highschool', 'purpose', 'meeting_place',
                'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info', 'level', 'attendance'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('highschool'),
                _('purpose'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('student level'),
                _('attendance status'),
            ]

            fields = [
                'structure', 'highschool', 'purpose', 'meeting_place',
                'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info', 'level', 'attendance'
            ]

            Q_filters = Q(visit__establishment=request.user.establishment) | Q(
                visit__structure__in=request.user.establishment.structures.all()
            )

        content = []

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','visit', 'visit__establishment', 'visit__structure',
            'visit__highschool', 'student__visitor_record', 'student__student_record',
            'student__high_school_student_record',
        ).filter(Q_filters, published=True, visit__isnull=False, immersions__cancellation_type__isnull=True)

        content = slots.annotate(
            establishment=F('visit__establishment__label'),
            structure=F('visit__structure__label'),
            highschool=F('visit__highschool__label'),
            purpose=F('visit__purpose'),
            meeting_place=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
            level=Coalesce(
                F('immersions__student__high_school_student_record__level__label'),
                F('immersions__student__student_record__level__label'),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
        ).values_list(
            *fields
        )

    # Export events
    if t == 'event':

        label = _('anonymous_events')

        if request.user.is_master_establishment_manager() or request.user.is_operator():

            header = [
                _('establishment'),
                _('structure'),
                _('event type'),
                _('label'),
                _('description'),
                _('campus'),
                _('building'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('registrant information'),
                _('origin institution'),
                _('student level'),
                _('attendance status'),
            ]

            fields = [
                'establishment', 'structure', 'type', 'label', 'desc', 'slot_campus', 'slot_building',
                'slot_room', 'slot_date', 'slot_start_time', 'slot_end_time', 'slot_speakers',
                'registered', 'slot_n_places', 'info', 'registrant_profile', 'institution', 'level', 'attendance'
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('event type'),
                _('label'),
                _('description'),
                _('campus'),
                _('building'),
                _('meeting place'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
                _('registrant information'),
                _('origin institution'),
                _('student level'),
                _('attendance status'),
            ]
            filters[
                'event__establishment'
            ] = request.user.establishment

            fields = [
                'structure', 'type', 'label', 'desc', 'slot_campus', 'slot_building', 'slot_room', 'slot_date',
                'slot_start_time', 'slot_end_time', 'slot_speakers', 'registered', 'slot_n_places', 'info',
                'registrant_profile', 'institution', 'level', 'attendance'
            ]

        content = []

        slots = Slot.objects.prefetch_related(
            'immersions','speakers','event', 'event__establishment', 'event__structure',
            'event__highschool', 'student__visitor_record', 'student__student_record',
            'student__high_school_student_record',
        ).filter(**filters, published=True, event__isnull=False, immersions__cancellation_type__isnull=True)

        content = slots.annotate(
            establishment=Coalesce(
                F('event__establishment__label'),
                Concat(F('event__highschool__label'), Value(' - '), F('event__highschool__city'), output_field=CharField())
            ),
            structure=F('event__structure__label'),
            type=F('event__event_type__label'),
            label=F('event__label'),
            desc=F('event__description'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(face_to_face=True,then=F('room')),
                When(face_to_face=False, then=Value(gettext('Remote'))),
            ),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
            registrant_profile=Case(
                When(
                    immersions__student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student"))
                ),
                When(immersions__student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(immersions__student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value('')
            ),
            institution=Coalesce(
                F('immersions__student__high_school_student_record__highschool__label'),
                F('immersions__student__student_record__institution__label'),
                F('immersions__student__student_record__uai_code'),
            ),
            level=Coalesce(
                F('immersions__student__high_school_student_record__level__label'),
                F('immersions__student__student_record__level__label'),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
        ).values_list(
            *fields
        )

    # Export registrations
    if t == 'registration':

        label = _('anonymous_registrations')

        header = [
            _('anonymous identity'),
            _('registrant profile'),
            _('student level'),
            _('origin institution'),
            _("Origin bachelor type"),
            _('establishment'),
            _('slot type'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('label'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('attendance status'),
            _('additional information'),
        ]

        if request.user.is_establishment_manager():

            filters[
                'slot__course__structure__in'
            ] = request.user.establishment.structures.all()

        content = []

        immersions = Immersion.objects.prefetch_related(
            'slot','student','slot__event__establishment', 'slot__event__structure',
            'slot__event__highschool', 'slot__speakers', 'slot__visit__establishment'
            'slot__visit__structure', 'slot__visit__highschool', 'slot__course__structure',
            'slot__course__highschool', 'student__visitor_record',
            'student__student_record__origin_bachelor_type'
            'student__student_record__institution',
            'student__high_school_student_record__origin_bachelor_type',
            'student__high_school_student_record__level',
            'student__high_school_student_record__highschool',
        ).filter(
            cancellation_type__isnull=True, slot__published=True, **filters
        )

        faker = Faker(settings.LANGUAGE_CODE)
        Faker.seed(4321)
        fake_names = {i:faker.name() for i in immersions.values_list('student__id',flat=True)}
        fake_names_whens = [
            When(
                student__id=k,
                then=Value(fake_names[k])
            ) for k,v in fake_names.items()
        ]

        attendance_status_choices = dict(Immersion._meta.get_field('attendance_status').flatchoices)
        attendance_status_whens = [
            When(
                attendance_status=k,
                then=Value(str(v))
            ) for k, v in attendance_status_choices.items()
        ]

        content = immersions.annotate(
            fake_name=Case(*fake_names_whens, output_field=CharField()),
            type=Case(
                When(
                    student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student"))
                ),
                When(student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value(gettext("Unknown"))
            ),
            level=Coalesce(
                F('student__high_school_student_record__level__label'),
                F('student__student_record__level__label')
            ),
            institution=Coalesce(
                F('student__high_school_student_record__highschool__label'),
                F('student__student_record__institution__label'),
                F('student__student_record__uai_code'),

            ),
            origin_bachelor_type=Coalesce(
                F('student__student_record__origin_bachelor_type__label'),
                F('student__high_school_student_record__origin_bachelor_type__label'),
            ),
            establishment=Coalesce(
                F('slot__course__structure__establishment__label'),
                F('slot__visit__establishment__label'),
                F('slot__event__establishment__label'),
            ),
            slot_type=Case(
                When(slot__course__isnull=False,then=Value(pgettext("slot type", "Course"))),
                When(slot__visit__isnull=False, then=Value(pgettext("slot type", "Visit"))),
                When(slot__event__isnull=False, then=Value(pgettext("slot type", "Event"))),
            ),
            domains=StringAgg(
                F('slot__course__training__training_subdomains__training_domain__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            subdomains=StringAgg(
                F('slot__course__training__training_subdomains__label'),
                 infield_separator, default=Value(''), output_field=CharField(), distinct=True
            ),
            training_label=F('slot__course__training__label'),
            slot_label=Coalesce(
                F('slot__course__label'),
                F('slot__visit__purpose'),
                F('slot__event__label'),
            ),
            slot_date=ExpressionWrapper(
                Func(F('slot__date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('slot__start_time'),
            slot_end_time=F('slot__end_time'),
            slot_campus_label=F('slot__campus__label'),
            slot_building=F('slot__building__label'),
            slot_room=Case(
                When(slot__face_to_face=True,then=F('slot__room')),
                When(slot__face_to_face=False, then=Value(gettext('Remote'))),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
            informations=F('slot__additional_information')

        ).values_list(
            'fake_name', 'type', 'level', 'institution', 'origin_bachelor_type', 'establishment',
            'slot_type', 'domains', 'subdomains', 'training_label', 'slot_label', 'slot_date',
            'slot_start_time', 'slot_end_time', 'slot_campus_label', 'slot_building', 'slot_room',
            'attendance', 'informations'
        )

    # Forge csv
    response['Content-Disposition'] = f'attachment; filename={label}_{today}.csv'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(content)
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

    # Ref-etab mail sending
    try:
        body = _('Mail sent by %s from contact form') % f'{firstname} {lastname} ({email})' + '<br><br>' + body
        send_email(recipient, subject, body, None, f'{firstname} {lastname} <{email}>')
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
@groups_required('REF-ETAB', 'SRV-JUR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_get_student_presence(request, date_from=None, date_until=None):
    response = {'data': [], 'msg': ''}

    filters = {}
    Q_filters = Q()

    if date_from and date_from != "None":
        filters["slot__date__gte"] = date_from

    if date_until and date_until != "None":
        filters["slot__date__lte"] = date_until

    filters["slot__visit__isnull"] = True

    if (
        not request.user.is_superuser
        and(request.user.is_establishment_manager()
        or request.user.is_legal_department_staff())
    ):

        structures = request.user.establishment.structures.all()

        Q_filters = (
            Q(slot__course__structure__in=structures) |
            Q(slot__event__structure__in=structures, slot__face_to_face=True)
        )

    elif request.user.is_high_school_manager() and not request.user.is_superuser:

        Q_filters = (
            Q(slot__course__highschool=request.user.highschool) |
            Q(slot__event__highschool=request.user.highschool, slot__face_to_face=True)
        )
    else:

        Q_filters = (
            Q(slot__event__isnull=False, slot__face_to_face=True) |
            Q(slot__course__isnull=False)

        )

    immersions = Immersion.objects\
        .prefetch_related(
            'slot__campus', 'slot__building', 'slot__course__structure__establishment',
            'slot__visit__establishment', 'slot__event__establishment', 'slot__course__structure',
            'slot__visit__structure', 'slot__event__structure', 'student__high_school_student_record__highschool',
            'student__student_record__institution', 'student__visitor_record',
        )\
        .filter(Q_filters, **filters, cancellation_type__isnull=True)\
        .annotate(
            date=F('slot__date'),
            start_time=F('slot__start_time'),
            end_time=F('slot__end_time'),
            student_profile=Case(
                When(
                    student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student"))
                ),
                When(student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value(gettext("Unknown")),
            ),
            institution=Coalesce(
                F('student__high_school_student_record__highschool__label'),
                F('student__student_record__institution__label'),
                F('student__student_record__uai_code'),
                Value('')
            ),
            first_name=F('student__first_name'),
            last_name=F('student__last_name'),
            phone=Coalesce(
                F('student__high_school_student_record__phone'),
                F('student__student_record__phone'),
                F('student__visitor_record__phone'),
                Value('')
            ),
            email=F('student__email'),
            campus=F('slot__campus__label'),
            building=F('slot__building__label'),
            meeting_place=Case(
                When(
                    slot__face_to_face=True,
                    then=F('slot__room')
                ),
                default=Value(gettext('Remote')),
            ),
            establishment=Coalesce(
                F('slot__course__structure__establishment__label'),
                F('slot__visit__establishment__label'),
                F('slot__event__establishment__label'),
                F('slot__course__highschool__label'),
                F('slot__visit__highschool__label'),
                F('slot__event__highschool__label'),
            ),
            structure=Coalesce(
                F('slot__course__structure__label'),
                F('slot__visit__structure__label'),
                F('slot__event__structure__label'),
            )
        )\
        .values()

    response['data'] = [i for i in immersions]

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

    # Add an alert and warn the user if it already exists:
    alert, created = UserCourseAlert.objects.get_or_create(
        email=email,
        course=course,
        defaults={'email_sent': False}
    )

    if not created and not alert.email_sent:
        response['error'] = True
        response['msg'] = gettext('You have already set an alert on this course')
        return JsonResponse(response, safe=False)

    response['msg'] = gettext('Alert successfully set')
    return JsonResponse(response, safe=False)


class UserCourseAlertList(generics.ListCreateAPIView):
    """
    User course alerts
    """
    serializer_class = UserCourseAlertSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [IsVisitorPermissions|IsHighSchoolStudentPermissions|IsStudentPermissions|CustomDjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user

        queryset = UserCourseAlert.objects\
            .prefetch_related('course__training__training_subdomains__training_domain')\
            .filter(email=user.email)

        return queryset


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
        registrations = []

        for record_id in t:
            try:
                record = HighSchoolStudentRecord.objects.get(pk=record_id)
                immersions_nb = Immersion.objects.prefetch_related('slot').filter(student=record.student.pk,
                                                                               cancellation_type__isnull=True).count()

                records.append(record)
                registrations.append(immersions_nb)
            except HighSchoolStudentRecord.DoesNotExist:
                continue


        if len(records) > 1:
            dupes_data = {
                "id": id,
                "record_ids": [r.id for r in records],
                "account_ids": [r.student.id for r in records],
                "names": [str(r.student) for r in records],
                "birthdates": [_date(r.birth_date) for r in records],
                "highschools": [f"{r.highschool.label}, {r.class_name}" for r in records],
                "emails": [r.student.email for r in records],
                "record_status": [r.validation for r in records],
                "record_links": [reverse('immersion:modify_hs_record', kwargs={'record_id': r.id}) for r in records],
                "registrations": [ _('Yes') if r > 0 else _('No') for r in registrations],
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


@login_required
@is_post_request
@groups_required('INTER')
def remove_link(request):
    """
    Remove user link : remove user_id from authenticated user usergroup
    """
    response = {'data': [], 'msg': '', 'error': ''}

    user = request.user
    remove_user_id = request.POST.get('user_id')

    try:
        user_group = user.usergroup.first()
        user_group.immersionusers.remove(remove_user_id)
        response['msg'] = gettext('User removed from your group')
    except Exception:
        # No group or user not in group : nothing to do
        pass

    return JsonResponse(response, safe=False)


class CampusList(generics.ListCreateAPIView):
    """
    Campus list
    """
    serializer_class = CampusSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', ]
    permission_classes = [CustomDjangoModelPermissions]

    def get_queryset(self):
        queryset = Campus.objects.filter(active=True).order_by('label')
        user = self.request.user

        if not user.is_superuser and user.is_establishment_manager():
            queryset = queryset.filter(establishment=user.establishment)

        return queryset

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)


class EstablishmentList(generics.ListAPIView):
    """
    Establishments list
    """
    serializer_class = EstablishmentSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['active', ]

    def get_queryset(self):
        queryset = Establishment.activated.order_by('label')
        user = self.request.user

        if not user.is_superuser and user.is_establishment_manager():
            queryset = queryset.filter(id=user.establishment.id)

        return queryset


class StructureList(generics.ListCreateAPIView):
    """
    Structures list
    """
    serializer_class = StructureSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', ]
    permission_classes = [CustomDjangoModelPermissions|IsStructureManagerPermissions|IsStructureConsultantPermissions|IsEstablishmentManagerPermissions]

    def get_queryset(self):
        queryset = Structure.activated.order_by('code', 'label')
        user = self.request.user

        if not user.is_superuser:
            if user.is_structure_manager() or user.is_structure_consultant():
                return user.structures.order_by('code', 'label')
            if user.is_establishment_manager() and user.establishment:
                return user.establishment.structures.order_by('code', 'label')

        return queryset

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)


class TrainingList(generics.ListCreateAPIView):
    """
    Training list / creation
    Returns only active trainings
    """
    # queryset = Training.objects.all()
    serializer_class = TrainingSerializer
    permission_classes = [
        IsRefLycPermissions|IsMasterEstablishmentManagerPermissions|IsEstablishmentManagerPermissions|
        IsStructureManagerPermissions|IsTecPermissions|CustomDjangoModelPermissions|IsStructureConsultantPermissions
    ]
    filterset_fields = ['structures', 'highschool', ]

    # Auth : default (see settings/base.py)

    def get_queryset(self):
        user = self.request.user
        trainings_queryset = Training.objects.filter(active=True)

        if user.is_high_school_manager():
            return trainings_queryset.filter(highschool=user.highschool)
        elif user.is_establishment_manager():
            return trainings_queryset.filter(structures__establishment=user.establishment)

        return trainings_queryset


    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class TrainingDomainList(generics.ListCreateAPIView):
    """
    Training domain list / creation
    """
    queryset = TrainingDomain.objects.all()
    serializer_class = TrainingDomainSerializer
    permission_classes = [CustomDjangoModelPermissions]
    # Auth : default (see settings/base.py)

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class TrainingSubdomainList(generics.ListCreateAPIView):
    """
    Training subdomain list / creation
    """
    model = TrainingSubdomain
    queryset = TrainingSubdomain.objects.all()
    serializer_class = TrainingSubdomainSerializer
    permission_classes = [CustomDjangoModelPermissions]
    # Auth : default (see settings/base.py)

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class SpeakerList(generics.ListCreateAPIView):
    """
    Speakers (only) list / creation
    """
    model = ImmersionUser
    serializer_class = SpeakerSerializer
    permission_classes = [SpeakersReadOnlyPermissions|CustomDjangoModelPermissions]
    filterset_fields = ['highschool', ]
    # Auth : default (see settings/base.py)

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args,**kwargs)

    def get_queryset(self):
        self.user = self.request.user

        course_id = self.kwargs.get("course_id")
        visit_id = self.kwargs.get("visit_id")
        event_id = self.kwargs.get("event_id")

        if course_id:
            return Course.objects.get(id=course_id).speakers.all()
        if visit_id:
            return Visit.objects.get(id=visit_id).speakers.all()
        if event_id:
            return OffOfferEvent.objects.get(id=event_id).speakers.all()

        filters = {'groups__name': 'INTER'}

        if self.user.is_high_school_manager():
            filters["highschool"] = self.user.highschool

        return ImmersionUser.objects.prefetch_related("groups").filter(**filters)

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class HighSchoolList(generics.ListCreateAPIView):
    """
    High schools list / creation
    Unauthenticated GET is granted only when requesting high schools with valid agreements
    Other users need authentication or Django permissions (can_* ...)
    """
    model = HighSchool
    serializer_class = HighSchoolSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [HighSchoolReadOnlyPermissions|CustomDjangoModelPermissions]
    filterset_fields = ['postbac_immersion', 'signed_charter', 'with_convention']

    def __init__(self, *args, **kwargs):
        self.agreed = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.request.GET.get("agreed") is not None:
            self.agreed = self.request.GET.get("agreed", False) in ('true', 'True')

        if self.agreed:
            return HighSchool.agreed.all()

        return HighSchool.objects.all()

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class HighSchoolDetail(generics.RetrieveAPIView):
    """
    High school detail
    """
    serializer_class = HighSchoolSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [IsAuthenticated] # not enough ?
    lookup_fields = ['id']
    queryset = HighSchool.objects.all()


class CourseList(generics.ListCreateAPIView):
    """
    Courses list
    """
    model = Course
    serializer_class = CourseSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [
        IsMasterEstablishmentManagerPermissions | IsEstablishmentManagerPermissions | IsStructureManagerPermissions |
        IsTecPermissions | IsRefLycPermissions | IsSpeakerPermissions | CustomDjangoModelPermissions |
        IsStructureConsultantPermissions
    ]
    filterset_fields = [
        'training', 'structure', 'highschool', 'published', 'training__structures', 'training__highschool'
    ]

    def __init__(self, *args, **kwargs):
        self.message = {}
        self.status = ""
        self.user = None
        self.user_courses = False
        self.user_filter = False
        self.filters = {}

        super().__init__(*args, **kwargs)

    def get_or_create_user(self, request, data):
        """
        When creating or updating a course :
        - if a highschool is present, look for existing ImmersionUsers
        else
        - if a structure is present (not a highschool),
        - & if the structure establishment is linked to an account provider (eg. LDAP),
        - & if data has an 'emails' field (list)
        then search for existing ImmersionUser accounts matching these emails
        or
        look for these accounts in the establishment account provider in order to create new ImmersionUsers
        :param request: request object
        :param data: POST data
        :return: speakers id
        """
        highschool_id = data.get("highschool")
        structure_id = data.get("structure")
        emails = data.get("emails", [])
        establishment = None
        speaker_user = None
        send_creation_msg = False

        if highschool_id:
            filter = {'highschool__id': highschool_id}
        elif structure_id:
            try:
                structure = Structure.objects.get(pk=structure_id)
                establishment = structure.establishment
                filter = {'establishment__id': establishment.id}
            except Structure.DoesNotExist:
                raise
        else:
            # Validation exception will be thrown by the serializer
            return data

        for email in emails:
            try:
                speaker_user = ImmersionUser.objects.get(email__iexact=email.strip(), **filter)
                data.get("speakers", []).append(speaker_user.id)
            except ImmersionUser.DoesNotExist:
                if establishment and establishment.provides_accounts():
                    account_api: AccountAPI = AccountAPI(establishment)
                    ldap_response: Union[bool, List[Any]] = account_api.search_user(
                        search_value=email.strip(),
                        search_attr=account_api.EMAIL_ATTR
                    )
                    if not ldap_response:
                        # not found
                        raise serializers.ValidationError(
                            detail=_("Course '%s' : speaker email '%s' not found in establishment '%s'")
                                % (data.get("label"), email, establishment.code),
                            code=status.HTTP_400_BAD_REQUEST
                        )
                    else:
                        speaker = ldap_response[0]
                        speaker_user = ImmersionUser.objects.create(
                            username=speaker['email'],
                            last_name=speaker['lastname'],
                            first_name=speaker['firstname'],
                            email=speaker['email'],
                            establishment=establishment
                        )
                        send_creation_msg = True
                else:
                    # High school or establishment without account provider : reject
                    raise serializers.ValidationError(
                        detail=_("Course '%s' : speaker '%s' has to be manually created before using it in a course")
                            % (data.get("label"), email),
                        code=status.HTTP_400_BAD_REQUEST
                    )

            if speaker_user:
                try:
                    Group.objects.get(name='INTER').user_set.add(speaker_user)
                except Exception as e:
                    raise serializers.ValidationError(
                        detail=_("Couldn't add group 'INTER' to user '%s' : %s") % (speaker_user.username, e),
                        code=status.HTTP_400_BAD_REQUEST
                    )

                if send_creation_msg:
                    msg = speaker_user.send_message(self.request, 'CPT_CREATE')

                    if msg:
                        data["status"] = "warning"
                        data["msg"] = { speaker_user.email: msg }

                data.get("speakers", []).append(speaker_user.pk)

        return data

    def get_queryset(self):
        self.user = self.request.user
        self.user_courses = self.request.GET.get("user_courses", False) in ('true', 'True')
        self.user_filter = False
        self.filters = {}

        force_user_filter = [
            self.user_courses,
            self.user.is_speaker() and not any([
                self.user.is_master_establishment_manager(),
                self.user.is_establishment_manager(),
                self.user.is_structure_manager(),
                self.user.is_structure_consultant(),
                self.user.is_operator()
            ])
        ]

        if any(force_user_filter):
            self.user_filter = True
            self.filters["speakers__in"] = self.user.linked_users()

        queryset = Course.objects.prefetch_related(
            'training__structures', 'training__highschool', 'training__training_subdomains', 'highschool',
            'structure', 'speakers'
        ).filter(**self.filters).order_by('label')

        if not self.user.is_superuser:
            if self.user.is_structure_manager() or self.user.is_structure_consultant():
                return queryset.filter(structure__in=self.user.structures.all()).order_by('label')
            if self.user.is_establishment_manager() and self.user.establishment:
                return Course.objects.filter(structure__in=self.user.establishment.structures.all()).order_by('label')

        return queryset

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        """
        Look for speaker emails and try to create/add them to serializer data
        """
        if data is not None:
            many = isinstance(data, list)

            if many:
                for course_data in data:
                    try:
                        course_data = self.get_or_create_user(self.request, course_data)
                    except Exception as e:
                        raise
            else:
                try:
                    data = self.get_or_create_user(self.request, data)
                except Exception as e:
                    raise

            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(
                instance=instance,
                many=many,
                partial=partial,
                context={
                    'user_courses': self.user_filter,
                    'request': self.request
                }
            )


class CourseDetail(generics.RetrieveDestroyAPIView):
    """
    Course detail / destroy
    """
    serializer_class = CourseSerializer
    permission_classes = [
        IsMasterEstablishmentManagerPermissions|IsEstablishmentManagerPermissions|
        IsStructureManagerPermissions|IsTecPermissions|IsRefLycPermissions|
        IsSpeakerPermissions|CustomDjangoModelPermissions|IsStructureConsultantPermissions
    ]

    def __init__(self, *args, **kwargs):
        self.user = None
        self.user_courses = False
        self.user_filter = False
        self.filters = {}

        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return Course.objects.prefetch_related('training__structures', 'training__highschool', 'training__training_subdomains', 'highschool',
            'structure', 'speakers').all()

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        """
        Look for speaker emails and try to create/add them to serializer data
        """
        self.user = self.request.user
        self.user_courses = self.request.GET.get("user_courses", False) in ('true', 'True')
        self.user_filter = False
        self.filters = {}

        force_user_filter = [
            self.user_courses,
            self.user.is_speaker() and not any([
                self.user.is_master_establishment_manager(),
                self.user.is_establishment_manager(),
                self.user.is_structure_manager(),
                self.user.is_structure_consultant(),
                self.user.is_operator()
            ])
        ]

        if any(force_user_filter):
            self.user_filter = True
            self.filters["speakers__in"] = self.user.linked_users()

        return super().get_serializer(
            instance=instance,
            many=many,
            partial=partial,
            context={
                'user_courses': self.user_filter,
                'request': self.request
            }
        )

    def delete(self, request, *args, **kwargs):
        course_id = kwargs.get("pk")

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return JsonResponse({"error": _("A valid course must be selected")}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.has_course_rights(course_id):
            return JsonResponse({"error": _("You are not allowed to delete this course")}, status=status.HTTP_403_FORBIDDEN)

        if course.slots.exists():
            return JsonResponse(
                {"error": _("Slots are linked to this course, it can't be deleted")},
                status=status.HTTP_403_FORBIDDEN
            )

        super().delete(request, *args, **kwargs)

        return JsonResponse(
            {"msg": _("Course successfully deleted")},
            status=status.HTTP_200_OK
        )


class SlotList(generics.ListCreateAPIView):
    """
    Courses list
    """
    model = Slot
    serializer_class = SlotSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [CustomDjangoModelPermissions]
    filterset_fields = ['course', 'course_type', 'visit', 'event', 'campus', 'building', 'room',
                        'date', 'start_time', 'end_time', 'speakers', 'published', 'face_to_face']

    def get_queryset(self):
        user = self.request.user
        queryset = Slot.objects.all()
        return queryset

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)


class BuildingList(generics.ListCreateAPIView):
    """
    Buildings list
    """
    serializer_class = BuildingSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['campus', ]
    permission_classes = [CustomDjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        queryset = Building.objects.order_by('label')

        if not user.is_superuser:
            if user.is_structure_manager():
                return queryset.filter(campus__establishment__structures__in=user.structures.all()).distinct()

            if user.is_establishment_manager() and user.establishment:
                return queryset.filter(campus__establishment=user.establishment)

        return queryset

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)
            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)


class GetEstablishment(generics.RetrieveAPIView):
    """
    Single establishment
    """
    serializer_class = EstablishmentSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    queryset = Establishment.objects.all()
    lookup_field = "id"


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingDetail(generics.RetrieveDestroyAPIView):
    """
    Training detail / destroy
    """
    serializer_class = TrainingSerializer

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

        user_visits = self.request.GET.get('user_visits', False) == 'true'

        force_user_filter = [
            user_visits,
            user.is_speaker() and not any([
                user.is_master_establishment_manager(),
                user.is_establishment_manager(),
                user.is_structure_manager(),
                user.is_operator()
            ])
        ]

        if not user.is_superuser:
            if any(force_user_filter):
                queryset = queryset.filter(speakers__in=user.linked_users())
            elif user.is_establishment_manager() and user.establishment:
                queryset = Visit.objects.filter(
                    Q(establishment=user.establishment)|Q(structure__in=user.establishment.structures.all()))\
                    .distinct()
            elif user.is_structure_manager():
                queryset = queryset.filter(structure__in=user.structures.all())

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

        user_events = self.request.GET.get('user_events', False) == 'true'

        force_user_filter = [
            user_events,
            user.is_speaker() and not any([
                user.is_master_establishment_manager(),
                user.is_establishment_manager(),
                user.is_structure_manager(),
                user.is_operator(),
                user.is_structure_consultant(),
            ])
        ]

        if not user.is_superuser:
            if any(force_user_filter):
                queryset = queryset.filter(speakers__in=user.linked_users())
            elif user.is_high_school_manager():
                queryset = queryset.filter(highschool=user.highschool)
            elif user.is_establishment_manager() and user.establishment:
                queryset = OffOfferEvent.objects.filter(
                    Q(establishment=user.establishment)|Q(structure__in=user.establishment.structures.all()))\
                    .distinct()
            elif user.is_structure_manager() or user.is_structure_consultant():
                queryset = queryset.filter(structure__in=user.structures.all())

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
        """
        Return every visitor records with state = 'operator'
        """
        today = timezone.localdate()
        data: Dict[str, Any] = {"msg": "", "data": None}

        operation: str = kwargs.get('operator', '').upper()

        operations = {
            'TO_VALIDATE': 1,
            'VALIDATED': 2,
            'REJECTED': 3,
            'TO_REVALIDATE': 4,
        }

        if not operations.get(operation, None):
            data["msg"] = _("No operator given or wrong operator (to_validate, validated, rejected, to_revalidate)")
            return JsonResponse(data)

        attestations = VisitorRecordDocument.objects \
            .filter(
                Q(validity_date__lt=today) | Q(validity_date__isnull=True),
                archive=False,
                record=OuterRef("pk"),
                requires_validity_date=True,
            ) \
            .exclude(mandatory=False, document='') \
            .order_by() \
            .annotate(count=Func(F('id'), function='Count')) \
            .values('count')


        records = VisitorRecord.objects.filter(
            validation=operations[operation]
        ).annotate(
            user_first_name=F("visitor__first_name"),
            user_last_name=F("visitor__last_name"),
            invalid_dates=Subquery(attestations),
        ).values("id", "user_first_name", "user_last_name", "birth_date", "creation_date", "validation_date",
                 "rejected_date", "invalid_dates")

        data['data'] = list(records)

        return JsonResponse(data)


@method_decorator(groups_required("REF-ETAB-MAITRE", "REF-TEC"), name="dispatch")
class VisitorRecordRejectValidate(View):
    def post(self, request, *args, **kwargs):
        today = timezone.localdate()
        data: Dict[str, Any] = {"msg": "", "data": None}

        # can't be none. No routes allowed for that
        record_id: str = self.kwargs["record_id"]
        operation: str = self.kwargs["operation"]
        validation_value: int = 1
        validation_email_template: str = ""
        delete_attachments: bool = False

        if operation == "validate":
            validation_value = VisitorRecord.STATUSES["VALIDATED"]
            validation_email_template = "CPT_MIN_VALIDE"
            delete_attachments = get_general_setting("DELETE_VISITOR_ATTACHMENTS_AT_VALIDATION")
        elif operation == "reject":
            validation_value = VisitorRecord.STATUSES["REJECTED"]
            validation_email_template = "CPT_MIN_REJET"
        else:
            data["msg"] = _("Error - Bad operation selected. Allowed: validate, reject")
            return JsonResponse(data)

        try:
            record: VisitorRecord = VisitorRecord.objects.prefetch_related('attestation').get(id=record_id)

            # Check documents
            attestations = record.attestation.filter(
                Q(validity_date__lte=today) | Q(validity_date__isnull=True),
                archive=False,
                requires_validity_date=True,
            )

            if validation_value == VisitorRecord.STATUSES["VALIDATED"] and attestations.exists():
                data['msg'] = _("Error: record has missing or invalid attestation dates")
                return JsonResponse(data, safe=False)

            if delete_attachments:
                # Delete only attestations that does not require a validity date
                for attestation in record.attestation.filter(requires_validity_date=False):
                    attestation.delete()

        except VisitorRecord.DoesNotExist:
            data["msg"] = _("Error - record not found: %s") % record_id
            return JsonResponse(data)

        record.validation = validation_value
        record.validation_date = timezone.now() if validation_value == 2 else None
        record.rejected_date = timezone.now() if validation_value == 3 else None
        record.save()
        record.visitor.send_message(self.request, validation_email_template)
        data["data"] = {"record_id": record.id}
        return JsonResponse(data)


@is_ajax_request
@is_post_request
@groups_required("REF-ETAB", "REF-LYC")
def signCharter(request):
    data = {"msg": "", "error": ""}
    charter_sign = get_general_setting('CHARTER_SIGN') # useful somewhere ?
    success = False
    user = request.user

    if user.establishment:
        user.establishment.signed_charter = True
        user.establishment.save()
        success = True
    elif user.highschool:
        user.highschool.signed_charter = True
        user.highschool.save()
        success = True

    if success:
        data["msg"] = _("Charter successfully signed")
    else:
        data["error"] = _("Charter not signed")

    return JsonResponse(data)


class MailingListGlobalView(APIView):
    authentication_classes = [TokenAuthentication, ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        try:
            global_mail = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            response["msg"] = "'GLOBAL_MAILING_LIST' setting does not exist (check admin GeneralSettings values)"
            return JsonResponse(data=response, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        mailing_list = [email for email in ImmersionUser.objects \
              .filter(Q(student_record__isnull=False)
                      | Q(high_school_student_record__validation=2,
                          high_school_student_record__isnull=False) \
                      | Q(visitor_record__validation=2,
                          visitor_record__isnull=False) \
                      ) \
              .values_list('email', flat=True).distinct()]

        response["data"] = {global_mail: mailing_list}
        return JsonResponse(data=response)


class MailingListStructuresView(APIView):
    authentication_classes = [TokenAuthentication, ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}
        for structure in Structure.objects.filter(mailing_list__isnull=False):
            mail = structure.mailing_list
            mailing_list = [email for email in Immersion.objects.filter(cancellation_type__isnull=True).filter(
                    Q(slot__course__structure=structure) \
                    | Q(slot__visit__structure=structure) \
                    | Q(slot__event__structure=structure)
            ).values_list('student__email', flat=True).distinct()]
            response["data"][mail] = mailing_list

        return JsonResponse(data=response)


class MailingListEstablishmentsView(APIView):
    authentication_classes = [TokenAuthentication, ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}
        for establishment in Establishment.objects.filter(mailing_list__isnull=False):
            mailing_list = [email for email in Immersion.objects.filter(cancellation_type__isnull=True).filter(
                Q(slot__course__structure__establishment=establishment) \
                | Q(slot__visit__establishment=establishment) \
                | Q(slot__event__establishment=establishment)
            ).values_list('student__email', flat=True).distinct()]
            response["data"][establishment.mailing_list] = mailing_list

        return JsonResponse(data=response)


class MailingListHighSchoolsView(APIView):
    authentication_classes = [TokenAuthentication, ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}

        for hs in HighSchool.agreed.filter(mailing_list__isnull=False):
            mailing_list = [email for email in Immersion.objects.filter(cancellation_type__isnull=True).filter(
                Q(slot__course__highschool=hs) \
                | Q(slot__visit__highschool=hs) \
                | Q(slot__event__highschool=hs)
            ).values_list('student__email', flat=True).distinct()]
            response["data"][hs.mailing_list] = mailing_list

        return JsonResponse(data=response)


# @method_decorator(groups_required('REF-ETAB', 'REF-STR', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
class MailTemplatePreviewAPI(View):
    def post(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"data": None, "msg": ""}
        pk: int = kwargs["pk"]

        body: str = request.POST.get("body", None)
        context_params: Dict[str, Any] = {
            "user_is": request.POST.get("user_group", "estetudiant"),
            "slot_type": request.POST.get("slot_type", "estuncours"),
            "local_account": request.POST.get("local_user", "true").strip().lower() == "true",
            "remote": request.POST.get("remote", "true").strip().lower() == "true",
        }

        if not body:
            response["msg"] = _("No body for this template provided")
            return JsonResponse(response)

        try:
            template = MailTemplate.objects.get(pk=pk)
        except MailTemplate.DoesNotExist:
            response["msg"] = _("Template #%s can't be found") % pk
            return JsonResponse(response)

        try:
            body = template.parse_var_faker_from_string(
                context_params=context_params,
                user=self.request.user,
                request=self.request,
                body=body
            )
            response["data"] = body
        except TemplateSyntaxError:
            response["msg"] = _("A syntax error has been found in template #%s") % pk

        return JsonResponse(response)


@method_decorator(groups_required('REF-TEC'), name="dispatch")
class AnnualPurgeAPI(View):
    def post(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"ok": False, "msg": "", "time": 0}

        from django.core.management import call_command
        from django.core.management.base import CommandError

        command_time: float = time.thread_time()

        # Step 1 : run annual purge (annual stats included)
        try:
            call_command("annual_purge")
            response["ok"] = True
        except CommandError:
            msg: str = _("""An error occurred while running annual purge command. """
                         """For more details, please contact the administrator.""")
            logger.error(msg)
            response["msg"] = msg

        # Step 2 : clear accounts that are no longer in establishment's LDAPs
        try:
            call_command("delete_account_not_in_ldap")
            response["ok"] = True
        except CommandError:
            msg: str = _("""An error occurred while deleting expired LDAP accounts. """
                         """For more details, please contact the administrator.""")
            logger.error(msg)
            response["msg"] = msg

        response["time"] = round(time.thread_time() - command_time, 3)

        return JsonResponse(response)


@is_ajax_request
@is_post_request
@groups_required("REF-STR")
def ajax_update_structures_notifications(request):

    settings = response = {}
    ids = request.POST.get('ids')
    ids = json.loads(ids) if ids else ''

    structures = request.user.get_authorized_structures().filter(id__in=ids).values_list('id', flat=True)

    settings, created = RefStructuresNotificationsSettings.objects.get_or_create(user=request.user)
    if structures:
        settings.structures.set(ids, clear=True)
    else:
        settings.delete()

    if settings:
        response["msg"] = gettext("Settings updated")
    else:
        response["msg"] = gettext("Nothing to do")

    return JsonResponse(response, safe=False)