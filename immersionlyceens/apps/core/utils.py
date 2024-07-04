"""
Functions that serve the templates and do not really belong to the API
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
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.db.models import (
    BooleanField, Case, CharField, Count, DateField, Exists, ExpressionWrapper, F, Func,
    OuterRef, Q, QuerySet, Subquery, Sum, Value, When,
)
from django.db.models.functions import Coalesce, JSONObject
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import (
    Slot, Training, UniversityYear
)

logger = logging.getLogger(__name__)

@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'INTER', 'REF-TEC', 'CONS-STR')
def slots(request):
    """
    Get slots list according to GET parameters
    :return:
    """
    today = timezone.localdate()
    now = timezone.localtime()

    user = request.user
    response = {'msg': '', 'data': []}

    can_update_attendances = False
    user_filter = False
    user_slots = request.GET.get('user_slots', False) == 'true'
    filters = {}

    try:
        year = UniversityYear.objects.get(active=True)
        can_update_attendances = today <= year.end_date
    except UniversityYear.DoesNotExist:
        pass

    training_id = request.GET.get('training_id')
    structure_id = request.GET.get('structure_id')
    highschool_id = request.GET.get('highschool_id')
    establishment_id = request.GET.get('establishment_id')
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

    force_user_filter = [
        user_slots,
        user.is_speaker() and not any([
            user.is_master_establishment_manager(),
            user.is_establishment_manager(),
            user.is_high_school_manager(),
            user.is_structure_manager(),
            user.is_structure_consultant(),
            user.is_operator()
        ])
    ]

    if any(force_user_filter):
        user_filter = True
        filters["speakers__in"] = user.linked_users()

    if not user_filter:
        if events and not establishment_id and not highschool_id:
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

        elif not events and not establishment_id and not training_id:
            response['msg'] = gettext("Error : a valid training must be selected")
            return JsonResponse(response, safe=False)

    if events:
        filters["course__isnull"] = True

        if establishment_id:
            filters['event__establishment__id'] = establishment_id
            if structure_id is not None:
                filters['event__structure__id'] = structure_id
        elif highschool_id:
            filters['event__highschool__id'] = highschool_id

        user_filter_key = "event__structure__in"
    else:
        filters["event__isnull"] = True

        if establishment_id is not None:
            filters['course__training__structures__establishment__id'] = establishment_id

        if structure_id is not None:
            filters['course__training__structures'] = structure_id

        if training_id is not None:
            filters['course__training__id'] = training_id

        user_filter_key = "course__training__structures__in"

    slots = Slot.objects.prefetch_related(
        'course__training__highschool',
        'course__training__structures__establishment', 'course_type',
        'course__structure__establishment', 'course__highschool',
        'campus', 'building', 'speakers', 'event__event_type',
        'event__establishment', 'event__structure__establishment',
        'event__highschool', 'immersions__cancellation_type',
        'allowed_establishments', 'allowed_highschools',
        'allowed_highschool_levels', 'allowed_post_bachelor_levels',
        'allowed_student_levels', 'allowed_bachelor_types',
        'allowed_bachelor_mentions', 'allowed_bachelor_teachings')\
        .filter(**filters)

    if not user.is_superuser and (user.is_structure_manager() or user.is_structure_consultant()):
        user_filter = {
            user_filter_key: user.structures.all()
        }
        slots = slots.filter(**user_filter)

    if not past_slots:
        slots = slots.filter(
            Q(date__isnull=True)
            | Q(date__gte=today)
            | Q(date=today, end_time__gte=now)
            | Q(place__in=[Slot.FACE_TO_FACE, Slot.OUTSIDE],
                immersions__attendance_status=0,
                immersions__cancellation_type__isnull=True
               )
        ).distinct()

    all_data = []
    allowed_structures = user.get_authorized_structures()
    user_establishment = user.establishment
    user_highschool = user.highschool

    slots = slots.annotate(
        course_label=F('course__label'),
        course_training_label=F('course__training__label'),
        course_type_label=F('course_type__label'),
        course_type_full_label=F('course_type__full_label'),
        event_type_label =F('event__event_type__label'),
        event_label=F('event__label'),
        event_description=F('event__description'),
        campus_label=F('campus__label'),
        building_label=F('building__label'),
        can_update_course_slot=Case(
            When(course__isnull=True, then=False),
            When(
                Q(Value(user.is_master_establishment_manager())) | Q(Value(user.is_operator())),
                then=True
            ),
            When(
                Q(Value(user.is_establishment_manager())) & Q(course__structure__establishment=user_establishment),
                then=True
            ),
            When(
                Q(Value(user.is_structure_manager())) & Q(course__structure__in=allowed_structures),
                then=True
            ),
            default=False
        ),
        can_update_event_slot=Case(
            When(event__isnull=True, then=False),
            When(
                Q(Value(user.is_master_establishment_manager())) | Q(Value(user.is_operator())),
                then=True
            ),
            When(
                Q(Value(user.is_establishment_manager())) & Q(event__establishment=user_establishment),
                then=True
            ),
            When(
                Q(Value(user.is_structure_manager())) & Q(event__structure__in=allowed_structures),
                then=True
            ),
            When(
                Q(Value(user.is_high_school_manager())) & Q(event__highschool=user_highschool),
                then=True
            ),
            default=False
        ),
        can_update_registrations=Case(
            When(
                Q(Value(user.is_master_establishment_manager())) | Q(Value(user.is_operator())),
                then=True
            ),
            When(
                Q(Value(user.is_establishment_manager()))
                & (Q(course__structure__establishment=user_establishment) | Q(event__establishment=user_establishment)),
                then=True
            ),
            When(
                Q(published=True) & (
                    Q(Value(user.is_structure_consultant()),
                      Q(course__structure__in=allowed_structures) | Q(event__structure__in=allowed_structures))
                    | Q(Value(user.is_structure_manager()),
                        Q(course__structure__in=allowed_structures) | Q(event__structure__in=allowed_structures))
                    | Q(Value(user.is_high_school_manager()),
                        Q(course__highschool=user_highschool) | Q(event__highschool=user_highschool))
                ),
                then=True
            ),
            default=False
        ),
        can_update_attendances=Case(
            When(
                Q(Q(ExpressionWrapper(F('can_update_registrations'), output_field=BooleanField()))
                  & Q(Value(can_update_attendances)))
                | (Q(Value(user.is_speaker())) & Q(speakers=user)),
                then=True
            ),
            default=False
        ),
        establishment_code=Coalesce(
            F('course__structure__establishment__code'),
            F('event__establishment__code'),
        ),
        establishment_label=Coalesce(
            F('course__structure__establishment__label'),
            F('event__establishment__label'),
        ),
        establishment_short_label=Coalesce(
            F('course__structure__establishment__short_label'),
            F('event__establishment__short_label'),
        ),
        structure_code=Coalesce(
            F('course__structure__code'),
            F('event__structure__code'),
        ),
        structure_label=Coalesce(
            F('course__structure__label'),
            F('event__structure__label'),
        ),
        structure_establishment_short_label=Coalesce(
            F('course__structure__establishment__short_label'),
            F('event__structure__establishment__short_label'),
        ),
        structure_managed_by_me=Case(
            When(
                Q(course__structure__in=allowed_structures) |
                Q(event__structure__in=allowed_structures),
                then=True
            ),
            default=False
        ),
        highschool_city=Coalesce(
            F('course__highschool__city'),
            F('event__highschool__city'),
        ),
        highschool_label=Coalesce(
            F('course__highschool__label'),
            F('event__highschool__label'),
        ),
        highschool_managed_by_me=Case(
            When(
                Q(Value(user.is_establishment_manager())) | Q(Value(user.is_operator()))
              | (Q(Value(user.is_high_school_manager())) &
                 Q(course__highschool=user_highschool)
               | Q(event__highschool=user_highschool)),
                then=True
            ),
            default=False
        ),
        n_register=Count('immersions', filter=Q(immersions__cancellation_type__isnull=True), distinct=True),
        n_group_register=Count(
            'group_immersions',
            filter=Q(group_immersions__cancellation_type__isnull=True),
            distinct=True
        ),
        n_group_students=Sum(
            'group_immersions__students_count',
            filter=Q(group_immersions__cancellation_type__isnull=True)
        ),
        n_group_guides=Sum(
            'group_immersions__guides_count',
            filter=Q(group_immersions__cancellation_type__isnull=True)
        ),
        is_past=ExpressionWrapper(
            Q(date__lt=today)|Q(date=today, start_time__lt=now),
            output_field=BooleanField()
        ),
        valid_immersions=Count('immersions', filter=Q(immersions__cancellation_type__isnull=True), distinct=True),
        attendances_to_enter=Count(
            'immersions',
            filter=Q(immersions__attendance_status=0, immersions__cancellation_type__isnull=True),
            distinct=True
        ),
        attendances_value=Case(
            When(
                Q(is_past=False),
                then=0
            ),
            When(
                ~Q(Value(can_update_attendances))
                | (Q(Value(events)) & Q(place=Slot.REMOTE)),
                then=Value(2)
            ),
            When(
                Q(Value(can_update_attendances), is_past=True, n_register__gt=0),
                then=Value(1)
            ),
            default=Value(-1)
        ),
        attendances_status=Case(
            When(Q(is_past=False), then=Value(gettext("Future slot"))),
            When(Q(attendances_value=2), then=Value(gettext("University year is over"))),
            When(Q(attendances_value=1), then=Value(gettext("To enter"))),
            default=Value('')
        ),
        speaker_list=Coalesce(
            ArrayAgg(
                JSONObject(
                    last_name=F('speakers__last_name'),
                    first_name=F('speakers__first_name'),
                    email=F('speakers__email')
                ),
                filter=Q(speakers__isnull=False),
                distinct=True),
            Value([]),
        ),
        allowed_establishments_list=Coalesce(
            ArrayAgg(
                F('allowed_establishments__short_label'),
                filter=Q(allowed_establishments__isnull=False),
                distinct=True
            ),
            Value([]),
        ),
        allowed_highschools_list=Coalesce(
            ArrayAgg(
                JSONObject(
                    city=F('allowed_highschools__city'),
                    label=F('allowed_highschools__label')
                ),
                filter=Q(allowed_highschools__isnull=False),
                distinct=True),
            Value([]),
        ),
        allowed_highschool_levels_list=Coalesce(
            ArrayAgg(
                F('allowed_highschool_levels__label'),
                filter=Q(allowed_highschool_levels__isnull=False),
                distinct=True
            ),
            Value([]),
        ),
        allowed_post_bachelor_levels_list=Coalesce(
            ArrayAgg(
                F('allowed_post_bachelor_levels__label'),
                filter=Q(allowed_post_bachelor_levels__isnull=False),
                distinct=True
            ),
            Value([]),
        ),
        allowed_student_levels_list=Coalesce(
            ArrayAgg(
                F('allowed_student_levels__label'),
                filter=Q(allowed_student_levels__isnull=False),
                distinct=True
            ),
            Value([]),
        ),
        allowed_bachelor_types_list=Coalesce(
            ArrayAgg(
                F('allowed_bachelor_types__label'),
                filter=Q(allowed_bachelor_types__isnull=False),
                distinct=True
            ),
            Value([])
        ),
        allowed_bachelor_mentions_list=Coalesce(
            ArrayAgg(
                F('allowed_bachelor_mentions__label'),
                filter=Q(allowed_bachelor_mentions__isnull=False),
                distinct=True
            ),
            Value([])
        ),
        allowed_bachelor_teachings_list=Coalesce(
            ArrayAgg(
                F('allowed_bachelor_teachings__label'),
                filter=Q(allowed_bachelor_teachings__isnull=False),
                distinct=True
            ),
            Value([])
        )
    )\
    .order_by('date', 'start_time')\
    .values(
        'id', 'published', 'can_update_course_slot', 'can_update_event_slot',
        'can_update_registrations', 'course_id', 'course_label', 'course_training_label',
        'course_type_label', 'course_type_full_label', 'establishment_code',
        'establishment_short_label', 'establishment_label', 'structure_code', 'structure_label',
        'structure_managed_by_me', 'structure_establishment_short_label', 'highschool_city',
        'highschool_label', 'highschool_managed_by_me',
        'event_id', 'event_type_label', 'event_label', 'event_description', 'date',
        'start_time', 'end_time', 'campus_label', 'building_label', 'place', 'url',
        'room', 'n_register', 'n_places', 'additional_information', 'attendances_value',
        'attendances_status', 'speaker_list', 'establishments_restrictions', 'levels_restrictions',
        'bachelors_restrictions', 'allowed_establishments_list', 'allowed_highschools_list',
        'allowed_highschool_levels_list', 'allowed_post_bachelor_levels_list',
        'allowed_student_levels_list', 'allowed_bachelor_types_list', 'allowed_bachelor_mentions_list',
        'allowed_bachelor_teachings_list', 'is_past', 'can_update_attendances', 'group_mode',
        'allow_individual_registrations', 'allow_group_registrations', 'n_group_places', 'public_group',
        'n_group_register', 'n_group_students', 'n_group_guides'
    )

    response['data'] = list(slots)

    return JsonResponse(response, safe=False)


def set_session_values(request, pagename=None, values=None):
    """
    Keep selected object id in session
    """
    pagename = request.POST.get('pagename', pagename)
    values = request.POST.get('values', values)

    if not isinstance(values, dict):
        try:
            values = json.loads(values)
        except:
            # bad format
            return JsonResponse({}, safe=False)

    if not pagename:
        return JsonResponse({}, safe=False)

    if not values and pagename in request.session:
        # clear
        for k, v in request.session[pagename].items():
            request.session[pagename][k] = ""

    elif values and isinstance(values, dict):
        if pagename not in request.session:
            request.session[pagename] = {}

        for k, v in values.items():
            request.session[pagename][k] = v

    request.session.modified = True

    return JsonResponse({}, safe=False)

def get_session_value(request, pagename, name):
    """
    Get value of 'name' for page 'pagename' in session
    """
    if all([name, pagename]):
        return request.session.get(pagename, {}).get(name, None)

    return None

@groups_required('REF-STR', 'REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def set_training_quota(request):
    """
    Set training quota
    """
    training_id = request.POST.get('id', None)
    value = request.POST.get('value', '').strip()
    user = request.user
    allowed_structures = user.get_authorized_structures()

    try:
        training = Training.objects.get(pk=int(training_id))
    except Training.DoesNotExist:
        return JsonResponse({'error': _("Training not found")}, safe=False)

    if user.is_high_school_manager() and training.highschool != user.highschool:
        return JsonResponse({'error': _("You are not allowed to set quota for this high school")}, safe=False)

    if any([user.is_structure_manager(), user.is_establishment_manager(), user.is_master_establishment_manager()]):
        if not training.structures.intersection(allowed_structures).exists():
            return JsonResponse({'error': _("You are not allowed to set quota for this training")}, safe=False)

    if value != '':
        try:
            value = int(value)
        except ValueError:
            return JsonResponse({'error': _("Bad quota value (positive integer required)")}, safe=False)

    training.allowed_immersions = value or None
    training.save()

    return JsonResponse({}, safe=False)