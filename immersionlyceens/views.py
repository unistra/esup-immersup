import datetime
import json
import logging
import mimetypes
import os
import sys
from collections import defaultdict
from email.policy import default
from wsgiref.util import FileWrapper

import requests
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.core.files.storage import default_storage
from django.db.models import (BooleanField, Case, CharField, Count, DateField,
                              Exists, ExpressionWrapper, F, Func, OuterRef, Q,
                              QuerySet, Subquery, Value, When, Sum, IntegerField)
from django.db.models.functions import Coalesce, Concat, Greatest, JSONObject
from django.http import (FileResponse, HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, HttpResponseNotFound,
                         StreamingHttpResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views import generic
from storages.backends.s3boto3 import S3Boto3Storage

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, AttestationDocument, Course, Establishment,
    FaqEntry, HighSchool, Immersion, ImmersionGroupRecord, InformationText, Period,
    PublicDocument, PublicType, Slot, Training, TrainingSubdomain,
    UserCourseAlert, ImmersionGroupRecord
)
from immersionlyceens.exceptions import DisplayException
from immersionlyceens.libs.utils import get_general_setting

logger = logging.getLogger(__name__)


def home(request):
    """Homepage view"""

    try:
        welcome_txt = InformationText.objects.get(code="ACCUEIL", active=True).content
    except InformationText.DoesNotExist:
        welcome_txt = ''

    try:
        procedure_txt = InformationText.objects.get(code="INFO_BULLE_PROCEDURE", active=True).content
    except InformationText.DoesNotExist:
        procedure_txt = ''

    try:
        offer_txt = InformationText.objects.get(code="INFO_BULLE_OFFRE", active=True).content
    except InformationText.DoesNotExist:
        offer_txt = ''

    try:
        accomp_txt = InformationText.objects.get(code="INFO_BULLE_ACCOMPAGNEMENT", active=True).content
    except InformationText.DoesNotExist:
        accomp_txt = ''

    try:
        procedure_intro_txt = InformationText.objects.get(code="INTRO_PROCEDURE", active=True).content
    except InformationText.DoesNotExist:
        procedure_intro_txt = ''

    try:
        offer_intro_txt = InformationText.objects.get(code="INTRO_OFFER", active=True).content
    except InformationText.DoesNotExist:
        offer_intro_txt = ''

    try:
        accomp_intro_txt = InformationText.objects.get(code="INTRO_ACCOMPAGNEMENT", active=True).content
    except InformationText.DoesNotExist:
        accomp_intro_txt = ''

    try:
        social_network_url = get_general_setting("SOCIAL_NETWORK_URL")
    except (ValueError, NameError):
        social_network_url = ''

    context = {
        'welcome_txt': welcome_txt,
        'procedure_txt': procedure_txt,
        'offer_txt': offer_txt,
        'accomp_txt': accomp_txt,
        'social_network_url': social_network_url,
        'offer_intro_txt': offer_intro_txt,
        'procedure_intro_txt': procedure_intro_txt,
        'accomp_intro_txt': accomp_intro_txt,
    }
    return render(request, 'home.html', context)


def offer(request):
    """Offer view"""

    try:
        offer_txt = InformationText.objects.get(code="INTRO_OFFER_COURSE", active=True).content
    except InformationText.DoesNotExist:
        offer_txt = ''

    slots_count = 0
    subdomains = TrainingSubdomain.activated.filter(training_domain__active=True).order_by('training_domain', 'label')

    # Count the total of all subdomains
    for sub in subdomains:
        sub_list = sub.subdomain_slots()
        slots_count += sub_list.count()

    context = {
        'subdomains': subdomains,
        'slots_count': slots_count,
        'offer_txt': offer_txt,
    }
    return render(request, 'offer.html', context)


def accompanying(request):
    """Accompanying view"""

    docs = []
    types = PublicType.activated.all()

    try:
        accomp_txt = InformationText.objects.get(code="ACCOMPAGNEMENT", active=True).content
    except InformationText.DoesNotExist:
        accomp_txt = ''

    for type in types:
        data = {
            'type': type.label,
            'docs': AccompanyingDocument.activated.all().filter(public_type__in=[type.pk,]),
        }
        if data['docs']:
            docs.append(data.copy())

    context = {
        'accomp_txt': accomp_txt,
        'accomp_docs': docs,
    }
    return render(request, 'accompanying.html', context)


def procedure(request):
    """Procedure view"""

    try:
        procedure_txt = InformationText.objects.get(code="PROCEDURE_LYCEEA", active=True).content
    except InformationText.DoesNotExist:
        procedure_txt = ''

    try:
        procedure_group_txt = InformationText.objects.get(code="PROCEDURE_LYCEEB", active=True).content
    except InformationText.DoesNotExist:
        procedure_group_txt = ''

    highschools = HighSchool.agreed.values("city", "label", "email")
    establishments = Establishment.activated.all().values('city', 'label', 'email')
    immersion_highschools = HighSchool.immersions_proposal\
            .filter(signed_charter=True)\
            .values('city', 'label', 'email')

    immersion_establishments = establishments.union(immersion_highschools)

    context = {
        'procedure_txt': procedure_txt,
        'procedure_group_txt': procedure_group_txt,
        'highschools': json.dumps(list(highschools)),
        'immersion_establishments': json.dumps(list(immersion_establishments))
    }
    return render(request, 'procedure.html', context)


def file_response(*args, **kwargs):
    try:
        return FileResponse(*args, **kwargs)
    except OSError:
        raise HttpResponseNotFound()


def serve_accompanying_document(request, accompanying_document_id):
    """Serve accompanying documents files"""
    try:
        doc = get_object_or_404(AccompanyingDocument, pk=accompanying_document_id)
        if isinstance(default_storage, S3Boto3Storage):
            response = requests.get(doc.document.url, stream=True)
            return file_response(response.raw, as_attachment=True, content_type=response.headers['content-type'])
        else:
            return redirect(doc.document.url)

    except Exception:
        return HttpResponseNotFound()


def serve_public_document(request, public_document_id):
    """Serve public documents files"""
    try:
        doc = get_object_or_404(PublicDocument, pk=public_document_id)
        if isinstance(default_storage, S3Boto3Storage):
            response = requests.get(doc.document.url, stream=True)
            return file_response(response.raw, as_attachment=True, content_type=response.headers['content-type'])
        else:
            return redirect(doc.document.url)

    except Exception:
        return HttpResponseNotFound()


def serve_attestation_document(request, attestation_document_id):
    """Serve attestation documents files"""
    try:
        doc = get_object_or_404(AttestationDocument, pk=attestation_document_id)
        if isinstance(default_storage, S3Boto3Storage):
            response = requests.get(doc.template.url, stream=True)
            return file_response(response.raw, as_attachment=True, content_type=response.headers['content-type'])
        else:
            return redirect(doc.template.url)

    except Exception:
        return HttpResponseNotFound()


def serve_immersion_group_document(request, immersion_group_id):
    """Serve attestation documents files"""
    try:
        immersion = get_object_or_404(ImmersionGroupRecord, pk=immersion_group_id)
        if isinstance(default_storage, S3Boto3Storage):
            response = requests.get(immersion.file.url, stream=True)
            return file_response(response.raw, as_attachment=True, content_type=response.headers['content-type'])
        else:
            return redirect(immersion.file.url)

    except Exception:
        return HttpResponseNotFound()


def data_for_context(data, data_dict, slot):

    training_id = slot['training_id']
    etab_label = slot['establishment_label'] if slot['course_structure_label'] else slot['training_highschool_label']
    course_id = slot['course_id']

    training_info = {
        'id': slot['training_id'],
        'label': slot['training_label'],
        'url': slot['training_url'],
        'highschool': slot['training_highschool'],
        'highschool_badge_html_color': slot['training_highschool_badge_html_color'],
        'highschool_label': slot['training_highschool_label'],
        'highschool_city': slot['training_highschool_city'],
    }

    etab_info = {
        'label': slot['establishment_label'],
        'badge_html_color': slot['establishment_badge_html_color'],
    }

    course_info = {
        'id': slot['course_id'],
        'label': slot['course_label'],
        'url': slot['course_url'],
        'is_displayed': slot['course_is_displayed'],
    }

    if 'info' not in data[training_id]:
        data[training_id]['info'] = training_info

    if 'info' not in data[training_id][etab_label]:
        data[training_id][etab_label]['info'] = etab_info

    if 'info' not in data[training_id][etab_label][course_id]:
        data[training_id][etab_label][course_id]['info'] = course_info

    if 'slots' not in data[training_id][etab_label][course_id]:
        data[training_id][etab_label][course_id]['slots'] = []

    data[training_id][etab_label][course_id]['slots'].append(slot)

    for training_id, etab_dict in data.items():
        etabs = {}
        for etab_label, course_dict in etab_dict.items():
            etabs[etab_label] = dict(course_dict)
        data_dict[training_id] = etabs


def offer_subdomain(request, subdomain_id):
    """Subdomain offer view"""
    student = None
    record = None
    remaining_regs_count = None
    course_alerts = None
    open_training_id, open_course_id = None, None

    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)

    now = timezone.now()
    today = timezone.localdate()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    data_dict = {}

    if not request.user.is_anonymous and (
            request.user.is_high_school_student() or
            request.user.is_student() or
            request.user.is_visitor()
    ):
        student = request.user

        # Get student record yet
        if student.is_high_school_student():
            record = student.get_high_school_student_record()
        elif student.is_student():
            record = student.get_student_record()
        elif student.is_visitor():
            record = student.get_visitor_record()

        # Remaining registrations for each period
        # remaining_regs_count = { period.pk : nb_registrations_left }
        remaining_regs_count = student.remaining_registrations_count()
        course_alerts = UserCourseAlert.objects.filter(
            email=request.user.email, email_sent=False
        ).values_list("course_id", flat=True)

    total_reserved_count = Count(
        'immersions',
        filter=Q(immersions__cancellation_type__isnull=True)
    )

    # TODO: poc for now maybe refactor dirty code in a model method !!!! Update: The code changed, now relying on the database but the comment may still be interesting
    slots_list = (Slot.objects
        .prefetch_related(
            'course__training__highschool',
            'course__training__structures__establishment',
            'course__structure__establishment',

            'pk',
            'id',
            'period',
            'date',
            'start_time',
            'end_time',
            'course_type',
            'speakers',
            'establishments_restrictions',
            'allowed_establishments',
            'allowed_highschools',
            'allowed_highschool_levels',
            'allowed_post_bachelor_levels',
            'allowed_student_levels',
            'allowed_bachelor_types',
            'allowed_bachelor_mentions',
            'allowed_bachelor_teachings',
            'campus',
            'building'
        )
        .filter(
            course__training__training_subdomains=subdomain_id,
            published=True,
            date__gte=today,
            allow_individual_registrations=True
        )
        .annotate(
            training=F('course__training'),
            training_id=F('course__training__id'),
            training_label=F('course__training__label'),
            training_url=F('course__training__url'),
            training_highschool=F('course__training__highschool'),
            training_highschool_badge_html_color=F('course__training__highschool__badge_html_color'),
            training_highschool_label=F('course__training__highschool__label'),
            training_highschool_city=F('course__training__highschool__city'),
            establishment_label=Coalesce(
                F('course__training__structures__establishment__label'),
                F('course__structure__establishment__label'),
            ),
            establishment_badge_html_color=Coalesce(
                F('course__training__structures__establishment__badge_html_color'),
                F('course__structure__establishment__badge_html_color'),
            ),
            course_label=F('course__label'),
            course_url=F('course__url'),
            course_structure_label=F('course__structure__label'),
            course_type_label=F('course_type__label'),

            period_pk=F('period__pk'),
            speaker_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        last_name=F('speakers__last_name'),
                        first_name=F('speakers__first_name'),
                        email=F('speakers__email'),
                    ),
                    filter=Q(speakers__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_establishments_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        city=F('allowed_establishments__city'),
                        label=F('allowed_establishments__label')
                    ),
                    filter=Q(allowed_establishments__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschools_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        id=F('allowed_highschools__id'),
                        city=F('allowed_highschools__city'),
                        label=F('allowed_highschools__label')
                    ),
                    filter=Q(allowed_highschools__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschool_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_highschool_levels__label'),
                    filter=Q(allowed_highschool_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_post_bachelor_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_post_bachelor_levels__label'),
                    filter=Q(allowed_post_bachelor_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_student_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_student_levels__label'), filter=Q(allowed_student_levels__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_types_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_types__label'), filter=Q(allowed_bachelor_types__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_mentions_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_mentions__label'),
                    filter=Q(allowed_bachelor_mentions__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_bachelor_teachings_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_teachings__label'),
                    filter=Q(allowed_bachelor_teachings__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            passed_registration_limit_date=Case(
                When(
                    registration_limit_date__isnull=False,
                    registration_limit_date__lt=now,
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            ),
            passed_cancellation_limit_date=Case(
                When(
                    cancellation_limit_date__isnull=False,
                    cancellation_limit_date__lt=now,
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            ),
            campus_label=F('campus__label'),
            building_label=F('building__label'),
            building_url=F('building__url'),

            total_reserved=total_reserved_count,
            calculated_seats=F('n_places') - F('total_reserved'),
            final_available_seats=Case(
                When(calculated_seats__lt=0, then=Value(0)),
                default=F('calculated_seats'),
                output_field=IntegerField()
            ),

            course_is_displayed=Case(
                When(
                    Q(course__published=True) &
                    Q(course__start_date__isnull=True) | Q(course__start_date__lte=now) &
                    Q(course__end_date__isnull=True) | Q(course__end_date__gte=now),
                    then = True
                ),
                default = False,
                output_field = BooleanField()
            ),
        )
        .order_by('date', 'start_time', 'end_time')
        .values(
            'training',
            'training_id',
            'training_label',
            'training_url',
            'training_highschool',
            'training_highschool_badge_html_color',
            'training_highschool_label',
            'training_highschool_city',
            'establishment_label',
            'establishment_badge_html_color',

            'course_id',
            'course_label',
            'course_url',
            'course_structure_label',

            'pk',
            'id',
            'period_pk',
            'date',
            'start_time',
            'end_time',
            'course_type_label',

            'speaker_list',
            'establishments_restrictions',
            'levels_restrictions',
            'bachelors_restrictions',

            'allowed_establishments_list',
            'allowed_highschools_list',
            'allowed_highschool_levels_list',
            'allowed_post_bachelor_levels_list',
            'allowed_student_levels_list',
            'allowed_bachelor_types_list',
            'allowed_bachelor_mentions_list',
            'allowed_bachelor_teachings_list',

            'passed_registration_limit_date',
            'passed_cancellation_limit_date',
            'registration_limit_date',

            'campus',
            'campus_label',

            'building',
            'building_label',
            'building_url',
            'room',
            'additional_information',

            'final_available_seats',
            'n_places',

            'course_is_displayed',
        )
    )

    # If the current user is a student, check whether he can register
    if student and record and remaining_regs_count:
        for slot in slots_list:

            slot['already_registered'] = False
            slot['can_register'] = False
            slot['cancelled'] = False
            slot['opening_soon'] = False

            # get slot period (for dates)
            try:
                period = Period.from_date(pk=slot['period_pk'], date=slot['date'])
            except Period.DoesNotExist as e:
                logger.exception(f"Period does not exist : {e}")
                raise
            except Period.MultipleObjectsReturned as e:
                logger.exception(f"Multiple period returned : {e}")
                raise

            # Already registered / cancelled ?
            for immersion in student.immersions.all():
                if immersion.slot == slot:
                    slot['already_registered'] = True
                    slot['cancelled'] = immersion.cancellation_type is not None

            # Can register ?
            # not registered + free seats + dates in range + cancelled to register again
            if not slot['already_registered'] or slot['cancelled']:
                can_register, _obj = student.can_register_slot(slot)

                if slot['final_available_seats'] > 0 and can_register:
                    immersion_end_datetime = datetime.datetime.combine(
                        period.immersion_end_date + datetime.timedelta(days=1),
                        datetime.time(0, 0)
                    ).replace(tzinfo=now.tzinfo)

                    if period.registration_start_date <= now <= immersion_end_datetime \
                            and slot['registration_limit_date'] >= now:
                        slot['can_register'] = True
                    elif now < slot['registration_limit_date']:
                        slot['opening_soon'] = True

            data_for_context(data, data_dict, slot)

    else:
        for slot in slots_list:
            slot['already_registered'] = False
            slot['can_register'] = False
            slot['cancelled'] = False

            data_for_context(data, data_dict, slot)

    data_dict["slot_list"] = slots_list

    data_dict['alert'] = (not slots_list or all(slot['final_available_seats'] == 0 for slot in slots_list))

    # For navigation
    slot_id = request.session.get("last_registration_slot_id", None)
    if slot_id:
        try:
            slot = Slot.objects.prefetch_related("course__training").get(pk=slot_id)
            # TODO: Check for events !!!!
            if slot.course:
                open_training_id = slot.training_id
                open_course_id = slot.course_id
        except Slot.DoesNotExist:
            pass

    # clean for next reload
    request.session.pop("last_registration_slot_id", None)

    context = {
        'subdomain': subdomain,
        'data': data_dict,
        'today': today,
        'student': student,
        'open_training_id': open_training_id,
        'open_course_id': open_course_id,
        'course_alerts': course_alerts,
        'is_anonymous': request.user.is_anonymous,
    }

    return render(request, 'offer_subdomains.html', context)

def data_for_context_event(data, data_dict, event):

    event_type_id = event['event_type_id']
    etab_label = event['establishment_label']
    event_id = event['event_id']

    event_type_info = {
        'id': event['event_type_id'],
        'label': event['event_type_label'],
    }

    etab_info = {
        'label': event['establishment_label'],
    }

    event_info = {
        'id': event['event_id'],
        'label': event['event_label'],
        'is_displayed': event['event_is_displayed'],
    }

    if 'info' not in data[event_type_id]:
        data[event_type_id]['info'] = event_type_info

    if 'info' not in data[event_type_id][etab_label]:
        data[event_type_id][etab_label]['info'] = etab_info

    if 'info' not in data[event_type_id][etab_label][event_id]:
        data[event_type_id][etab_label][event_id]['info'] = event_info

    if 'slots' not in data[event_type_id][etab_label][event_id]:
        data[event_type_id][etab_label][event_id]['slots'] = []

    data[event_type_id][etab_label][event_id]['slots'].append(event)

    for event_type_id, etab_dict in data.items():
        etabs = {}
        for etab_label, event_dict in etab_dict.items():
            etabs[etab_label] = dict(event_dict)
        data_dict[event_type_id] = etabs


def offer_off_offer_events(request):
    """ Events Offer view """

    filters = {}
    student = None
    record = None

    now = timezone.now()
    today = timezone.localdate()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    data_dict = {}

    if not request.user.is_anonymous \
        and (request.user.is_high_school_student() or request.user.is_student() or request.user.is_visitor()):

        student = request.user

        # Get student/highschool/visitor record
        if student.is_high_school_student():
            record = student.get_high_school_student_record()
        elif student.is_student():
            record = student.get_student_record()
        elif student.is_visitor():
            #TODO: really needed ?
            record = student.get_visitor_record()

    try:
        events_txt = InformationText.objects.get(code="INTRO_EVENEMENTHO", active=True).content
    except InformationText.DoesNotExist:
        events_txt = ''

    # Published event only & no course
    filters["course__isnull"] = True
    filters["event__published"] = True
    filters["published"] = True
    filters["allow_individual_registrations"] = True
    filters["date__gte"] = today

    group_registered_persons_query = (
        ImmersionGroupRecord.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True)
        .annotate(group_registered_persons=(F('students_count') + F('guides_count')))
        .annotate(total=Coalesce(Func('group_registered_persons', function='SUM'), 0))
        .values('total')
    )

    total_reserved_count = Count(
        'immersions',
        filter=Q(immersions__cancellation_type__isnull=True)
    )

    total_registered_groups_count = Count(
        'group_immersions',
        filter=Q(group_immersions__cancellation_type__isnull=True)
    )

    events = (Slot.objects
        .prefetch_related(
            'event__highschool',
            'event__establishment',
            'event__structure__establishment',
            'event__event_type__label',
            'period__registration_start_date',
            'immersions',
            
            'pk',
            'date',
            'start_time',
            'end_time',
            'speakers',
            'establishments_restrictions',
            'allow_group_registrations',
            'allowed_establishments',
            'allowed_highschools',
            'allowed_highschool_levels',
            'allowed_post_bachelor_levels',
            'allowed_student_levels',
            'allowed_bachelor_types',
            'allowed_bachelor_mentions',
            'allowed_bachelor_teachings',
            'campus',
            'building',
        )
        .filter(
            **filters
        ).filter(
            Q(event__start_date__lte=today) |
            Q(event__start_date__isnull=True)
        )
        .annotate(
            event_structure=F('event__structure'),
            establishment_label=Coalesce(
                F('event__establishment__label'),
                F('event__structure__establishment__label'),
            ),
            establishment_badge_html_color=Coalesce(
                F('event__establishment__badge_html_color'),
                F('event__structure__establishment__badge_html_color'),
            ),
            event_label=F('event__label'),
            event_structure_label=F('event__structure__label'),
            event_type=F('event__event_type'),
            event_type_id=F('event__event_type__id'),
            event_type_label=F('event__event_type__label'),

            speaker_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        last_name=F('speakers__last_name'),
                        first_name=F('speakers__first_name'),
                        email=F('speakers__email'),
                    ),
                    filter=Q(speakers__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_establishments_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        city=F('allowed_establishments__city'),
                        label=F('allowed_establishments__label')
                    ),
                    filter=Q(allowed_establishments__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschools_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        id=F('allowed_highschools__id'),
                        city=F('allowed_highschools__city'),
                        label=F('allowed_highschools__label')
                    ),
                    filter=Q(allowed_highschools__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschool_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_highschool_levels__label'),
                    filter=Q(allowed_highschool_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_post_bachelor_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_post_bachelor_levels__label'),
                    filter=Q(allowed_post_bachelor_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_student_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_student_levels__label'), filter=Q(allowed_student_levels__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_types_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_types__label'), filter=Q(allowed_bachelor_types__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_mentions_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_mentions__label'),
                    filter=Q(allowed_bachelor_mentions__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_bachelor_teachings_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_teachings__label'),
                    filter=Q(allowed_bachelor_teachings__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),

            passed_registration_limit_date=Case(
                When(
                    registration_limit_date__isnull=False,
                    registration_limit_date__lt=now,
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            ),

            campus_label=F('campus__label'),
            building_label=F('building__label'),
            building_url=F('building__url'),

            group_registered_persons=Subquery(group_registered_persons_query),
            total_registered_groups=total_registered_groups_count,
            period_registration_start_date=F('period__registration_start_date'),
            valid_registration_start_date=Q(period__registration_start_date__lte=now),
            valid_registration_date=Case(
                When(period__registration_end_date_policy=Period.REGISTRATION_END_DATE_PERIOD,
                     then=Q(period__registration_start_date__lte=now,
                            period__registration_end_date__gte=now)
                     ),
                default=Q(
                    period__registration_start_date__lte=now,
                    registration_limit_date__gte=now
                )
            ),

            total_reserved=total_reserved_count,
            calculated_seats=F('n_places') - F('total_reserved'),
            final_available_seats=Case(
                When(calculated_seats__lt=0, then=Value(0)),
                default=F('calculated_seats'),
                output_field=IntegerField()
            ),

            event_is_displayed=Case(
                When(
                    Q(event__published=True) &
                    Q(event__start_date__isnull=True) | Q(event__start_date__lte=now) &
                    Q(event__end_date__isnull=True) | Q(event__end_date__gte=now),
                    then=True
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
        )
        .order_by('event__establishment__label',
            'event__highschool__label',
            'event__label',
            'date',
            'start_time'
        )
        .values(
            'event_structure',
            'establishment_label',
            'establishment_badge_html_color',

            'event_id',
            'event_label',
            'event_structure_label',

            'pk',
            'date',
            'start_time',
            'end_time',
            'event_type',
            'event_type_id',
            'event_type_label',

            'speaker_list',
            'establishments_restrictions',
            'levels_restrictions',
            'bachelors_restrictions',

            'allow_group_registrations',
            'allow_individual_registrations',
            'allowed_establishments_list',
            'allowed_highschools_list',
            'allowed_highschool_levels_list',
            'allowed_post_bachelor_levels_list',
            'allowed_student_levels_list',
            'allowed_bachelor_types_list',
            'allowed_bachelor_mentions_list',
            'allowed_bachelor_teachings_list',

            'passed_registration_limit_date',
            'registration_limit_date',

            'campus',
            'campus_label',

            'building',
            'building_label',
            'building_url',
            'room',
            'additional_information',

            'n_group_places',
            'group_registered_persons',
            'period_registration_start_date',

            'valid_registration_start_date',
            'valid_registration_date',
            'group_mode',

            'final_available_seats',
            'n_places',

            'event_is_displayed',
        )
    )

    # TODO: poc for now maybe refactor dirty code in a model method !!!!

    # If the current user is a student/highschool student, check whether he can register
    if student and record:
        for event in events:

            event['cancelled'] = False
            event['can_register'] = False
            event['already_registered'] = False
            event['opening_soon'] = False

            # Already registered / cancelled ?
            for immersion in student.immersions.all():
                if immersion.slot.pk == event['pk']:
                    event['already_registered'] = True
                    event['cancelled'] = immersion.cancellation_type is not None

            # Can register ?
            # not registered + free seats + dates in range + cancelled to register again
            if not event['already_registered'] or event['cancelled']:
                can_register, _obj = student.can_register_slot(event)

                try:
                    period = Period.from_date(pk=event['period_pk'], date=event['date'])
                except Period.DoesNotExist as e:
                    logger.exception(f"Period does not exist : {e}")
                    raise

                if event['final_available_seats'] > 0 and can_register:
                    if period.registration_start_date.date() <= today <= period.immersion_end_date \
                            and event['registration_limit_date'] >= now:
                        event['can_register'] = True
                    elif now < event['registration_limit_date']:
                        event['opening_soon'] = True

            data_for_context_event(data, data_dict, event)

    else:
        for event in events:
            event['cancelled'] = False
            event['can_register'] = False
            event['already_registered'] = False

            data_for_context_event(data, data_dict, event)

    data_dict["events"] = events

    events_count = events.count()

    context = {
        'events_count': events_count,
        'events_txt': events_txt,
        'data': data_dict,
    }

    return render(request, 'offer_off_offer_events.html', context)


def charter_not_signed(request):
    """
    Charter not signed static page
    """
    context = {
    }
    return render(request, 'charter_not_signed.html', context)


def error_500(request, *args, **kwargs):
    context = {}
    _, exc, _ = sys.exc_info()
    display = getattr(exc, "display", False)

    if display:
        context["error"] = str(exc)

    return render(request, '500.html', context, status=500)

def faq(request):
    """FAQ view"""

    entries = FaqEntry.activated.all().order_by('order')

    context = {
        'entries': entries,
    }

    return render(request, 'faq.html', context)


def host_establishments(request):
    """Host establishments view"""

    establishments = Establishment.activated.filter(is_host_establishment=True).values('city', 'label', 'email')
    immersion_highschools = HighSchool.immersions_proposal\
            .filter(signed_charter=True)\
            .values('city', 'label', 'email')

    immersion_establishments = establishments.union(immersion_highschools)

    context = {
        'immersion_establishments': json.dumps(list(immersion_establishments))
    }
    return render(request, 'establishments_under_agreement.html', context)


def highschools(request):
    """ Highschools public view"""

    affiliated_highschools = HighSchool.objects.filter(
        active=True,
        with_convention=True,
        allow_individual_immersions=True
    ).values("city", "label", "email", "uses_student_federation")

    try:
        affiliated_highschools_intro_txt = InformationText.objects.get(
            code="INTRO_LYCEES_CONVENTIONNES",
            active=True
        ).content
    except InformationText.DoesNotExist:
        affiliated_highschools_intro_txt = ''

    try:
        not_affiliated_highschools_intro_txt = InformationText.objects.get(
            code="INTRO_LYCEES_NON_CONVENTIONNES",
            active=True
        ).content
    except InformationText.DoesNotExist:
        not_affiliated_highschools_intro_txt = ''

    not_affiliated_highschools = HighSchool.objects.filter(
        active=True,
        with_convention=False,
        allow_individual_immersions=True
    ).values("city", "label", "email", "uses_student_federation")

    context = {
        'affiliated_highschools': json.dumps(list(affiliated_highschools)),
        'affiliated_highschools_intro_txt': affiliated_highschools_intro_txt,
        'not_affiliated_highschools': json.dumps(list(not_affiliated_highschools)),
        'not_affiliated_highschools_intro_txt': not_affiliated_highschools_intro_txt,
    }

    return render(request, 'highschools.html', context)


def search_slots(request):

    try:
        intro_offer_search = InformationText.objects.get(
            code="INTRO_OFFER_SEARCH", active=True
        ).content
    except InformationText.DoesNotExist:
        intro_offer_search = ""

    context = {
        "intro_offer_search": intro_offer_search,
    }
    return render(request, "search_slots.html", context)


def cohort_offer(request):
    """Cohort offer view"""

    filters = {}
    user = request.user
    is_anonymous = request.user.is_anonymous

    try:
        cohort_offer_txt = InformationText.objects.get(code="INTRO_OFFER_COHORT", active=True).content
    except InformationText.DoesNotExist:
        cohort_offer_txt = ''

    slots_count = 0
    subdomains = TrainingSubdomain.activated.filter(training_domain__active=True).order_by('training_domain', 'label')

    if is_anonymous or not user.is_high_school_manager():
        # Count the total of all subdomains
        for sub in subdomains:
            sub_list = sub.group_public_subdomain_slots()
            slots_count += sub_list.count()
    else :
        for sub in subdomains:
            sub_list = sub.group_public_and_private_subdomain_slots()
            slots_count += sub_list.count()

    now = timezone.now()
    today = timezone.now().date()
    # Published event only & no course

    group_registered_persons_query = ImmersionGroupRecord.objects.filter(
        slot=OuterRef("pk"), cancellation_type__isnull=True
    )\
    .annotate(group_registered_persons=(F('students_count') + F('guides_count')))\
    .annotate(total=Coalesce(Func('group_registered_persons', function='SUM'),0))\
    .values('total')

    filters["course__isnull"] = True
    filters["event__published"] = True
    filters["published"] = True
    filters["allow_group_registrations"] = True
    filters["date__gte"] = today

    if is_anonymous or not request.user.is_high_school_manager():
        filters["public_group"] = True

    events = (
        Slot.objects.prefetch_related(
            'event__establishment', 'event__structure', 'event__highschool', 'speakers', 'immersions'
        )
        .filter(**filters)
        .annotate(
            group_registered_persons=Subquery(group_registered_persons_query),
            valid_registration_start_date=Q(period__registration_start_date__lte=now),
            valid_registration_date=Case(
              When(period__registration_end_date_policy=Period.REGISTRATION_END_DATE_PERIOD,
                then=Q(period__registration_start_date__lte=now,
                        period__registration_end_date__gte=now)
              ),
              default=Q(
                  period__registration_start_date__lte=now,
                  registration_limit_date__gte=now
              )
            )
        )
        .order_by('event__establishment__label', 'event__highschool__label', 'event__label', 'date', 'start_time')
    )

    context = {
        'subdomains': subdomains,
        'slots_count': slots_count,
        'cohort_offer_txt': cohort_offer_txt,
        'events_count': events.count(),
        'events': events,
        'highschool': (
            request.user.highschool if request.user.is_authenticated and request.user.is_high_school_manager() else None
        ),
    }
    return render(request, 'cohort_offer.html', context)


def cohort_offer_subdomain(request, subdomain_id):
    """Cohort subdomain offer view"""

    user = request.user
    public_groups_filter = {}

    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)

    now = timezone.now()
    today = timezone.localdate()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    data_dict = {}

    if user.is_anonymous or not user.is_high_school_manager():
        public_groups_filter = {"public_group": True}

    group_registered_persons_query = (
        ImmersionGroupRecord.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True)
        .annotate(group_registered_persons=(F('students_count') + F('guides_count')))
        .annotate(total=Coalesce(Func('group_registered_persons', function='SUM'), 0))
        .values('total')
    )

    total_registered_groups_count = Count(
        'group_immersions',
        filter=Q(group_immersions__cancellation_type__isnull=True)
    )

    slots_list = (Slot.objects
        .prefetch_related(
            'course__training__highschool',
            'course__training__structures__establishment',
            'course__structure__establishment',
            'period__registration_start_date',

            'pk',
            'id',
            'date',
            'start_time',
            'end_time',
            'course_type',
            'speakers',
            'establishments_restrictions',
            'allow_group_registrations',
            'allowed_establishments',
            'allowed_highschools',
            'allowed_highschool_levels',
            'allowed_post_bachelor_levels',
            'allowed_student_levels',
            'allowed_bachelor_types',
            'allowed_bachelor_mentions',
            'allowed_bachelor_teachings',
            'campus',
            'building'
        )
        .filter(
            course__training__training_subdomains=subdomain_id,
            published=True,
            date__gte=today,
            allow_group_registrations=True,
            **public_groups_filter
        )
        .annotate(
            training=F('course__training'),
            training_id=F('course__training__id'),
            training_label=F('course__training__label'),
            training_url=F('course__training__url'),
            training_highschool=F('course__training__highschool'),
            training_highschool_badge_html_color=F('course__training__highschool__badge_html_color'),
            training_highschool_label=F('course__training__highschool__label'),
            training_highschool_city=F('course__training__highschool__city'),
            establishment_label=Coalesce(
                F('course__training__structures__establishment__label'),
                F('course__structure__establishment__label'),
            ),
            establishment_badge_html_color=Coalesce(
                F('course__training__structures__establishment__badge_html_color'),
                F('course__structure__establishment__badge_html_color'),
            ),
            course_label=F('course__label'),
            course_url=F('course__url'),
            course_structure_label=F('course__structure__label'),
            course_type_label=F('course_type__label'),

            speaker_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        last_name=F('speakers__last_name'),
                        first_name=F('speakers__first_name'),
                        email=F('speakers__email'),
                    ),
                    filter=Q(speakers__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_establishments_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        city=F('allowed_establishments__city'),
                        label=F('allowed_establishments__label')
                    ),
                    filter=Q(allowed_establishments__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschools_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        id=F('allowed_highschools__id'),
                        city=F('allowed_highschools__city'),
                        label=F('allowed_highschools__label')
                    ),
                    filter=Q(allowed_highschools__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschool_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_highschool_levels__label'),
                    filter=Q(allowed_highschool_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_post_bachelor_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_post_bachelor_levels__label'),
                    filter=Q(allowed_post_bachelor_levels__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_student_levels_list=Coalesce(
                ArrayAgg(
                    F('allowed_student_levels__label'), filter=Q(allowed_student_levels__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_types_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_types__label'), filter=Q(allowed_bachelor_types__isnull=False), distinct=True
                ),
                Value([]),
            ),
            allowed_bachelor_mentions_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_mentions__label'),
                    filter=Q(allowed_bachelor_mentions__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_bachelor_teachings_list=Coalesce(
                ArrayAgg(
                    F('allowed_bachelor_teachings__label'),
                    filter=Q(allowed_bachelor_teachings__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            passed_registration_limit_date=Case(
                When(
                    registration_limit_date__isnull=False,
                    registration_limit_date__lt=now,
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            ),
            campus_label=F('campus__label'),
            building_label=F('building__label'),
            building_url=F('building__url'),

            group_registered_persons=Subquery(group_registered_persons_query),
            total_registered_groups=total_registered_groups_count,
            period_registration_start_date=F('period__registration_start_date'),
            valid_registration_start_date=Q(period__registration_start_date__lte=now),
            valid_registration_date=Case(
                When(period__registration_end_date_policy=Period.REGISTRATION_END_DATE_PERIOD,
                     then=Q(period__registration_start_date__lte=now,
                            period__registration_end_date__gte=now)
                     ),
                default=Q(
                    period__registration_start_date__lte=now,
                    registration_limit_date__gte=now
                )
            ),

            course_is_displayed=Case(
                When(
                    Q(course__published=True) &
                    Q(course__start_date__isnull=True) | Q(course__start_date__lte=now) &
                    Q(course__end_date__isnull=True) | Q(course__end_date__gte=now),
                    then=True
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
        )
        .order_by('date', 'start_time', 'end_time')
        .values(
            'training',
            'training_id',
            'training_label',
            'training_url',
            'training_highschool',
            'training_highschool_badge_html_color',
            'training_highschool_label',
            'training_highschool_city',
            'establishment_label',
            'establishment_badge_html_color',

            'course_id',
            'course_label',
            'course_url',
            'course_structure_label',

            'pk',
            'id',
            'date',
            'start_time',
            'end_time',
            'course_type_label',

            'speaker_list',
            'establishments_restrictions',
            'levels_restrictions',
            'bachelors_restrictions',

            'allow_group_registrations',
            'allowed_establishments_list',
            'allowed_highschools_list',
            'allowed_highschool_levels_list',
            'allowed_post_bachelor_levels_list',
            'allowed_student_levels_list',
            'allowed_bachelor_types_list',
            'allowed_bachelor_mentions_list',
            'allowed_bachelor_teachings_list',

            'passed_registration_limit_date',
            'registration_limit_date',

            'campus',
            'campus_label',

            'building',
            'building_label',
            'building_url',
            'room',
            'additional_information',

            'n_group_places',
            'group_registered_persons',
            'total_registered_groups',
            'period_registration_start_date',
            'valid_registration_start_date',
            'valid_registration_date',
            'group_mode',

            'course_is_displayed',
        )
    )

    for slot in slots_list:
        data_for_context(data, data_dict, slot)

    data_dict["slot_list"] = slots_list

    context = {
        'subdomain': subdomain,
        'data': data_dict,
        'today': today,
        'is_anonymous': request.user.is_anonymous,
        'highschool': request.user.highschool if request.user.is_authenticated and request.user.is_high_school_manager() else None,
    }

    return render(request, 'cohort_offer_subdomains.html', context)
