"""
API Views
"""

import csv
import datetime
import importlib
import json
import logging
import time
import codecs

from functools import reduce
from itertools import chain, permutations
from typing import Any, Dict, List, Optional, Tuple, Union

import django_filters.rest_framework
from django.conf import settings

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    DateField,
    Exists,
    ExpressionWrapper,
    F,
    Func,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, Greatest, JSONObject
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
    BaseEstablishment,
    Building,
    Campus,
    CancelType,
    Course,
    CourseType,
    Establishment,
    GeneralSettings,
    HigherEducationInstitution,
    HighSchool,
    HighSchoolLevel,
    Holiday,
    Immersion,
    ImmersionGroupRecord,
    ImmersionUser,
    ImmersionUserGroup,
    MailTemplate,
    MailTemplateVars,
    OffOfferEvent,
    Period,
    PublicDocument,
    RefStructuresNotificationsSettings,
    Slot,
    Structure,
    Training,
    TrainingDomain,
    TrainingSubdomain,
    UniversityYear,
    UserCourseAlert,
    Vacation,
)
from immersionlyceens.apps.core.serializers import (
    BuildingSerializer,
    CampusSerializer,
    CourseSerializer,
    CourseTypeSerializer,
    EstablishmentSerializer,
    HighSchoolLevelSerializer,
    HighSchoolSerializer,
    ImmersionUserSerializer,
    OffOfferEventSerializer,
    PeriodSerializer,
    SlotSerializer,
    SpeakerSerializer,
    StructureSerializer,
    TrainingDomainSerializer,
    TrainingSerializer,
    TrainingSubdomainSerializer,
    UserCourseAlertSerializer,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord,
    HighSchoolStudentRecordDocument,
    BaseRecord,
    StudentRecord,
    VisitorRecord,
    VisitorRecordDocument,
)
from immersionlyceens.decorators import (
    groups_required,
    is_ajax_request,
    is_post_request,
    timer,
)
from immersionlyceens.libs.api.accounts import AccountAPI
from immersionlyceens.libs.mails.mail import Mail
from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting, render_text

from . import filters
from .mixins import ManyMixin, SpeakersManyMixin

from .permissions import (
    CustomDjangoModelPermissions,
    HighSchoolReadOnlyPermissions,
    IsEstablishmentManagerPermissions,
    IsHighSchoolStudentPermissions,
    IsMasterEstablishmentManagerPermissions,
    IsRefLycPermissions,
    IsSpeakerPermissions,
    IsStructureConsultantPermissions,
    IsStructureManagerPermissions,
    IsStudentPermissions,
    IsTecPermissions,
    IsVisitorPermissions,
    SpeakersReadOnlyPermissions,
    IsRefLycPermissions,
)

from .utils import get_or_create_user

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
            filters = {'groups__name': 'INTER', 'last_name__istartswith': search_str}

            if structure_id is not None:
                users_filter = Q(establishment=establishment) | Q(structures=structure_id)
            else:
                users_filter = Q(establishment=establishment)
                filters["establishment"] = establishment

            users_queryset = ImmersionUser.objects.filter(users_filter, **filters)

    elif highschool:
        users_queryset = ImmersionUser.objects.filter(
            highschool=highschool, groups__name='INTER', last_name__istartswith=search_str
        )

    if users_queryset:
        response['data'] = [query_order] + [
            {
                'username': user.username,
                'firstname': user.first_name,
                'lastname': user.last_name,
                'email': user.email,
                'display_name': f"{user.last_name} {user.first_name}",
            }
            for user in users_queryset
        ]

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
    period = request.GET.get('period')

    if not _date:
        response['msg'] = gettext('Error: A date is required')
        return JsonResponse(response, safe=False)
        
    # two format date
    try:
        formated_date = datetime.datetime.strptime(_date, '%Y/%m/%d')
    except ValueError:
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
        period = Period.from_date(pk=period, date=formated_date)
    except Period.DoesNotExist:
        details.append(_("Outside valid period"))

    response['data'] = {
        'date': _date,
        'is_between': is_vacation or is_holiday or is_sunday,
        'details': details,
        'valid_period': period is not None,
    }

    return JsonResponse(response, safe=False)

def validate_parent_date(request):
    """
    Check if a date:
      - is before the start_date of the parent (event or course)
      - is after the end_date of the parent (event or course)
    :param request: the request.
    :return: a dict with data about the date
    """
    response = {'data': {}, 'msg': ''}

    _date = request.GET.get('date')
    start_date = datetime.datetime.fromisoformat(request.GET.get('start_date'))
    end_date = datetime.datetime.fromisoformat(request.GET.get('end_date'))
    is_before = False
    is_after = False

    if not _date:
        response['msg'] = gettext('Error: A date is required')
        return JsonResponse(response, safe=False)

    # two format date
    try:
        formated_date = datetime.datetime.strptime(_date, '%Y/%m/%d')
    except ValueError:
        try:
            formated_date = datetime.datetime.strptime(_date, '%d/%m/%Y')
        except ValueError:
            response['msg'] = gettext('Error: bad date format')
            return JsonResponse(response, safe=False)

    formated_date =  timezone.make_aware(formated_date)

    details = []
    if start_date:
        is_before = formated_date < start_date
    if end_date:
        is_after = formated_date > end_date

    if is_before:
        details.append(_("Before"))
    if is_after:
        details.append(_("After"))

    response['data'] = {
        'date': _date,
        'outside': is_before or is_after,
        'details': details,
    }

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

    # get these values from BaseRecord class
    actions = {
        'TO_VALIDATE': BaseRecord.TO_VALIDATE,
        'VALIDATED': BaseRecord.VALIDATED,
        'REJECTED': BaseRecord.REJECTED,
        'TO_REVALIDATE': BaseRecord.TO_REVALIDATE,
    }

    try:
        record_filter = {
            "validation": actions[action]
        }
    except KeyError:
        response['msg'] = gettext("Error: No action selected for request")
        return JsonResponse(response, safe=False)

    # Highschool : accept an int or 'all'
    try:
        hs_id = int(hs_id)
        record_filter['highschool_id'] = hs_id
    except (ValueError, TypeError):
        # Default
        hs_id = 'all'

    # Conventions
    if with_convention in [0, 1, "0", "1"]:
        record_filter['highschool__with_convention'] = with_convention in (1, "1")

    # Store filters in session
    request.session["highschool_filter"] = hs_id
    request.session["convention_filter"] = with_convention

    attestations = (
        HighSchoolStudentRecordDocument.objects.filter(
            Q(validity_date__lt=today) | Q(validity_date__isnull=True),
            archive=False,
            record=OuterRef("pk"),
            requires_validity_date=True,
        )
        .exclude(Q(validity_date__isnull=True, document='') | Q(validity_date__isnull=False), mandatory=False)
        .order_by()
        .annotate(count=Func(F('id'), function='Count'))
        .values('count')
    )

    records = (
        HighSchoolStudentRecord.objects.prefetch_related('highschool')
        .filter(**record_filter)
        .annotate(
            user_first_name=F("student__first_name"),
            user_last_name=F("student__last_name"),
            record_level=F("level__label"),
            invalid_dates=Subquery(attestations),
        )
        .values(
            "id",
            "user_first_name",
            "user_last_name",
            "birth_date",
            "record_level",
            "class_name",
            "creation_date",
            "validation_date",
            "rejected_date",
            "rejection_reason",
            "invalid_dates",
            "highschool__city",
            "highschool__label",
            "highschool__with_convention",
        )
    )

    # List of the ids of the extracted records
    record_ids = [r['id'] for r in records]

    # Getting the attestations linked to the records
    docs_qs = HighSchoolStudentRecordDocument.objects.filter(
        record_id__in=record_ids,
        archive=False,
        document__isnull=False
    ).select_related('attestation')

    # List of attestations
    attestations_by_record = {}
    for doc in docs_qs:
        att = doc.attestation
        if att:
            attestations_by_record.setdefault(doc.record_id, []).append({
                'id': doc.pk,
                'label': att.label,
                'url': doc.document.url if doc.document else '',
                'validity_date': doc.validity_date.strftime("%Y-%m-%d") if doc.validity_date else None,
                'requires_validity_date': doc.requires_validity_date,
            })

    for rec in records:
        rec['attestations'] = attestations_by_record.get(rec['id'], [])

    response['data'] = list(records)

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_cancel_rejection(request):
    """
    Reinit the visitor or high school student record status to 'to validate'
    """
    student_record_id = request.POST.get('student_record_id')
    visitor_record_id = request.POST.get('visitor_record_id')

    response = {'data': None, 'msg': ''}
    highschool_filter = {}
    msgs = []

    if not student_record_id and not visitor_record_id:
        response['msg'] = "Error: No record selected"
        return JsonResponse(response, safe=False)
    else:
        if student_record_id:
            record_class = HighSchoolStudentRecord
            record_id = student_record_id
        else:
            record_class = VisitorRecord
            record_id = visitor_record_id

    # Check authenticated user profile, the following have access to all high schools
    all_highschools_conditions = [
        request.user.is_establishment_manager(),
        request.user.is_master_establishment_manager(),
        request.user.is_operator(),
    ]

    # Single high school access (the one linked to the user)
    if not any(all_highschools_conditions):
        highschool_filter['id'] = request.user.highschool.id

    hs = HighSchool.objects.filter(**highschool_filter)

    if not hs.exists():
        response['msg'] = "Error: No high school"
        return JsonResponse(response, safe=False)

    try:
        record = record_class.objects.get(pk=record_id)
        record.set_status("TO_VALIDATE")
        record.save()
        response['data'] = {'ok': True}
    except record_class.DoesNotExist:
        response['msg'] = gettext("Error - record not found: %s") % (record_id)

    return JsonResponse(response, safe=False)

# REJECT / VALIDATE STUDENT
@is_ajax_request
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def ajax_validate_reject_student(request, validate):
    """
    Validate or reject student
    """
    student_record_id = request.POST.get('student_record_id')
    rejection_reason = request.POST.get('rejection_reason', '')
    validation_data = request.POST.get("validity_dates", "[]")

    today = timezone.localdate()
    response = {'data': None, 'msg': ''}
    highschool_filter = {}
    msgs = []

    if not student_record_id:
        response['msg'] = "Error: No student selected"
        return JsonResponse(response, safe=False)

    try:
        validation_data = json.loads(validation_data)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON validation data"}, status=400)

    # Check authenticated user profile, the following have access to all high schools
    all_highschools_conditions = [
        request.user.is_establishment_manager(),
        request.user.is_master_establishment_manager(),
        request.user.is_operator(),
    ]

    # Single high school access (the one linked to the user)
    if not any(all_highschools_conditions):
        highschool_filter['id'] = request.user.highschool.id

    hs = HighSchool.objects.filter(**highschool_filter)

    if not hs.exists():
        response['msg'] = "Error: No high school"
        return JsonResponse(response, safe=False)

    # Direct validation of attestations (POST validation_data from student_validation template)
    for document_data in validation_data:
        doc_id = document_data.get("id")
        doc_validity_date = document_data.get("validity_date", "")

        try:
            document = HighSchoolStudentRecordDocument.objects.get(pk=doc_id, record_id=student_record_id)
            if doc_validity_date:
                document.validity_date = parse_date(doc_validity_date)
                document.save()

        except HighSchoolStudentRecordDocument.DoesNotExist:
            pass
        # Add exception for parse_date ?

    try:
        record = HighSchoolStudentRecord.objects.prefetch_related('attestation').get(
            id=student_record_id,
            highschool__in=hs
        )

        # Check documents
        attestations = record.attestation.filter(
            Q(validity_date__lt=today) | Q(validity_date__isnull=True),
            archive=False,
            requires_validity_date=True,
        ).exclude(Q(validity_date__isnull=True, document='') | Q(validity_date__isnull=False), mandatory=False)

        if validate and attestations.exists():
            response['msg'] = _("Error: record has missing or invalid attestation dates")
            return JsonResponse(response, safe=False)

        # Disability notifications
        set_status_params = {}

        # Already valid record or 'to revalidate' : do not send the notification again
        # For the others, it also depends on the 'disability' flag of the record
        if record.validation not in (BaseRecord.TO_REVALIDATE, BaseRecord.VALIDATED):
            set_status_params = {
                "request": request,
                "notify_disability": record.disability
            }

        # 2 => VALIDATED
        # 3 => REJECTED
        res = record.set_status("VALIDATED" if validate else "REJECTED", **set_status_params)

        if res.get("msg"):
            msgs.append(res.get("msg"))

        record.rejected_date = None if validate else timezone.localtime()
        record.rejection_reason = rejection_reason if rejection_reason else ""
        record.save()

        # Delete attestations ?
        if validate:
            delete_attachments = get_general_setting("DELETE_RECORD_ATTACHMENTS_AT_VALIDATION")
            if delete_attachments:
                # Delete only attestations that does not require a validity date
                for attestation in record.attestation.filter(requires_validity_date=False):
                    attestation.delete()

        template = 'CPT_MIN_VALIDE' if validate else 'CPT_MIN_REJET'
        ret = record.student.send_message(request, template)

        if ret:
            msgs.append(_("Record updated but notification not sent : %s") % ret)
            response['msg'] = "<br>".join(map(str, msgs))
        else:
            msgs.append(_("Record updated, notification sent"))
            response.update({
                'msg': "<br>".join(map(str, msgs)),
                'data': {'ok': True}
            })

    except HighSchoolStudentRecord.DoesNotExist:
        response['msg'] = gettext("Error: No student record")

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
                response = {
                    'error': True,
                    'msg': gettext("You can't delete this account (this user has slots)")
                }
                return JsonResponse(response, safe=False)

            if request.user.is_high_school_manager():
                if not request.user.highschool or request.user.highschool != account.highschool:
                    response = {
                        'error': True,
                        'msg': gettext("You can't delete this account (insufficient privileges)"),
                    }
                    return JsonResponse(response, safe=False)

            if request.user.is_establishment_manager():
                if not request.user.establishment or request.user.establishment != account.establishment:
                    response = {
                        'error': True,
                        'msg': gettext("You can't delete this account (insufficient privileges)"),
                    }
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
    now = timezone.now()
    user = request.user
    allowed_structures = user.get_authorized_structures()

    # FIXME : test request.user rights on immersion.slot

    if not immersion_id or not reason_id:
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            immersion = Immersion.objects.prefetch_related("slot__course", "student", "slot__speakers").get(
                pk=immersion_id
            )
            if immersion.slot.date < today.date() or (
                immersion.slot.date == today.date() and immersion.slot.start_time < today.time()
            ):
                response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
                return JsonResponse(response, safe=False)

            if immersion.slot.cancellation_limit_date < timezone.localtime():
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
                user.is_high_school_manager()
                and (immersion.slot.course or immersion.slot.event)
                and slot_highschool
                and user.highschool == slot_highschool,
            ]

            if not any(valid_conditions):
                response = {'error': True, 'msg': _("You don't have enough privileges to cancel this registration")}
                return JsonResponse(response, safe=False)

            cancellation_reason = CancelType.objects.get(pk=reason_id)

            # Check usability
            managers = [
                request.user.is_establishment_manager(),
                request.user.is_master_establishment_manager(),
                request.user.is_high_school_manager(),
                request.user.is_operator(),
                request.user.is_structure_manager(),
            ]

            students = [request.user.is_high_school_student(), request.user.is_visitor(), request.user.is_student()]

            if (
                not cancellation_reason.usable_for_students
                or (any(managers) and not cancellation_reason.usable_by_manager())
                or (any(students) and not cancellation_reason.usable_by_student())
            ):
                response = {'error': True, 'msg': _("You can't use this cancellation reason")}
                return JsonResponse(response, safe=False)

            immersion.cancellation_type = cancellation_reason
            immersion.cancellation_date = timezone.now()
            immersion.save()
            ret = immersion.student.send_message(request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot)

            # If slot registrations are over (check limit date), also send a message to speakers
            # and structure managers
            if immersion.slot.registration_limit_date < now:
                for speaker in immersion.slot.speakers.all():
                    speaker.send_message(request, 'IMMERSION_ANNULATION_INT', slot=immersion.slot)

                # structure managers
                slot_structure = immersion.slot.get_structure()
                if slot_structure:
                    for notify in RefStructuresNotificationsSettings.objects.filter(structures=slot_structure):
                        ret = notify.user.send_message(None, "IMMERSION_ANNULATION_STR", slot=immersion.slot)
                        # FIXME : do something if send_message fails

                # High school managers
                highschool = immersion.slot.get_highschool()

                if highschool:
                    # Get this high school managers
                    # Check the message preferences (False by default)
                    # Send the same message template
                    for manager in highschool.users.filter(groups__name='REF-LYC'):
                        if manager.get_preference("RECEIVE_REGISTERED_STUDENTS_LIST", False):
                            ret = manager.send_message(None, "IMMERSION_ANNULATION_STR", slot=immersion.slot)
                            # FIXME : do something if send_message fails

            response = {'error': False, 'msg': gettext("Immersion cancelled")}
        except Immersion.DoesNotExist:
            response = {'error': True, 'msg': gettext("User not found")}
        except CancelType.DoesNotExist:
            response = {'error': True, 'msg': gettext("Invalid cancellation reason #id")}

    return JsonResponse(response, safe=False)


@is_ajax_request
# TODO: check rights
@groups_required('REF-ETAB', 'LYC', 'ETU', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC', 'VIS')
def ajax_get_immersions(request, user_id=None):
    """
    Returns students immersions
    GET parameters:
    immersion_type in "future", "past", "cancelled" or None (= all)
    slot_type in "course", "event" or None (= all)
    """
    all_types = ['course', 'event']  # Fixme : do something with this in Slot class

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
        user.id == user_id,
    ]

    if not any(valid_conditions):
        response['msg'] = gettext("Error : invalid user id")
        return JsonResponse(response, safe=False)

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = timezone.localdate()
    now = timezone.localtime()

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

    prefetch = ['slot__campus', 'slot__building', 'slot__speakers']

    if slot_type:
        filters.update({f'slot__{a}__isnull': True for a in filter(lambda a: a != slot_type, all_types)})
        prefetch.append(f'slot__{slot_type}')

        if slot_type == 'course':
            prefetch += ['slot__course__training', 'slot__course_type']
    else:
        prefetch += ['slot__course', 'slot__course__training', 'slot__course_type', 'slot__event']

    if immersion_type == "cancelled":
        filters["cancellation_type__isnull"] = False
    elif immersion_type:
        filters["cancellation_type__isnull"] = True

    immersions = Immersion.objects.prefetch_related(*prefetch).filter(**filters)

    if immersion_type == "future":
        immersions = immersions.filter(Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gte=time))
    elif immersion_type == "past":
        immersions = immersions.filter(Q(slot__date__lt=today) | Q(slot__date=today, slot__start_time__lte=time))

    for immersion in immersions:
        slot = immersion.slot
        highschool = slot.get_highschool()
        establishment = slot.get_establishment()
        structure = slot.get_structure()
        campus = slot.campus.label if slot.campus else ""
        campus_city = slot.campus.city if slot.campus else ""
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
        if slot.place == Slot.REMOTE:
            meeting_place = gettext('Remote')
        elif slot.place in [Slot.FACE_TO_FACE, Slot.OUTSIDE]:
            meeting_place = slot.room

        if highschool:
            hs_address = highschool.address if highschool.address else ""
            hs_address2 = highschool.address2 if highschool.address2 else ""
            hs_address3 = highschool.address2 if highschool.address2 else ""

        immersion_data = {
            'id': immersion.id,
            'type': slot.get_type(),
            'translated_type': gettext(slot.get_type().title()),
            'label': slot.get_label(),
            'establishment': establishment.label if establishment else "",
            'highschool': f'{highschool.label} - {highschool.city.title()}' if highschool else "",
            'highschool_address': f'{hs_address} {hs_address2} {hs_address3}' if highschool else "",
            'highschool_city': highschool.city.title() if highschool else "",
            'highschool_zip_code': highschool.zip_code if highschool else "",
            'structure': structure.label if structure else "",
            'meeting_place': meeting_place,
            'campus': campus,
            'building': building,
            'room': slot.room,
            'establishments': [],
            'course': (
                {
                    'label': slot.course.label,
                    'training': slot.course.training.label,
                    'training_url': slot.course.training.url,
                    'type': slot.course_type.label,
                    'type_full': slot.course_type.full_label,
                }
                if slot.course
                else {}
            ),
            'event': {'label': slot.event.label, 'type': slot.event.event_type.label} if slot.event else {},
            'datetime': slot_datetime,
            'date': date_format(slot.date),
            'start_time': slot.start_time.strftime("%-Hh%M"),
            'end_time': slot.end_time.strftime("%-Hh%M"),
            'speakers': [],
            'info': slot.additional_information,
            'attendance': immersion.get_attendance_status_display(),
            'attendance_status': immersion.attendance_status,
            'cancellable': (
                timezone.localtime() <= slot.cancellation_limit_date if slot.cancellation_limit_date else True
            ),
            'cancellation_limit_date': slot.cancellation_limit_date,
            'cancellation_type': '',
            'slot_id': slot.id,
            'free_seats': 0,
            'can_register': False,
            'place': slot.place,
            'url': slot.url if slot.can_show_url() else gettext("Displayed a few days before event"),
            'can_show_url': slot.can_show_url(),
            'registration_date': immersion.registration_date,
            'cancellation_date': immersion.cancellation_date if immersion.cancellation_date else "",
            'campus_city': campus_city.title() if campus_city else "",
            'allow_individual_registrations': slot.allow_individual_registrations,
            'n_places': slot.n_places,
            'n_registered': slot.registered_students(),
            'registration_limit_date': slot.registration_limit_date,
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
                period = slot.period
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
                immersions__cancellation_type__isnull=True,
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
    # TODO: should be optimized to avoid loops on queryset
    # USE ANNOTATIONS
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
                    immersion_data['disabled'] = record.disability
                    immersion_data['school'] = record.highschool.label
                    immersion_data['city'] = record.highschool.city
                    immersion_data['level'] = record.level.label

            elif immersion.student.is_student():
                immersion_data['profile'] = pgettext("person type", "Student")
                record = immersion.student.get_student_record()

                if record:
                    immersion_data['disabled'] = record.disability
                    immersion_data['school'] = record.institution.label if record.institution else record.uai_code
                    immersion_data['level'] = record.level.label

            elif immersion.student.is_visitor():
                record = immersion.student.get_visitor_record()

                if record:
                    immersion_data['disabled'] = record.disability

                immersion_data['profile'] = pgettext("person type", "Visitor")

            response['data'].append(immersion_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC', 'CONS-STR')
def ajax_get_slot_groups_registrations(request, slot_id):
    # TODO: should be optimized to avoid loops on queryset
    # USE ANNOTATIONS
    slot = None
    response = {'msg': '', 'data': [], 'n_group_places': 0, 'total_registered': 0}

    try:
        slot = Slot.objects.get(pk=slot_id)
        response['n_group_places'] = slot.n_group_places
    except ObjectDoesNotExist:
        response['msg'] = gettext("Error : invalid slot id")

    if slot:
        immersions = ImmersionGroupRecord.objects.prefetch_related('highschool').filter(
            slot=slot, cancellation_type__isnull=True
        )

        response['total_groups_registered'] = immersions.count()
        response['group_mode'] = slot.group_mode

        for immersion in immersions:
            total_count = (immersion.students_count or 0) + (immersion.guides_count or 0)
            immersion_data = {
                'id': immersion.id,
                'highschool_id': immersion.highschool.id,
                'school': immersion.highschool.label,
                'city': immersion.highschool.city,
                'students_count': immersion.students_count,
                'guides_count': immersion.guides_count,
                'total_count': total_count,
                'file_link': (
                    reverse('group_document', kwargs={'immersion_group_id': immersion.id}) if immersion.file else ""
                ),
                'file_name': immersion.file.name if immersion.file else "",
                'emails': immersion.emails,
                'comments': immersion.comments,
                'attendance': immersion.get_attendance_status_display(),
                'attendance_status': immersion.attendance_status,
                'registration_date': immersion.registration_date,
            }

            response['data'].append(immersion_data.copy())
            response['total_registered'] += total_count

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
                    immersion.student,
                    gettext("you don't have enough privileges to set the attendance status"),
                )

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'CONS-STR')
def ajax_set_group_attendance(request):
    """
    Update group immersion attendance status
    """
    immersion_group_id = request.POST.get('immersion_group_id', None)
    immersion_group_ids = request.POST.get('immersion_group_ids', None)
    user = request.user
    allowed_structures = user.get_authorized_structures()

    # Control if we can cancel a group immersion by clicking again on its status
    single_immersion = True

    response = {'success': '', 'error': '', 'data': []}

    if immersion_group_ids:
        immersion_group_ids = json.loads(immersion_group_ids)
        single_immersion = False

    try:
        attendance_value = int(request.POST.get('attendance_value'))
    except:
        attendance_value = None

    if not attendance_value:
        response['error'] = gettext("Error: no attendance status set in parameter")
        return JsonResponse(response, safe=False)

    if not immersion_group_id and not immersion_group_ids:
        response['error'] = gettext("Error: missing immersion id parameter")
        return JsonResponse(response, safe=False)

    if immersion_group_id and not immersion_group_ids:
        immersion_group_ids = [immersion_group_id]

    for immersion_id in immersion_group_ids:
        immersion = None
        try:
            immersion = ImmersionGroupRecord.objects.get(pk=immersion_id)
        except ImmersionGroupRecord.DoesNotExist:
            response['error'] = gettext("Error : query contains some invalid group immersion ids")

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
                response['success'] += f"{immersion.highschool} : {gettext('attendance status updated')}"
            else:
                response['error'] += "%s : %s" % (
                    immersion.highschool,
                    gettext("you don't have enough privileges to set the attendance status"),
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
    off_offer = False
    training_quota_active = False
    training_quota_count = 0
    available_training_registrations = None
    send_mail = True

    request.session.pop("last_registration_slot", None)

    can_force_reg = any([user.is_establishment_manager(), user.is_master_establishment_manager(), user.is_operator()])

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
            off_offer = True if slot.event else False
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

    requesting_user_is_student = any([
        user.is_high_school_student(),
        user.is_student(),
        user.is_visitor(),
    ])

    # Fixme : add slot restrictions here
    unpublished_slot_update_conditions = [
        user.is_master_establishment_manager(),
        user.is_operator(),
        user.is_establishment_manager() and establishment == user_establishment,
    ]

    published_slot_update_conditions = [
        any(unpublished_slot_update_conditions),
        user.is_structure_manager() and slot_structure in allowed_structures,
        slot.course and user.is_high_school_manager() and slot_highschool and slot_highschool == user_highschool,
        requesting_user_is_student,
        user.is_high_school_manager()
        and (slot.course or slot.event)
        and slot_highschool
        and user.highschool == slot_highschool,
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

    # Only valid student records
    if student.is_student():
        if not student.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to student account state")}
            return JsonResponse(response, safe=False)

        record = student.get_student_record()
        if not record or not record.is_valid():
            response = {'error': True, 'msg': _("Cannot register slot due to student record state")}
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

    # Out of date mandatory attestations
    if student.has_obsolete_attestations():
        response = {'error': True, 'msg': _("Cannot register slot due to out of date attestations")}
        return JsonResponse(response, safe=False)

    # Check if slot date is not passed. The admins can register people even if the date is passed
    if not (user.is_master_establishment_manager() or
            user.is_establishment_manager() and establishment == user_establishment or
            user.is_structure_manager() and structure == allowed_structures or
            user.is_high_school_manager() and user.highschool == user_highschool):
        if slot.date < today or (slot.date == today and today_time > slot.start_time):
            response = {'error': True, 'msg': _("Register to past slot is not possible")}
            return JsonResponse(response, safe=False)

    # Slot restrictions validation
    can_register_slot, reasons = student.can_register_slot(slot)
    passed_registration_date = timezone.localtime() > slot.registration_limit_date

    if not can_register_slot or passed_registration_date:
        if can_force_reg:
            if not force:
                if not can_register_slot:
                    return JsonResponse({'error': True, 'msg': 'force_update', 'reason': 'restrictions'}, safe=False)

                if passed_registration_date:
                    return JsonResponse(
                        {'error': True, 'msg': 'force_update', 'reason': 'passed_registration_date'}, safe=False
                    )
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

        # For courses slots only : training quotas ?
        if not off_offer:
            try:
                training_quota = GeneralSettings.get_setting("ACTIVATE_TRAINING_QUOTAS")
                training_quota_active = training_quota['activate']
                training_quota_count = training_quota['default_quota']
            except Exception as e:
                msg = _(
                    "ACTIVATE_TRAINING_QUOTAS parameter not found or incorrect : please check the platform settings"
                )
                response = {'error': True, 'msg': msg}
                return JsonResponse(response, safe=False)

        # Get period, available period registrations (quota) and the optional training quota
        period = slot.period

        if period:
            available_registrations = remaining_registrations.get(period.pk, 0)

            # If training quota is active, check registrations for this period/training

            if not off_offer and training_quota_active:
                training_regs_count = student.immersions.filter(
                    slot__date__gte=period.immersion_start_date,
                    slot__date__lte=period.immersion_end_date,
                    slot__course__training=slot.course.training,
                    cancellation_type__isnull=True,
                ).count()

                # specific quota for this training ?
                if slot.course.training.allowed_immersions:
                    training_quota_count = slot.course.training.allowed_immersions

                available_training_registrations = training_quota_count - training_regs_count
        else:
            msg = _("No period found for slot %s : please check periods settings") % slot
            response = {'error': True, 'msg': msg}
            return JsonResponse(response, safe=False)

        if off_offer:
            can_register = True
        elif available_registrations > 0 and available_training_registrations is None:
            can_register = True
        elif available_registrations > 0 and (
            available_training_registrations is not None and available_training_registrations > 0
        ):
            can_register = True
        elif can_force_reg and not force:
            reason = ""

            if available_registrations <= 0:
                reason = "quota"
            elif available_training_registrations is not None and available_training_registrations <= 0:
                reason = "training_quota"

            return JsonResponse({'error': True, 'msg': 'force_update', 'reason': reason}, safe=False)
        elif force:
            can_register = True
            if slot.is_course():
                student.set_increment_registrations_(period=period)
        elif user.is_high_school_student() or user.is_student() or user.is_visitor():
            msg = None

            if available_registrations <= 0:
                msg = _(
                    """You have no more remaining registration available for this period, """
                    """you should cancel an immersion or contact immersion service"""
                )
            elif available_training_registrations is not None and available_training_registrations <= 0:
                msg = _(
                    """You have no more remaining registration available for this training and this period, """
                    """you should cancel an immersion or contact immersion service"""
                )

            if msg:
                response = {'error': True, 'msg': msg}
                return JsonResponse(response, safe=False)
        elif user.is_structure_manager() or user.is_high_school_manager():
            msg = None

            if available_registrations <= 0:
                msg = _("This student is over quota for this period")
            elif available_training_registrations is not None and available_training_registrations <= 0:
                msg = _("This student is over training quota for this period")

            if msg:
                response = {'error': True, 'msg': msg}
                return JsonResponse(response, safe=False)

        if can_register:
            msgs = []
            error = False
            immersion = None

            # Transaction should prevent multiple registrations to the same slot within a few milliseconds
            with transaction.atomic():
                # Cancelled immersion exists : re-register
                if student.immersions.filter(slot=slot, cancellation_type__isnull=False).exists():
                    student.immersions.filter(slot=slot, cancellation_type__isnull=False).update(
                        cancellation_type=None,
                        attendance_status=0,
                        cancellation_date=None
                    )
                    immersion = student.immersions.filter(slot=slot, cancellation_type__isnull=True).first()
                elif not student.immersions.filter(slot=slot).exists():
                    try:
                        # New registration
                        immersion = Immersion.objects.create(
                            student=student,
                            slot=slot,
                            cancellation_type=None,
                            attendance_status=0,
                        )
                    except IntegrityError:
                        # Immersion already exists, should not happen
                        send_mail = False
                        error = True
                        msgs.append(_("Registration to this slot already exists"))

            # Disability options
            notify_disability = "never"  # "never" / "auto" / "on_demand"
            notification_settings = slot.get_disability_notification_setting() # will also check general setting

            if record and record.disability:
                # if requesting user is not a student, bypass this case and automatically notify
                if notification_settings == BaseEstablishment.DISABILITY_SLOT_NOTIFICATION_IF_ASKED:
                    if requesting_user_is_student:
                        notify_disability = "on_demand"
                    else:
                        # Force the setting to "auto"
                        notification_settings = BaseEstablishment.DISABILITY_SLOT_NOTIFICATION_IF_CHECKED

                if notification_settings == BaseEstablishment.DISABILITY_SLOT_NOTIFICATION_IF_CHECKED:
                    # Send the email here
                    notify_disability = "auto"

                    # Should notify establishment/high school referent (if email is set)
                    # and the structure referents
                    if immersion and immersion.slot.date > today:
                        ret = immersion.notify_disability_referent()
                        error = ret.get("error", False)
                        if ret.get("msg"):
                            msgs.append(ret["msg"])

            # Send the confirmation email
            if send_mail:
                ret = student.send_message(request, 'IMMERSION_CONFIRM', slot=slot)
                if not ret:
                    msgs.append(gettext("Registration successfully added, confirmation email sent"))
                else:
                    msgs.append(gettext("Registration successfully added, confirmation email NOT sent : %s") % ret)
                    error = True

            response = {
                'error': error,
                'msg': "<br>".join(msgs),
                'notify_disability': notify_disability
            }

            # TODO: use django messages for errors as well ?
            # this is a js boolean !!!!
            if feedback == True:
                if error:
                    messages.warning(request, "<br>".join(msgs))
                else:
                    messages.success(request, "<br>".join(msgs))

            request.session["last_registration_slot_id"] = slot.id
        else:
            response = {'error': True, 'msg': _("Registration is not currently allowed")}

    return JsonResponse(response, safe=False)


@is_ajax_request
@login_required
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_group_slot_registration(request):
    """
    Register a group to a slot
    """
    id = request.POST.get('id', None)
    slot_id = request.POST.get('slot_id', None)
    highschool_id = request.POST.get('highschool_id', None)
    students_count = request.POST.get('students_count', None)
    guides_count = request.POST.get('guides_count', None)
    file = request.FILES.get('file', None)
    emails = request.POST.get('emails', None)
    comments = request.POST.get('comments', None)
    feedback = request.POST.get('feedback', True)
    current_students_count = 0
    current_guides_count = 0

    error = False
    cleaned_emails = []
    user = request.user

    activate_groups = GeneralSettings.get_setting("ACTIVATE_COHORT")
    if not activate_groups:
        response = {'error': True, 'msg': _("Groups registrations are disabled")}
        return JsonResponse(response, safe=False)

    try:
        students_count = int(students_count)
        assert students_count > 0
    except:
        response = {'error': True, 'msg': _("Invalid value for students count")}
        return JsonResponse(response, safe=False)

    try:
        guides_count = int(guides_count)
        assert guides_count > 0
    except:
        response = {'error': True, 'msg': _("Invalid value for guides count")}
        return JsonResponse(response, safe=False)

    try:
        # Update
        immersion_group_record = ImmersionGroupRecord.objects.get(pk=id)
        current_students_count = immersion_group_record.students_count
        current_guides_count = immersion_group_record.guides_count
    except:
        # Creation
        immersion_group_record = None

    try:
        slot = Slot.objects.get(pk=slot_id)
    except:
        response = {'error': True, 'msg': _("Invalid slot")}
        return JsonResponse(response, safe=False)

    if not slot.allow_group_registrations:
        response = {'error': True, 'msg': _("This slot doesn't allow group registrations")}
        return JsonResponse(response, safe=False)

    if slot.group_mode == Slot.ONE_GROUP:
        excludes = {"pk": id} if id else {}

        if slot.group_immersions.filter(cancellation_type__isnull=True).exclude(**excludes).count() > 0:
            response = {'error': True, 'msg': _("This slot accepts only one registered group")}
            return JsonResponse(response, safe=False)

    # available places
    # on update, do not forget to ignore current slot students and guides count
    people_dict = slot.registered_groups_people_count()
    current_registered_count = sum(people_dict.values()) - current_guides_count - current_students_count


    if (students_count + guides_count) > (slot.n_group_places - current_registered_count):
        response = {'error': True, 'msg': _("There is not enough available places for this group")}
        return JsonResponse(response, safe=False)

    # Valid user conditions to register a group
    allowed_structures = user.get_authorized_structures()
    user_establishment = user.establishment
    user_highschool = user.highschool

    establishment = slot.get_establishment()
    slot_structure = slot.get_structure()

    # Fixme : add slot restrictions here
    unpublished_slot_update_conditions = [
        user.is_master_establishment_manager(),
        user.is_operator(),
        user.is_establishment_manager() and establishment == user_establishment,
    ]

    published_slot_update_conditions = [
        any(unpublished_slot_update_conditions),
        user.is_structure_manager() and slot_structure in allowed_structures,
        user.is_high_school_manager(),
    ]

    # Check registration rights depending on the (not student) authenticated user
    if not slot.published and not any(unpublished_slot_update_conditions):
        response = {'error': True, 'msg': _("Registering to an unpublished slot is forbidden")}
        return JsonResponse(response, safe=False)

    if slot.published and not any(published_slot_update_conditions):
        response = {'error': True, 'msg': _("Sorry, you can't add any group registration to this slot")}
        return JsonResponse(response, safe=False)

    # Validate emails format
    if emails:
        for email in map(lambda a: a.strip(), emails.split(',')):
            try:
                validate_email(email)
                cleaned_emails.append(email.lower())
            except ValidationError:
                response = {
                    'error': True,
                    'msg': _("This email seems invalid : %s. Please check the field format.") % email,
                }
                return JsonResponse(response, safe=False)
        else:
            emails = ",".join(cleaned_emails)

    if immersion_group_record:
        immersion_group_record.highschool_id = user_highschool.id if user.is_high_school_manager() else highschool_id
        immersion_group_record.students_count = students_count
        immersion_group_record.guides_count = guides_count
        immersion_group_record.comments = comments
        immersion_group_record.emails = emails
        if file:
            # Remove previous file from FS
            if immersion_group_record.file.name:
                immersion_group_record.file.storage.delete(immersion_group_record.file.name)

            immersion_group_record.file = file

        immersion_group_record.save()
        msg = _("Group successfully updated.")
    else:
        try:
            immersion_group_record = ImmersionGroupRecord.objects.create(
                slot=slot,
                highschool_id=user_highschool.id if user.is_high_school_manager() else highschool_id,
                students_count=students_count,
                guides_count=guides_count,
                comments=comments,
                emails=emails,
                file=file,
            )
            msg = _("Group successfully registered.")
        except Exception as e:
            msg = _("Registration error : %s") % e
            error = True

    if not error:
        # Send message to group contacts
        msg, error = immersion_group_record.send_message(request, 'IMMERSION_CONFIRM')

    if feedback == True:
        if error:
            messages.warning(request, msg)
        else:
            messages.success(request, msg)

    response = {'error': error, 'msg': msg}
    return JsonResponse(response, safe=False)


@login_required
@is_ajax_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_get_available_students(request, slot_id):
    """
    Get students list for manual slot registration
    Students must have a valid record and not already registered to the slot
    """
    response = {'data': [], 'slot': {}, 'msg': ''}
    user = request.user

    try:
        slot = Slot.objects.get(pk=slot_id)
        # Slot restrictions
        response['slot'] = {
            "establishments_restrictions": slot.establishments_restrictions,
            "levels_restrictions": slot.levels_restrictions,
            "bachelors_restrictions": slot.bachelors_restrictions,
            "allowed_establishments": [e.uai_reference_id for e in slot.allowed_establishments.all()],
            "allowed_highschools": [hs.id for hs in slot.allowed_highschools.all()],
            "allowed_highschool_levels": [level.id for level in slot.allowed_highschool_levels.all()],
            "allowed_student_levels": [level.id for level in slot.allowed_student_levels.all()],
            "allowed_post_bachelor_levels": [level.id for level in slot.allowed_post_bachelor_levels.all()],
            "allowed_bachelor_types": [bt.id for bt in slot.allowed_bachelor_types.all()],
            "allowed_bachelor_mentions": [bm.id for bm in slot.allowed_bachelor_mentions.all()],
            "allowed_bachelor_teachings": [bt.id for bt in slot.allowed_bachelor_teachings.all()],
        }
    except Slot.DoesNotExist:
        response['msg'] = _("Error : slot not found")
        return JsonResponse(response, safe=False)

    valid_high_school_record = HighSchoolStudentRecord.STATUSES["VALIDATED"]
    valid_visitor_record = VisitorRecord.STATUSES["VALIDATED"]

    # Secondary query needed in exclude : we need to see students who have cancelled their registration to
    # keep the possibility to read them
    students = (
        ImmersionUser.objects.prefetch_related(
            "groups",
            "immersions",
            "high_school_student_record__highschool",
            "student_record__institution",
            "high_school_student_record__level",
            "student_record__level",
            "high_school_student_record__post_bachelor_level",
            "high_school_student_record__bachelor_type",
            "high_school_student_record__technological_bachelor_mention",
        )
        .filter(
            Q(high_school_student_record__isnull=False, high_school_student_record__validation=valid_high_school_record)
            | Q(student_record__isnull=False)
            | Q(visitor_record__isnull=False, visitor_record__validation=valid_visitor_record),
            groups__name__in=['LYC', 'ETU', 'VIS'],
            validation_string__isnull=True,
        )
        .exclude(immersions__in=(Immersion.objects.filter(slot__id=slot_id, cancellation_type__isnull=True)))
    )

    # Restrictions :
    # Some users will only see a warning about restrictions not met (ref-etab, ref-etab-maitre, ref-tec)
    # Others won't even see the filtered participants in the list (ref-lyc, ref-str)

    if user.is_high_school_manager() or user.is_structure_manager():
        if slot.establishments_restrictions:
            establishment_filter = {}

            if slot.allowed_establishments.exists():
                establishment_filter['establishment__in'] = slot.allowed_establishments.all()

            if slot.allowed_highschools.exists():
                establishment_filter['high_school_student_record__highschool__in'] = slot.allowed_highschools.all()

            if establishment_filter:
                students = students.filter(
                    reduce(lambda x, y: x | y, [Q(**{'%s' % f: value}) for f, value in establishment_filter.items()])
                )

        if slot.levels_restrictions:
            levels_restrictions = {}

            if slot.allowed_highschool_levels.exists():
                levels_restrictions['high_school_student_record__level__in'] = slot.allowed_highschool_levels.all()

            if slot.allowed_post_bachelor_levels.exists():
                levels_restrictions['high_school_student_record__post_bachelor_level__in'] = (
                    slot.allowed_post_bachelor_levels.all()
                )

            if slot.allowed_student_levels.exists():
                levels_restrictions['student_record__level__in'] = slot.allowed_student_levels.all()

            if levels_restrictions:
                students = students.filter(
                    reduce(lambda x, y: x | y, [Q(**{'%s' % f: value}) for f, value in levels_restrictions.items()])
                )

        if slot.bachelors_restrictions:
            bachelor_type_filter = {}
            bachelors_restrictions = {}

            if slot.allowed_bachelor_types.exists():
                bachelor_type_filter = {
                    'high_school_student_record__bachelor_type__in': slot.allowed_bachelor_types.all()
                }

            if slot.allowed_bachelor_mentions.exists():
                bachelors_restrictions['high_school_student_record__technological_bachelor_mention__in'] = (
                    slot.allowed_bachelor_mentions.all()
                )

            if slot.allowed_bachelor_teachings.exists():
                bachelors_restrictions['high_school_student_record__general_bachelor_teachings__in'] = (
                    slot.allowed_bachelor_teachings.all()
                )

            if bachelor_type_filter and bachelors_restrictions:
                students = students.filter(
                    reduce(lambda x, y: x | y, [Q(**{'%s' % f: value}) for f, value in bachelors_restrictions.items()]),
                    **bachelor_type_filter,
                )

    # Annotations
    students = students.annotate(
        record_highschool_label=F('high_school_student_record__highschool__label'),
        record_highschool_id=F('high_school_student_record__highschool__id'),
        institution_label=F('student_record__institution__label'),
        institution_uai_code=F('student_record__uai_code'),
        city=F('high_school_student_record__highschool__city'),
        class_name=F('high_school_student_record__class_name'),
        profile=Case(
            When(high_school_student_record__isnull=False, then=Value(pgettext("person type", "High school student"))),
            When(student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
            When(visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
            default=Value(gettext("Unknown")),
        ),
        profile_name=Case(
            When(high_school_student_record__isnull=False, then=Value("highschool")),
            When(student_record__isnull=False, then=Value("student")),
            When(visitor_record__isnull=False, then=Value("visitor")),
            default=Value(gettext("Unknown")),
        ),
        level_id=Coalesce(
            F('high_school_student_record__level__id'),
            F('student_record__level__id')
        ),
        level=Coalesce(
            Case(
                When(
                    high_school_student_record__level__is_post_bachelor=True,
                    then=Concat(
                        F('high_school_student_record__level__label'),
                        Value(' - '),
                        F('high_school_student_record__post_bachelor_level__label'),
                    ),
                ),
                default=F('high_school_student_record__level__label'),
            ),
            F('student_record__level__label'),
        ),
        post_bachelor_level_id=F('high_school_student_record__post_bachelor_level__id'),
        post_bachelor_level=F('high_school_student_record__post_bachelor_level__label'),
        bachelor_type_id=F('high_school_student_record__bachelor_type__id'),
        bachelor_type=F('high_school_student_record__bachelor_type__label'),
        bachelor_type_is_professional=F('high_school_student_record__bachelor_type__professional'),
        technological_bachelor_mention_id=F('high_school_student_record__technological_bachelor_mention__id'),
        technological_bachelor_mention=F('high_school_student_record__technological_bachelor_mention__label'),
        general_bachelor_teachings_ids=ArrayAgg(
            F('high_school_student_record__general_bachelor_teachings__id'),
            ordering='high_school_student_record__general_bachelor_teachings__id',
            distinct=True,
        ),
    )

    students = students.values(
        "id",
        "last_name",
        "first_name",
        "record_highschool_label",
        "record_highschool_id",
        "institution_label",
        "institution_uai_code",
        "city",
        "class_name",
        "profile",
        "profile_name",
        "level",
        "level_id",
        "post_bachelor_level",
        "post_bachelor_level_id",
        "bachelor_type_id",
        "bachelor_type",
        "technological_bachelor_mention_id",
        "technological_bachelor_mention",
        "general_bachelor_teachings_ids",
        "bachelor_type_is_professional",
    )

    response['data'] = [s for s in students]

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
    no_account_activation: bool = False
    response: Dict[str, Any] = {'data': [], 'msg': ''}

    admin_groups: List[bool] = [
        request.user.is_establishment_manager(),
        request.user.is_master_establishment_manager(),
        request.user.is_operator(),
        request.user.is_high_school_manager() and request.user.highschool and request.user.highschool.postbac_immersion,
    ]

    # request agreement setting
    try:
        request_agreement = GeneralSettings.get_setting("REQUEST_FOR_STUDENT_AGREEMENT")
    except:
        request_agreement = False

    # Display only accounts that are not activated yet (validation string is not empty)
    if any(admin_groups):
        no_account_activation = resolve(request.path_info).url_name == 'get_students_without_account_activation'

    if (
        request.user.is_high_school_manager()
        and request.user.highschool
        and not request.user.highschool.postbac_immersion
    ):
        highschool_id = request.user.highschool.id

    if highschool_id:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record__highschool',
            'high_school_student_record__post_bachelor_level',
            'high_school_student_record__bachelor_type',
            'high_school_student_record__origin_bachelor_type',
            'immersions',
            'groups',
        ).filter(
            high_school_student_record__highschool__id=highschool_id
        )
    else:
        students = ImmersionUser.objects.prefetch_related(
            'high_school_student_record__level',
            'high_school_student_record__highschool',
            'high_school_student_record__post_bachelor_level',
            'high_school_student_record__origin_bachelor_type',
            'student_record__level',
            'student_record__institution',
            'student_record__origin_bachelor_type',
            'visitor_record',
            'immersions',
            'groups',
        ).filter(
            groups__name__in=['ETU', 'LYC', 'VIS']
        )

    if no_account_activation:
        students = students.filter(validation_string__isnull=False)
    else:
        students = students.filter(validation_string__isnull=True)

    students = students.annotate(
        high_school_record_id=F('high_school_student_record__id'),
        student_record_id=F('student_record__id'),
        visitor_record_id=F('visitor_record__id'),
        user_type=Case(
            When(groups__name="LYC", then=Value(pgettext("person type", "High school student"))),
            When(groups__name="ETU", then=Value(pgettext("person type", "Student"))),
            When(groups__name="VIS", then=Value(pgettext("person type", "Visitor"))),
            default=Value(gettext("Unknown")),
        ),
        disabled=Coalesce(
            F('student_record__disability'),
            F('high_school_student_record__disability'),
            F('visitor_record__disability'),
        ),
        level=Coalesce(
            F('high_school_student_record__level__label'),
            F('student_record__level__label')
        ),
        birth_date=Coalesce(
            F('student_record__birth_date'),
            F('high_school_student_record__birth_date'),
            F('visitor_record__birth_date'),
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
            F('student_record__current_diploma'), F('high_school_student_record__post_bachelor_level__label')
        ),
        is_post_bachelor=F('high_school_student_record__level__is_post_bachelor'),
        student_origin_bachelor=F('student_record__origin_bachelor_type__label'),
        hs_origin_bachelor=F('high_school_student_record__origin_bachelor_type__label'),
        bachelor=F('high_school_student_record__bachelor_type__label'),
        registered=Count(F('immersions')),
        request_agreement=Value(request_agreement),
        allow_high_school_consultation=Case(
            When(Q(request_agreement=False), then=True),
            When(
                high_school_student_record__highschool__with_convention=True,
                then=F('high_school_student_record__allow_high_school_consultation'),
            ),
            default=True,
        ),
        record_status=Coalesce(
            F('high_school_student_record__validation'),
            F('student_record__validation'),
            F('visitor_record__validation'),
        ),
        record_status_display=Case(
            When(Q(record_status=0), then=Value(gettext('To complete'))),
            When(Q(record_status=1), then=Value(gettext('To validate'))),
            When(Q(record_status=2), then=Value(pgettext('record status', 'Validated'))),
            When(Q(record_status=3), then=Value(pgettext('record status', 'Rejected'))),
            When(Q(record_status=4), then=Value(gettext('To revalidate'))),
            When(Q(record_status=5), then=Value(gettext('Initialization (to complete)'))),
            default=Value("")
        )
    ).values()

    response['data'] = list(students)

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'INTER', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'CONS-STR')
def ajax_send_email(request):
    """
    Send an email to all students registered to a specific slot, or all contacts of all groups
    depending on the value of 'mode'
    """
    slot_id = request.POST.get('slot_id', None)
    send_copy = request.POST.get('send_copy', False) == "true"
    subject = request.POST.get('subject', "")
    body = request.POST.get('body', "")
    mode = request.POST.get('mode', "")

    response = {'error': False, 'msg': ''}

    if mode not in ['student', 'group']:
        response = {'error': True, 'msg': gettext("mode param ('group' or 'student') is required")}
        return JsonResponse(response, safe=False)

    if not slot_id:
        response = {'error': True, 'msg': gettext("Slot id is missing")}
        return JsonResponse(response, safe=False)

    if not body.strip():
        response = {'error': True, 'msg': gettext("Body is missing")}
        return JsonResponse(response, safe=False)

    if not subject.strip():
        response = {'error': True, 'msg': gettext("Subject is missing")}
        return JsonResponse(response, safe=False)

    try:
        slot = Slot.objects.get(pk=slot_id)

        slot_label = slot.get_label()
        date = date_format(slot.date, format='l d F Y', use_l10n=True)
        start_time = slot.start_time.isoformat(timespec='minutes')
        end_time = slot.end_time.isoformat(timespec='minutes')
        subject = f"{slot_label} : {date} ({start_time}-{end_time}) - {subject}"
    except Slot.DoesNotExist:
        response = {'error': True, 'msg': gettext("Invalid slot id")}
        return JsonResponse(response, safe=False)

    if mode == 'student':
        immersions = Immersion.objects.filter(slot_id=slot_id, cancellation_type__isnull=True)

        for immersion in immersions:
            recipient = immersion.student.email
            try:
                send_email(recipient, subject, body)
            except Exception:
                response['error'] = True
                response['msg'] += _("%s : error") % recipient
    else:
        # group mode
        immersions = ImmersionGroupRecord.objects.filter(slot_id=slot_id, cancellation_type__isnull=True)
        for immersion in immersions:
            for recipient in immersion.emails.split(","):
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
    slot_id = request.POST.get('slot_id')

    immersion_errors = []
    cancelled_immersions = 0
    msg = ""
    warning_msg = ""
    err = False
    err_msg = None
    today = datetime.datetime.today()
    now = timezone.now()
    user = request.user
    mail_returns = set()
    allowed_structures = user.get_authorized_structures()

    if not all([immersion_ids, reason_id, slot_id]):
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            slot = Slot.objects.get(pk=slot_id)
        except (Slot.DoesNotExist, ValueError):
            response = {'error': True, 'msg': gettext("Invalid slot id")}
            return JsonResponse(response, safe=False)

        try:
            json_data = json.loads(immersion_ids)
        except json.decoder.JSONDecodeError:
            response = {'error': True, 'msg': gettext("Invalid json decoding")}
            return JsonResponse(response, safe=False)

        # Check user rights on slot
        slot_establishment = slot.get_establishment()
        slot_structure = slot.get_structure()
        slot_highschool = slot.get_highschool()

        # Check authenticated user rights on this registration
        valid_conditions = [
            user.is_master_establishment_manager(),
            user.is_operator(),
            user.is_establishment_manager() and slot_establishment == user.establishment,
            user.is_structure_manager() and slot_structure in allowed_structures,
            user.is_high_school_manager()
            and (slot.course or slot.event)
            and slot_highschool
            and user.highschool == slot_highschool,
        ]


        if not any(valid_conditions):
            response = {'error': True, 'msg': _("You don't have enough privileges to cancel these registrations")}
            return JsonResponse(response, safe=False)

        # Check slot date
        if slot.date < today.date() or (slot.date == today.date() and slot.start_time < today.time()):
            response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
            return JsonResponse(response, safe=False)

        # Cancellation reason
        try:
            cancellation_reason = CancelType.objects.get(pk=reason_id)
        except CancelType.DoesNotExist:
            response = {'error': True, 'msg': _("Invalid cancellation reason #id")}
            return JsonResponse(response, safe=False)

        # Check usability
        managers = [
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager(),
            request.user.is_high_school_manager(),
            request.user.is_operator(),
            request.user.is_structure_manager(),
        ]

        students = [request.user.is_high_school_student(), request.user.is_visitor(), request.user.is_student()]

        if (
            not cancellation_reason.usable_for_students
            or (any(managers) and not cancellation_reason.usable_by_manager())
            or (any(students) and not cancellation_reason.usable_by_student())
        ):
            response = {'error': True, 'msg': _("You can't use this cancellation reason")}
            return JsonResponse(response, safe=False)

        for immersion_id in json_data:
            try:
                immersion = Immersion.objects.get(pk=immersion_id, slot=slot)
                immersion.cancellation_type = cancellation_reason
                immersion.cancellation_date = timezone.now()
                immersion.save()

                cancelled_immersions += 1

                ret = immersion.student.send_message(
                    request, 'IMMERSION_ANNUL', immersion=immersion, slot=immersion.slot
                )
                if ret:
                    mail_returns.add(ret)

            except Immersion.DoesNotExist:
                immersion_errors.append(_("Immersion %s not found") % immersion_id)

        # If slot registrations are over (check limit date), also send a message to speakers
        # and structure managers
        if slot.registration_limit_date < now:
            for speaker in slot.speakers.all():
                ret = speaker.send_message(request, 'IMMERSION_ANNULATION_INT', slot=slot)
                if ret:
                    mail_returns.add(ret)

            # structure managers
            slot_structure = slot.get_structure()

            if slot_structure:
                for notify in RefStructuresNotificationsSettings.objects.filter(structures=slot_structure):
                    ret = notify.user.send_message(None, "IMMERSION_ANNULATION_STR", slot=slot)
                    if ret:
                        mail_returns.add(ret)

            # High school managers
            highschool = slot.get_highschool()

            if highschool:
                # Get this high school managers
                # Check the message preferences (False by default)
                # Send the same message template
                for manager in highschool.users.filter(groups__name='REF-LYC'):
                    if manager.get_preference("RECEIVE_REGISTERED_STUDENTS_LIST", False):
                        ret = manager.send_message(None, "IMMERSION_ANNULATION_STR", slot=slot)
                        if ret:
                            mail_returns.add(ret)

        # Return warnings and errors
        if cancelled_immersions:
            msg = _("%s immersion(s) cancelled") % cancelled_immersions

        if mail_returns:
            err = True
            warning_msg = _("Warning : some confirmation emails have not been sent :") + " <br><ul>"
            for ret in mail_returns:
                warning_msg += f"<li>{ret}</li>"
            warning_msg += "</ul>"
            msg += f"<br>{warning_msg}"

        if immersion_errors:
            err = True
            error_msg = _("Immersions warnings") + " :<br><ul>"
            for immersion_error in immersion_errors:
                error_msg += f"<li>{immersion_error}</li>"
            error_msg += "</ul>"
            msg += f"<br>{error_msg}"

        response = {'error': err, 'msg': msg}

    return JsonResponse(response, safe=False)


@is_ajax_request
@is_post_request
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def ajax_groups_batch_cancel_registration(request):
    """
    Cancel registrations to groups immersions slots
    """
    groups_immersion_ids = request.POST.get('groups_immersion_ids')
    reason_id = request.POST.get('reason_id')
    slot_id = request.POST.get('slot_id')

    immersion_errors = []
    cancelled_immersions = 0
    msg = ""
    warning_msg = ""
    err = False
    err_msg = None
    today = datetime.datetime.today()
    now = timezone.now()
    user = request.user
    mail_returns = set()
    allowed_structures = user.get_authorized_structures()

    if not all([groups_immersion_ids, reason_id, slot_id]):
        response = {'error': True, 'msg': gettext("Invalid parameters")}
    else:
        try:
            slot = Slot.objects.get(pk=slot_id)
        except (Slot.DoesNotExist, ValueError):
            response = {'error': True, 'msg': gettext("Invalid slot id")}
            return JsonResponse(response, safe=False)

        try:
            json_data = json.loads(groups_immersion_ids)
        except json.decoder.JSONDecodeError:
            response = {'error': True, 'msg': gettext("Invalid json decoding")}
            return JsonResponse(response, safe=False)

        # Check user rights on slot
        slot_establishment = slot.get_establishment()
        slot_structure = slot.get_structure()
        slot_highschool = slot.get_highschool()
        # Check if highschool manager can cancel his groups registrations from his highschool
        other_hs_count = (
            ImmersionGroupRecord.objects.filter(pk__in=json_data, slot=slot).exclude(highschool=user.highschool).count()
        )

        # Check authenticated user rights on this registration
        valid_conditions = [
            user.is_master_establishment_manager(),
            user.is_operator(),
            user.is_establishment_manager() and slot_establishment == user.establishment,
            user.is_structure_manager() and slot_structure in allowed_structures,
            user.is_high_school_manager()
            and (slot.course or slot.event)
            and slot_highschool
            and user.highschool == slot_highschool,
            user.is_high_school_manager() and (slot.course or slot.event) and other_hs_count == 0,
        ]

        if not any(valid_conditions):
            response = {'error': True, 'msg': _("You don't have enough privileges to cancel these registrations")}
            return JsonResponse(response, safe=False)

        # Check slot date
        if slot.date < today.date() or (slot.date == today.date() and slot.start_time < today.time()):
            response = {'error': True, 'msg': _("Past immersion cannot be cancelled")}
            return JsonResponse(response, safe=False)

        # Cancellation reason
        # TODO : check that the reason is compatible with groups immersions
        try:
            cancellation_reason = CancelType.objects.get(pk=reason_id)
        except CancelType.DoesNotExist:
            response = {'error': True, 'msg': _("Invalid cancellation reason #id")}
            return JsonResponse(response, safe=False)

        # Check usability for groups
        managers = [
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager(),
            request.user.is_high_school_manager(),
            request.user.is_operator(),
            request.user.is_structure_manager(),
        ]

        students = [request.user.is_high_school_student(), request.user.is_visitor(), request.user.is_student()]

        if (
            not cancellation_reason.usable_for_groups
            or (any(managers) and not cancellation_reason.usable_by_manager())
            or (any(students) and not cancellation_reason.usable_by_student())
        ):
            response = {'error': True, 'msg': _("You can't use this cancellation reason")}
            return JsonResponse(response, safe=False)

        for immersion_id in json_data:
            try:
                group_immersion = ImmersionGroupRecord.objects.get(pk=immersion_id, slot=slot)
                group_immersion.cancellation_type = cancellation_reason
                group_immersion.cancellation_date = timezone.now()
                group_immersion.save()

                cancelled_immersions += 1

                # Send message to group contacts
                msg, error = group_immersion.send_message(request, 'IMMERSION_ANNUL')

                if error:
                    mail_returns.add(msg)

            except ImmersionGroupRecord.DoesNotExist:
                immersion_errors.append(_("Group immersion %s not found") % immersion_id)

        # If slot registrations are over (check limit date), also send a message to speakers
        # and structure managers
        if slot.registration_limit_date < now:
            for speaker in slot.speakers.all():
                ret = speaker.send_message(request, 'IMMERSION_ANNULATION_INT', slot=slot)
                if ret:
                    mail_returns.add(ret)

            # structure managers
            slot_structure = slot.get_structure()

            if slot_structure:
                for notify in RefStructuresNotificationsSettings.objects.filter(structures=slot_structure):
                    ret = notify.user.send_message(None, "IMMERSION_ANNULATION_STR", slot=slot)
                    if ret:
                        mail_returns.add(ret)

            # High school managers
            highschool = slot.get_highschool()

            if highschool:
                # Get this high school managers
                # Check the message preferences (False by default)
                # Send the same message template
                for manager in highschool.users.filter(groups__name='REF-LYC'):
                    if manager.get_preference("RECEIVE_REGISTERED_STUDENTS_LIST", False):
                        ret = manager.send_message(None, "IMMERSION_ANNULATION_STR", slot=slot)
                        if ret:
                            mail_returns.add(ret)

        # Return warnings and errors
        if cancelled_immersions:
            msg = _("%s immersion(s) cancelled") % cancelled_immersions

        if mail_returns:
            err = True
            warning_msg = _("Warning : some confirmation emails have not been sent :") + " <br><ul>"
            for ret in mail_returns:
                warning_msg += f"<li>{ret}</li>"
            warning_msg += "</ul>"
            msg += f"<br>{warning_msg}"

        if immersion_errors:
            err = True
            error_msg = _("Immersions warnings") + " :<br><ul>"
            for immersion_error in immersion_errors:
                error_msg += f"<li>{immersion_error}</li>"
            error_msg += "</ul>"
            msg += f"<br>{error_msg}"

        response = {'error': err, 'msg': msg}

    return JsonResponse(response, safe=False)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC', 'REF-TEC')
def get_csv_structures(request):
    filters = {}
    slots_filters = Q()
    content = []
    today = _date(datetime.datetime.today(), 'Ymd')

    structures = request.user.get_authorized_structures()
    structure_label = structures[0].label.replace(' ', '_') if structures.count() == 1 else 'structures'
    t = request.GET.get('type')
    infield_separator = '|'

    if not t:
        raise Http404

    registered_students_count = (
        Immersion.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True)
        .order_by()
        .annotate(count=Func(F('id'), function='Count'))
        .values('count')
    )

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
                _('period'),
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
                'establishment',
                'structure',
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('training domain'),
                _('training subdomain'),
                _('training'),
                _('course'),
                _('course_type'),
                _('period'),
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

            filters['course__structure__in'] = request.user.establishment.structures.all()

            fields = [
                'structure',
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        elif request.user.is_high_school_manager():

            header = [
                _('training domain'),
                _('training subdomain'),
                _('training'),
                _('course'),
                _('course_type'),
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('meeting place'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]
            filters['course__highschool'] = request.user.highschool

            fields = [
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        elif request.user.is_structure_manager():
            header = [
                _('structure'),
                _('training domain'),
                _('training subdomain'),
                _('training'),
                _('course'),
                _('course_type'),
                _('period'),
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
            filters['course__structure__in'] = structures

            fields = [
                'structure',
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        slots = (
            Slot.objects.prefetch_related(
                'immersions',
                'speakers',
                'period',
                'course',
                'course__establishment',
                'course__structure',
                'course__highschool',
                'course__training__training_subdomains',
            )
            .filter(**filters, published=True, course__isnull=False)
            .order_by('date', 'start_time')
        )

        content = slots.annotate(
            establishment=Coalesce(
                F('course__structure__establishment__label'),
                Concat(
                    F('course__highschool__label'),
                    Value(' - '),
                    F('course__highschool__city'),
                    output_field=CharField(),
                ),
            ),
            structure=F('course__structure__label'),
            domains=StringAgg(
                F('course__training__training_subdomains__training_domain__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            subdomains=StringAgg(
                F('course__training__training_subdomains__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            training_label=F('course__training__label'),
            course_label=F('course__label'),
            slot_course_type=F('course_type__label'),
            slot_period_label=F('period__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(place=Slot.FACE_TO_FACE, then=F('room')),
                When(place=Slot.OUTSIDE, then=F('room')),
                When(place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(*fields)

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
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'establishment',
                'structure',
                'type',
                'label',
                'desc',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
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
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            slots_filters = Q(event__establishment=request.user.establishment) | Q(
                event__structure__in=request.user.establishment.structures.all()
            )

            fields = [
                'structure',
                'type',
                'label',
                'desc',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
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
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            filters['event__structure__in'] = structures

            fields = [
                'structure',
                'type',
                'label',
                'desc',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        elif request.user.is_high_school_manager():

            header = [
                _('event type'),
                _('label'),
                _('description'),
                _('meeting place'),
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            filters['event__highschool'] = request.user.highschool

            fields = [
                'type',
                'label',
                'desc',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        slots = (
            Slot.objects.prefetch_related(
                'immersions',
                'speakers',
                'period',
                'event',
                'event__establishment',
                'event__structure',
                'event__highschool'
            )
            .filter(slots_filters, **filters, published=True, event__isnull=False)
            .order_by('date', 'start_time')
        )

        content = slots.annotate(
            establishment=Coalesce(
                F('event__establishment__label'),
                Concat(
                    F('event__highschool__label'), Value(' - '), F('event__highschool__city'), output_field=CharField()
                ),
            ),
            structure=F('event__structure__label'),
            type=F('event__event_type__label'),
            label=F('event__label'),
            desc=F('event__description'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(place=Slot.FACE_TO_FACE, then=F('room')),
                When(place=Slot.OUTSIDE, then=F('room')),
                When(place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            slot_period_label=F('period__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(*fields)

    # Forge CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{structure_label}_{label}_{today}.csv"'
    # Dirty hack for ms-excel to recognize utf-8
    response.write(codecs.BOM_UTF8)
    writer = csv.writer(response, **settings.CSV_OPTIONS)
    writer.writerow(header)
    writer.writerows(content)

    return response


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def get_csv_highschool(request):
    response = HttpResponse(content_type='text/csv')
    today = _date(datetime.datetime.today(), 'Ymd')
    request_agreement = GeneralSettings.get_setting("REQUEST_FOR_STUDENT_AGREEMENT")
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
        _('course/event label'),
        _('period'),
        _('date'),
        _('start_time'),
        _('end_time'),
        _('campus'),
        _('building'),
        _('meeting place'),
        _('attendance status'),
        _('additional information'),
        _('high school consultancy agreement'),
        _('registrations visibility agreement'),
    ]

    users_filters = Q(immersions__cancellation_type__isnull=True)

    students = (
        ImmersionUser.objects.prefetch_related(
            'high_school_student_record__level',
            'high_school_student_record__highschool',
            'high_school_student_record__bachelor_type',
            'immersions',
            'immersions__slot__period',
        )
        .filter(
            users_filters,
            groups__name='LYC',
            high_school_student_record__highschool__id=hs.id,
        )
        .order_by('last_name', 'first_name')
    )

    attendance_status_choices = dict(Immersion._meta.get_field('attendance_status').flatchoices)
    attendance_status_whens = [
        When(immersions__attendance_status=k, then=Value(str(v))) for k, v in attendance_status_choices.items()
    ]

    if request_agreement:

        agreed_students = (
            students.filter(high_school_student_record__allow_high_school_consultation=True)
            .annotate(
                student_last_name=F('last_name'),
                student_first_name=F('first_name'),
                student_birth_date=ExpressionWrapper(
                    Func(F('high_school_student_record__birth_date'), Value('DD/MM/YYYY'), function='to_char'),
                    output_field=CharField(),
                ),
                student_bachelor_type=F('high_school_student_record__bachelor_type__label'),
                slot_establishment=Coalesce(
                    F('immersions__slot__course__structure__establishment__label'),
                    F('immersions__slot__event__establishment__label'),
                ),
                slot_type=Case(
                    When(immersions__slot__course__isnull=False, then=Value(pgettext("slot type", "Course"))),
                    When(immersions__slot__event__isnull=False, then=Value(pgettext("slot type", "Event"))),
                    When(immersions__isnull=False, then=Value("")),
                ),
                domains=StringAgg(
                    F('immersions__slot__course__training__training_subdomains__training_domain__label'),
                    infield_separator,
                    default=Value(''),
                    output_field=CharField(),
                    distinct=True,
                ),
                subdomains=StringAgg(
                    F('immersions__slot__course__training__training_subdomains__label'),
                    infield_separator,
                    default=Value(''),
                    output_field=CharField(),
                    distinct=True,
                ),
                training_label=F('immersions__slot__course__training__label'),
                slot_label=Coalesce(
                    F('immersions__slot__course__label'),
                    F('immersions__slot__event__label'),
                ),
                slot_period_label=F('immersions__slot__period__label'),
                slot_date=ExpressionWrapper(
                    Func(F('immersions__slot__date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
                ),
                slot_start_time=F('immersions__slot__start_time'),
                slot_end_time=F('immersions__slot__end_time'),
                slot_campus_label=F('immersions__slot__campus__label'),
                slot_building=F('immersions__slot__building__label'),
                slot_room=Case(
                    When(immersions__slot__place=Slot.FACE_TO_FACE, then=F('immersions__slot__room')),
                    When(immersions__slot__place=Slot.OUTSIDE, then=F('immersions__slot__room')),
                    When(immersions__slot__place=Slot.REMOTE, then=Value(gettext('Remote'))),
                ),
                attendance=Case(*attendance_status_whens, output_field=CharField()),
                informations=F('immersions__slot__additional_information'),
                detail_consultancy=Case(
                    When(high_school_student_record__allow_high_school_consultation=True, then=Value(gettext('Yes'))),
                    When(high_school_student_record__allow_high_school_consultation=False, then=Value(gettext('No'))),
                ),
                detail_registrations=Case(
                    When(high_school_student_record__visible_immersion_registrations=True, then=Value(gettext('Yes'))),
                    When(high_school_student_record__visible_immersion_registrations=False, then=Value(gettext('No'))),
                ),
            )
            .values_list(
                'student_last_name',
                'student_first_name',
                'student_birth_date',
                'high_school_student_record__level__label',
                'high_school_student_record__class_name',
                'student_bachelor_type',
                'slot_establishment',
                'slot_type',
                'domains',
                'subdomains',
                'training_label',
                'slot_label',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus_label',
                'slot_building',
                'slot_room',
                'attendance',
                'informations',
                'detail_consultancy',
                'detail_registrations',
            )
        )
        not_agreed_students = (
            students.filter(high_school_student_record__allow_high_school_consultation=False)
            .annotate(
                student_last_name=F('last_name'),
                student_first_name=F('first_name'),
                student_birth_date=ExpressionWrapper(
                    Func(F('high_school_student_record__birth_date'), Value('DD/MM/YYYY'), function='to_char'),
                    output_field=CharField(),
                ),
                student_bachelor_type=F('high_school_student_record__bachelor_type__label'),
                slot_establishment=Value(''),
                slot_type=Value(''),
                domains=Value(''),
                subdomains=Value(''),
                training_label=Value(''),
                slot_label=Value(''),
                slot_period_label=Value(''),
                slot_date=Value(''),
                slot_start_time=Value(''),
                slot_end_time=Value(''),
                slot_campus_label=Value(''),
                slot_building=Value(''),
                slot_room=Value(''),
                attendance=Value(''),
                informations=Value(''),
                detail_consultancy=Case(
                    When(high_school_student_record__allow_high_school_consultation=True, then=Value(gettext('Yes'))),
                    When(high_school_student_record__allow_high_school_consultation=False, then=Value(gettext('No'))),
                ),
                detail_registrations=Case(
                    When(high_school_student_record__visible_immersion_registrations=True, then=Value(gettext('Yes'))),
                    When(high_school_student_record__visible_immersion_registrations=False, then=Value(gettext('No'))),
                ),
            )
            .values_list(
                'student_last_name',
                'student_first_name',
                'student_birth_date',
                'high_school_student_record__level__label',
                'high_school_student_record__class_name',
                'student_bachelor_type',
                'slot_establishment',
                'slot_type',
                'domains',
                'subdomains',
                'training_label',
                'slot_label',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus_label',
                'slot_building',
                'slot_room',
                'attendance',
                'informations',
                'detail_consultancy',
                'detail_registrations',
            )
        )

        content = chain(agreed_students, not_agreed_students.distinct())

    else:
        content = students.annotate(
            student_last_name=F('last_name'),
            student_first_name=F('first_name'),
            student_birth_date=ExpressionWrapper(
                Func(F('high_school_student_record__birth_date'), Value('DD/MM/YYYY'), function='to_char'),
                output_field=CharField(),
            ),
            student_bachelor_type=F('high_school_student_record__bachelor_type__label'),
            slot_establishment=Coalesce(
                F('immersions__slot__course__structure__establishment__label'),
                F('immersions__slot__event__establishment__label'),
            ),
            slot_type=Case(
                When(immersions__slot__course__isnull=False, then=Value(pgettext("slot type", "Course"))),
                When(immersions__slot__event__isnull=False, then=Value(pgettext("slot type", "Event"))),
                When(immersions__isnull=False, then=Value("")),
            ),
            domains=StringAgg(
                F('immersions__slot__course__training__training_subdomains__training_domain__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            subdomains=StringAgg(
                F('immersions__slot__course__training__training_subdomains__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            training_label=F('immersions__slot__course__training__label'),
            slot_period_label=F('immersions__slot__period__label'),
            slot_label=Coalesce(
                F('immersions__slot__course__label'),
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
                When(immersions__slot__place=Slot.FACE_TO_FACE, then=F('immersions__slot__room')),
                When(immersions__slot__place=Slot.OUTSIDE, then=F('immersions__slot__room')),
                When(immersions__slot__place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
            informations=F('immersions__slot__additional_information'),
            detail_consultancy=Case(
                When(high_school_student_record__allow_high_school_consultation=True, then=Value(gettext('Yes'))),
                When(high_school_student_record__allow_high_school_consultation=False, then=Value(gettext('No'))),
            ),
            detail_registrations=Case(
                When(high_school_student_record__visible_immersion_registrations=True, then=Value(gettext('Yes'))),
                When(high_school_student_record__visible_immersion_registrations=False, then=Value(gettext('No'))),
            ),
        ).values_list(
            'student_last_name',
            'student_first_name',
            'student_birth_date',
            'high_school_student_record__level__label',
            'high_school_student_record__class_name',
            'student_bachelor_type',
            'slot_establishment',
            'slot_type',
            'domains',
            'subdomains',
            'training_label',
            'slot_label',
            'slot_period_label',
            'slot_date',
            'slot_start_time',
            'slot_end_time',
            'slot_campus_label',
            'slot_building',
            'slot_room',
            'attendance',
            'informations',
            'detail_consultancy',
            'detail_registrations',
        )

    # Dirty hack for ms-excel to recognize utf-8
    response.write(codecs.BOM_UTF8)
    # Forge csv file and return it
    writer = csv.writer(response, **settings.CSV_OPTIONS)
    writer.writerow(header)
    writer.writerows(list(content))

    return response


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def get_csv_anonymous(request):
    response = HttpResponse(content_type='text/csv')
    today = _date(datetime.datetime.today(), 'Ymd')
    infield_separator = '|'
    t = request.GET.get('type')
    filters = {}
    if not t:
        raise Http404

    registered_students_count = (
        Immersion.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True)
        .order_by()
        .annotate(count=Func(F('id'), function='Count'))
        .values('count')
    )

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
                _('period'),
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
                'establishment',
                'structure',
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        elif request.user.is_establishment_manager():

            header = [
                _('structure'),
                _('training domain'),
                _('training subdomain'),
                _('training'),
                _('course'),
                _('course_type'),
                _('period'),
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
                'structure',
                'domains',
                'subdomains',
                'training_label',
                'course_label',
                'slot_course_type',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

            filters['course__structure__in'] = request.user.establishment.structures.all()

        content = []

        slots = Slot.objects.prefetch_related(
            'immersions',
            'speakers',
            'period',
            'course',
            'course__establishment',
            'course__structure',
            'course__highschool',
            'student__visitor_record',
            'student__student_record',
            'student__high_school_student_record',
            'course__training__training_subdomains',
        ).filter(**filters, published=True, course__isnull=False)

        content = slots.annotate(
            establishment=Coalesce(
                F('course__structure__establishment__label'),
                Concat(
                    F('course__highschool__label'),
                    Value(' - '),
                    F('course__highschool__city'),
                    output_field=CharField(),
                ),
            ),
            structure=F('course__structure__label'),
            domains=StringAgg(
                F('course__training__training_subdomains__training_domain__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            subdomains=StringAgg(
                F('course__training__training_subdomains__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            training_label=F('course__training__label'),
            course_label=F('course__label'),
            slot_course_type=F('course_type__label'),
            slot_period_label=F('period__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(place=Slot.FACE_TO_FACE, then=F('room')),
                When(place=Slot.OUTSIDE, then=F('room')),
                When(place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(*fields)

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
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]

            fields = [
                'establishment',
                'structure',
                'type',
                'label',
                'desc',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
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
                _('period'),
                _('date'),
                _('start_time'),
                _('end_time'),
                _('speakers'),
                _('registration number'),
                _('place number'),
                _('additional information'),
            ]
            filters['event__establishment'] = request.user.establishment

            fields = [
                'structure',
                'type',
                'label',
                'desc',
                'slot_campus',
                'slot_building',
                'slot_room',
                'slot_period_label',
                'slot_date',
                'slot_start_time',
                'slot_end_time',
                'slot_speakers',
                'registered',
                'slot_n_places',
                'info',
            ]

        content = []

        slots = Slot.objects.prefetch_related(
            'immersions',
            'speakers',
            'period',
            'event',
            'event__establishment',
            'event__structure',
            'event__highschool',
            'student__visitor_record',
            'student__student_record',
            'student__high_school_student_record',
        ).filter(**filters, published=True, event__isnull=False)

        content = slots.annotate(
            establishment=Coalesce(
                F('event__establishment__label'),
                Concat(
                    F('event__highschool__label'), Value(' - '), F('event__highschool__city'), output_field=CharField()
                ),
            ),
            structure=F('event__structure__label'),
            type=F('event__event_type__label'),
            label=F('event__label'),
            desc=F('event__description'),
            slot_campus=F('campus__label'),
            slot_building=F('building__label'),
            slot_room=Case(
                When(place=Slot.FACE_TO_FACE, then=F('room')),
                When(place=Slot.OUTSIDE, then=F('room')),
                When(place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            slot_period_label=F('period__label'),
            slot_date=ExpressionWrapper(
                Func(F('date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('start_time'),
            slot_end_time=F('end_time'),
            slot_speakers=StringAgg(
                Concat(F('speakers__last_name'), Value(' '), F('speakers__first_name')),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            registered=Subquery(registered_students_count),
            slot_n_places=F('n_places'),
            info=(F('additional_information')),
        ).values_list(*fields)

    # Export registrations
    if t == 'registration':
        label = _('anonymous_registrations')

        header = [
            _('anonymous identity'),
            _('registrant profile'),
            _('level'),
            _('origin institution'),
            _('city'),
            _("bachelor type"),
            _('establishment'),
            _('slot type'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('label'),
            _('type'),
            _('period'),
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
            filters['slot__course__structure__in'] = request.user.establishment.structures.all()

        immersions = Immersion.objects.prefetch_related(
            'slot',
            'student',
            'slot__period',
            'slot__event__establishment',
            'slot__event__structure',
            'slot__event__highschool',
            'slot__speakers',
            'slot__course__structure',
            'slot__course__highschool',
            'student__visitor_record',
            'student__student_record__origin_bachelor_type',
            'student__student_record__institution',
            'student__high_school_student_record__origin_bachelor_type',
            'student__high_school_student_record__level',
            'student__high_school_student_record__highschool',
        ).filter(cancellation_type__isnull=True, slot__published=True, **filters)

        faker = Faker(settings.LANGUAGE_CODE)
        Faker.seed(4321)
        fake_names = {i: faker.name() for i in immersions.values_list('student__id', flat=True)}
        fake_names_whens = [When(student__id=k, then=Value(fake_names[k])) for k, v in fake_names.items()]

        attendance_status_choices = dict(Immersion._meta.get_field('attendance_status').flatchoices)
        attendance_status_whens = [
            When(attendance_status=k, then=Value(str(v))) for k, v in attendance_status_choices.items()
        ]

        content = immersions.annotate(
            fake_name=Case(*fake_names_whens, output_field=CharField()),
            type=Case(
                When(
                    student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student")),
                ),
                When(student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value(gettext("Unknown")),
            ),
            level=Coalesce(
                F('student__high_school_student_record__level__label'),
                F('student__student_record__level__label')
            ),
            institution=Coalesce(
                F('student__high_school_student_record__highschool__label'),
                F('student__student_record__institution__label'),
                F('student__student_record__uai_code'),
                Value('')
            ),
            city=Coalesce(
                F('student__high_school_student_record__highschool__city'),
                F('student__student_record__institution__city'),
                Value('')
            ),
            origin_bachelor_type=Coalesce(
                F('student__high_school_student_record__bachelor_type__label'),
                F('student__student_record__origin_bachelor_type__label'),
            ),
            establishment=Coalesce(
                F('slot__course__highschool__label'),
                F('slot__course__structure__establishment__label'),
                F('slot__event__establishment__label'),
            ),
            slot_type=Case(
                When(slot__course__isnull=False, then=Value(pgettext("slot type", "Course"))),
                When(slot__event__isnull=False, then=Value(pgettext("slot type", "Event"))),
            ),
            domains=StringAgg(
                F('slot__course__training__training_subdomains__training_domain__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            subdomains=StringAgg(
                F('slot__course__training__training_subdomains__label'),
                infield_separator,
                default=Value(''),
                output_field=CharField(),
                distinct=True,
            ),
            training_label=F('slot__course__training__label'),
            slot_label=Coalesce(
                F('slot__course__label'),
                F('slot__event__label'),
            ),
            slot_course_type=Coalesce(
                F('slot__course_type__label'),
                F('slot__event__event_type__label'),
            ),
            slot_period_label=F('slot__period__label'),
            slot_date=ExpressionWrapper(
                Func(F('slot__date'), Value('DD/MM/YYYY'), function='to_char'), output_field=CharField()
            ),
            slot_start_time=F('slot__start_time'),
            slot_end_time=F('slot__end_time'),
            slot_campus_label=F('slot__campus__label'),
            slot_building=F('slot__building__label'),
            slot_room=Case(
                When(slot__place=Slot.FACE_TO_FACE, then=F('slot__room')),
                When(slot__place=Slot.OUTSIDE, then=F('slot__room')),
                When(slot__place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            attendance=Case(*attendance_status_whens, output_field=CharField()),
            informations=F('slot__additional_information'),
        ).values_list(
            'fake_name',
            'type',
            'level',
            'institution',
            'city',
            'origin_bachelor_type',
            'establishment',
            'slot_type',
            'domains',
            'subdomains',
            'training_label',
            'slot_label',
            'slot_course_type',
            'slot_period_label',
            'slot_date',
            'slot_start_time',
            'slot_end_time',
            'slot_campus_label',
            'slot_building',
            'slot_room',
            'attendance',
            'informations',
        )

    # Forge csv
    response['Content-Disposition'] = f'attachment; filename={label}_{today}.csv'
    # Dirty hack for ms-excel to recognize utf-8a
    response.write(codecs.BOM_UTF8)
    writer = csv.writer(response, **settings.CSV_OPTIONS)
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
    subject = request.POST.get('subject', "").strip()
    body = request.POST.get('body', "").strip()
    lastname = request.POST.get('lastname', "").strip().capitalize()
    firstname = request.POST.get('firstname', "").strip().capitalize()
    email = request.POST.get('email', "").strip()
    notify_user = False

    try:
        recipient = get_general_setting('MAIL_CONTACT_REF_ETAB')
    except (NameError, ValueError):
        logger.error('MAIL_CONTACT_REF_ETAB not configured properly in settings')
        response = {'error': True, 'msg': gettext("Config parameter not found")}
        return JsonResponse(response, safe=False)

    response = {'error': False, 'msg': ''}

    if not all([subject, body, lastname, firstname, email]):
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
def ajax_get_student_presence(request):
    """
    List of registrations to every slot
    GET params: from_date, until_date, place (0:face to face or 2:outside of the establishment)
    """
    response = {'data': [], 'msg': ''}

    from_date = request.GET.get('from_date')
    until_date = request.GET.get('until_date')

    try:
        place = int(request.GET.get('place', 0))
    except:
        place = 0

    filters = {'slot__place': place}
    immersions_filters = Q()

    if from_date and from_date != "None":
        filters["slot__date__gte"] = from_date

    if until_date and until_date != "None":
        filters["slot__date__lte"] = until_date

    if request.user.is_superuser or request.user.is_operator() or request.user.is_master_establishment_manager():
        immersions_filters = (
            Q(slot__event__isnull=False, slot__place=Slot.FACE_TO_FACE)
            | Q(slot__event__isnull=False, slot__place=Slot.OUTSIDE)
            | Q(slot__course__isnull=False)
        )

    elif request.user.is_establishment_manager() or request.user.is_legal_department_staff():
        structures = request.user.establishment.structures.all()

        immersions_filters = (
            Q(slot__course__structure__in=structures)
            | Q(slot__event__structure__in=structures, slot__place=Slot.FACE_TO_FACE)
            | Q(slot__event__structure__in=structures, slot__place=Slot.OUTSIDE)
        )
    elif request.user.is_high_school_manager():
        if not request.user.highschool.postbac_immersion:
            # Not allowed to view registrants
            return JsonResponse(response, safe=False)

        immersions_filters = (
                Q(slot__course__highschool=request.user.highschool)
                | Q(slot__event__highschool=request.user.highschool)
        )

    immersions = (
        Immersion.objects.prefetch_related(
            'slot__campus',
            'slot__building',
            'slot__course__structure__establishment',
            'slot__event__establishment',
            'slot__course__structure',
            'slot__event__structure',
            'student__high_school_student_record__highschool',
            'student__student_record__institution',
            'student__visitor_record',
        )
        .filter(immersions_filters, **filters, cancellation_type__isnull=True)
        .annotate(
            datatype=Value('student'),
            date=F('slot__date'),
            start_time=F('slot__start_time'),
            end_time=F('slot__end_time'),
            student_profile=Case(
                When(
                    student__high_school_student_record__isnull=False,
                    then=Value(pgettext("person type", "High school student")),
                ),
                When(student__student_record__isnull=False, then=Value(pgettext("person type", "Student"))),
                When(student__visitor_record__isnull=False, then=Value(pgettext("person type", "Visitor"))),
                default=Value(gettext("Unknown")),
            ),
            disabled=Coalesce(
                F('student__high_school_student_record__disability'),
                F('student__student_record__disability'),
                F('student__visitor_record__disability'),
            ),
            institution=Coalesce(
                F('student__high_school_student_record__highschool__label'),
                F('student__student_record__institution__label'),
                F('student__student_record__uai_code'),
                Value(''),
            ),
            first_name=F('student__first_name'),
            last_name=F('student__last_name'),
            phone=Coalesce(
                F('student__high_school_student_record__phone'),
                F('student__student_record__phone'),
                F('student__visitor_record__phone'),
                Value(''),
            ),
            email=F('student__email'),
            campus=F('slot__campus__label'),
            building=F('slot__building__label'),
            meeting_place=Case(
                When(slot__place=Slot.FACE_TO_FACE, then=F('slot__room')),
                When(slot__place=Slot.OUTSIDE, then=F('slot__room')),
                default=Value(gettext('Remote')),
            ),
            establishment=Coalesce(
                F('slot__course__structure__establishment__label'),
                F('slot__event__establishment__label'),
                F('slot__course__highschool__label'),
                F('slot__event__highschool__label'),
            ),
            structure=Coalesce(
                F('slot__course__structure__label'),
                F('slot__event__structure__label'),
            )
        )
        .values()
    )

    # Build a second queryset with group immersions
    group_immersions = (
        ImmersionGroupRecord.objects.prefetch_related(
            'slot__campus',
            'slot__building',
            'slot__course__structure__establishment',
            'slot__event__establishment',
            'slot__course__structure',
            'slot__event__structure'
            'highschool'
        )
        .filter(immersions_filters, **filters, cancellation_type__isnull=True)
        .annotate(
            datatype=Value('group'),
            date=F('slot__date'),
            start_time=F('slot__start_time'),
            end_time=F('slot__end_time'),
            student_profile=Value(gettext('Group')),
            institution=F('highschool__label'),
            campus=F('slot__campus__label'),
            building=F('slot__building__label'),
            meeting_place=Case(
                When(slot__place=Slot.FACE_TO_FACE, then=F('slot__room')),
                When(slot__place=Slot.OUTSIDE, then=F('slot__room')),
                default=Value(gettext('Remote')),
            ),
            disabled=Value(''),
            establishment=Coalesce(
                F('slot__course__structure__establishment__label'),
                F('slot__event__establishment__label'),
                F('slot__course__highschool__label'),
                F('slot__event__highschool__label'),
            ),
            structure=Coalesce(
                F('slot__course__structure__label'),
                F('slot__event__structure__label'),
            )
        )
        .values()
    )

    # Return a list with mixed values, 'datatype' field must be used to know
    # what to display in datatable
    response['data'] = list(immersions) + list(group_immersions)

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
    alert, created = UserCourseAlert.objects.get_or_create(email=email, course=course, defaults={'email_sent': False})

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
    permission_classes = [
        IsVisitorPermissions | IsHighSchoolStudentPermissions | IsStudentPermissions | CustomDjangoModelPermissions
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = UserCourseAlert.objects.prefetch_related(
            'course__training__training_subdomains__training_domain'
        ).filter(email=user.email)

        return queryset


class PeriodList(generics.ListAPIView):
    """
    Immersion periods
    """

    serializer_class = PeriodSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        queryset = Period.objects.all()

        if "date" in self.request.query_params:
            _date = self.request.query_params.get("date")
            error = False

            try:
                formated_date = datetime.datetime.strptime(_date, '%Y/%m/%d')
            except ValueError:
                error = True

            if error:
                try:
                    formated_date = datetime.datetime.strptime(_date, '%d/%m/%Y')
                except ValueError:
                    return Period.objects.none()

            queryset = queryset.filter(immersion_start_date__lte=formated_date, immersion_end_date__gte=formated_date)

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
                immersions_nb = (
                    Immersion.objects.prefetch_related('slot')
                    .filter(student=record.student.pk, cancellation_type__isnull=True)
                    .count()
                )

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
                "registrations": [_('Yes') if r > 0 else _('No') for r in registrations],
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

@login_required
@is_post_request
def notify_disability_referent(request):
    """
    On slot registration, notify establishment disability referent
    This is called when 'on demand' has been set
    """
    response = {'data': [], 'msg': '', 'error': False}

    user = request.user
    slot_id = request.POST.get('slot_id')
    str_ref_only = request.POST.get('str_ref_only') == "true"
    today = datetime.datetime.today().date()

    try:
        slot = Slot.objects.get(pk=slot_id)
    except Slot.DoesNotExist:
        # Slot does not exist : nothing to do
        response = {"error": True, "msg": _("Slot not found")}
        return JsonResponse(response, safe=False)

    immersion = Immersion.objects.filter(student=user, slot=slot, cancellation_type__isnull=True).first()

    if immersion and immersion.slot.date > today:
        res = immersion.notify_disability_referent(str_ref_only=str_ref_only)
        response.update({
            "msg": res.get("msg"),
            "error": res.get("error", False)
        })

    return JsonResponse(response, safe=False)


class CampusList(ManyMixin, generics.ListCreateAPIView):
    """
    Campus list
    """

    serializer_class = CampusSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = [
        'establishment',
    ]
    permission_classes = [CustomDjangoModelPermissions]

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
    filterset_fields = [
        'active',
    ]

    def get_queryset(self):
        queryset = Establishment.activated.order_by('label')
        user = self.request.user

        if not user.is_superuser and user.is_establishment_manager():
            queryset = queryset.filter(id=user.establishment.id)

        return queryset


class StructureList(ManyMixin, generics.ListCreateAPIView):
    """
    Structures list
    """

    serializer_class = StructureSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = [
        'establishment',
    ]
    permission_classes = [
        CustomDjangoModelPermissions
        | IsStructureManagerPermissions
        | IsStructureConsultantPermissions
        | IsEstablishmentManagerPermissions
        | IsRefLycPermissions
    ]

    def get_queryset(self):
        queryset = Structure.activated.order_by('code', 'label')
        user = self.request.user

        if not user.is_superuser:
            if user.is_structure_manager() or user.is_structure_consultant():
                return user.structures.order_by('code', 'label')
            if user.is_establishment_manager() and user.establishment:
                return user.establishment.structures.order_by('code', 'label')

        return queryset


class TrainingList(ManyMixin, generics.ListCreateAPIView):
    """
    Training list / creation
    Returns only active trainings
    """

    # queryset = Training.objects.all()
    serializer_class = TrainingSerializer
    permission_classes = [
        IsRefLycPermissions
        | IsMasterEstablishmentManagerPermissions
        | IsEstablishmentManagerPermissions
        | IsStructureManagerPermissions
        | IsTecPermissions
        | CustomDjangoModelPermissions
        | IsStructureConsultantPermissions
    ]
    filterset_fields = [
        'structures',
        'highschool',
    ]

    # Auth : default (see settings/base.py)

    def get_queryset(self):
        user = self.request.user
        trainings_queryset = (
            Training.objects.prefetch_related('highschool', 'structures__establishment', 'courses')
            .filter(active=True)
            .annotate(
                nb_courses=Count('courses'),
            )
        )

        if user.is_high_school_manager():
            return trainings_queryset.filter(highschool=user.highschool)
        elif user.is_establishment_manager():
            return trainings_queryset.filter(structures__establishment=user.establishment)
        elif user.is_structure_manager():
            return trainings_queryset.filter(structures__in=user.get_authorized_structures())

        return trainings_queryset

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class TrainingDomainList(ManyMixin, generics.ListCreateAPIView):
    """
    Training domain list / creation
    """

    queryset = TrainingDomain.objects.all()
    serializer_class = TrainingDomainSerializer
    permission_classes = [CustomDjangoModelPermissions]
    # Auth : default (see settings/base.py)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class TrainingSubdomainList(ManyMixin, generics.ListCreateAPIView):
    """
    Training subdomain list / creation
    """

    model = TrainingSubdomain
    queryset = TrainingSubdomain.objects.all()
    serializer_class = TrainingSubdomainSerializer
    permission_classes = [CustomDjangoModelPermissions]
    # Auth : default (see settings/base.py)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class SpeakerList(ManyMixin, generics.ListCreateAPIView):
    """
    Speakers (only) list / creation
    """

    model = ImmersionUser
    serializer_class = SpeakerSerializer
    permission_classes = [SpeakersReadOnlyPermissions | CustomDjangoModelPermissions]
    filterset_fields = [
        'highschool', 'email'
    ]
    # Auth : default (see settings/base.py)

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        self.user = self.request.user

        course_id = self.kwargs.get("course_id")
        event_id = self.kwargs.get("event_id")

        if course_id:
            return Course.objects.get(id=course_id).speakers.all()
        if event_id:
            return OffOfferEvent.objects.get(id=event_id).speakers.all()

        filters = {'groups__name': 'INTER'}

        if self.user.is_high_school_manager():
            filters["highschool"] = self.user.highschool

        return ImmersionUser.objects.prefetch_related("groups").filter(**filters)

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = serializer.save()

        if user:
            user.send_message(self.request, 'CPT_CREATE')
            # TODO : check send message return


class UserList(generics.ListAPIView):
    """
    Users list
    """

    model = ImmersionUser
    queryset = ImmersionUser.objects.all()
    serializer_class = ImmersionUserSerializer
    permission_classes = [CustomDjangoModelPermissions]
    filterset_class = filters.ImmersionUserFilter

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)


class HighSchoolList(ManyMixin, generics.ListCreateAPIView):
    """
    High schools list / creation
    Unauthenticated GET is granted only when requesting high schools with valid agreements
    Other users need authentication or Django permissions (can_* ...)
    """

    model = HighSchool
    serializer_class = HighSchoolSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [HighSchoolReadOnlyPermissions | CustomDjangoModelPermissions]
    filterset_fields = [
        'active',
        'allow_individual_immersions',
        'id',
        'postbac_immersion',
        'signed_charter',
        'uses_agent_federation',
        'uses_student_federation',
        'with_convention',
    ]

    def __init__(self, *args, **kwargs):
        self.agreed = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.request.GET.get("agreed") is not None:
            self.agreed = self.request.GET.get("agreed", False) in ('true', 'True')

        if self.agreed:
            return HighSchool.agreed.all()

        return HighSchool.objects.all()

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)


class HighSchoolDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    High school detail
    """

    serializer_class = HighSchoolSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [CustomDjangoModelPermissions]
    lookup_fields = ['id']
    queryset = HighSchool.objects.all()

    def get_serializer(self, *args, **kwargs):
        context = kwargs.get('context', {})
        context['request'] = self.request
        return super().get_serializer(*args, **kwargs, context=context)

    def delete(self, request, *args, **kwargs):
        highschool_id = kwargs.get("pk")

        try:
            highschool = HighSchool.objects.get(pk=highschool_id)
        except HighSchool.DoesNotExist:
            return JsonResponse({"error": _("A valid high school must be selected")}, status=status.HTTP_404_NOT_FOUND)

        # Test all related objects before deletion
        tests = {
            "Courses": highschool.courses.exists(),
            "Events": highschool.events.exists(),
            "Group immersions": highschool.group_immersions.exists(),
            "Student records": highschool.student_records.exists(),
            "Trainings": highschool.trainings.exists(),
            "Users": highschool.users.exists()
        }

        errors = [
            _("Objects '%s' are linked to this high school, it can't be deleted") % x
            for x,y in tests.items() if y
        ]

        if errors:
            return JsonResponse(
                {"error": errors},
                status=status.HTTP_403_FORBIDDEN
            )

        super().delete(request, *args, **kwargs)

        return JsonResponse({"msg": _("High school successfully deleted")}, status=status.HTTP_200_OK)

class CourseTypeList(ManyMixin, generics.ListCreateAPIView):
    """
    Course types list
    """

    model = CourseType
    serializer_class = CourseTypeSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [CustomDjangoModelPermissions]
    filterset_fields = ['label', 'full_label', 'active']

    def get_queryset(self):
        user = self.request.user
        queryset = CourseType.objects.all()
        return queryset


class CourseTypeDetail(generics.RetrieveAPIView):
    """
    Course Type detail
    """

    serializer_class = CourseTypeSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [IsAuthenticated]  # enough ?
    lookup_fields = ['id']
    queryset = CourseType.objects.all()


class CourseList(SpeakersManyMixin, generics.ListCreateAPIView):
    """
    Courses list
    """

    model = Course
    serializer_class = CourseSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [
        IsMasterEstablishmentManagerPermissions
        | IsEstablishmentManagerPermissions
        | IsStructureManagerPermissions
        | IsTecPermissions
        | IsRefLycPermissions
        | IsSpeakerPermissions
        | CustomDjangoModelPermissions
        | IsStructureConsultantPermissions
    ]
    filterset_fields = [
        'training',
        'structure',
        'highschool',
        'published',
        'training__structures',
        'training__highschool',
    ]

    def __init__(self, *args, **kwargs):
        self.message = {}
        self.status = ""
        self.user = None
        self.user_courses = False
        self.user_filter = False
        self.filters = {}

        super().__init__(*args, **kwargs)

    def get_queryset(self):
        self.user = self.request.user
        self.user_courses = self.request.GET.get("user_courses", False) in ('true', 'True')
        self.user_filter = False
        self.filters = {}

        force_user_filter = [
            self.user_courses,
            self.user.is_speaker()
            and not any([
                self.user.is_master_establishment_manager(),
                self.user.is_establishment_manager(),
                self.user.is_high_school_manager(),
                self.user.is_structure_manager(),
                self.user.is_structure_consultant(),
                self.user.is_operator(),
            ]),
        ]

        if any(force_user_filter):
            self.user_filter = True
            self.filters["speakers__in"] = self.user.linked_users()

        queryset = (
            Course.objects.prefetch_related(
                'training__structures',
                'training__highschool',
                'training__training_subdomains',
                'highschool',
                'structure',
                'speakers',
            )
            .filter(**self.filters)
            .order_by('label')
        )

        if not self.user.is_superuser:
            if self.user.is_structure_manager() or self.user.is_structure_consultant():
                return queryset.filter(structure__in=self.user.structures.all()).order_by('label')
            if self.user.is_establishment_manager() and self.user.establishment:
                return Course.objects.filter(structure__in=self.user.establishment.structures.all()).order_by('label')

        return queryset


class CourseDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Course detail / update / destroy
    """

    serializer_class = CourseSerializer
    permission_classes = [
        IsMasterEstablishmentManagerPermissions
        | IsEstablishmentManagerPermissions
        | IsStructureManagerPermissions
        | IsTecPermissions
        | IsRefLycPermissions
        | IsSpeakerPermissions
        | CustomDjangoModelPermissions
        | IsStructureConsultantPermissions
    ]

    def __init__(self, *args, **kwargs):
        self.user = None
        self.user_courses = False
        self.user_filter = False
        self.filters = {}

        super().__init__(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return Course.objects.prefetch_related(
            'training__structures',
            'training__highschool',
            'training__training_subdomains',
            'highschool',
            'structure',
            'speakers',
        ).all()

    def get_serializer(self, instance=None, data=None, partial=False):
        """
        Look for speaker emails and try to create/add them to serializer data
        """
        self.user = self.request.user
        self.user_courses = self.request.GET.get("user_courses", False) in ('true', 'True')
        self.user_filter = False
        self.filters = {}

        force_user_filter = [
            self.user_courses,
            self.user.is_speaker()
            and not any(
                [
                    self.user.is_master_establishment_manager(),
                    self.user.is_establishment_manager(),
                    self.user.is_structure_manager(),
                    self.user.is_structure_consultant(),
                    self.user.is_operator(),
                ]
            ),
        ]

        if any(force_user_filter):
            self.user_filter = True
            self.filters["speakers__in"] = self.user.linked_users()

        serializer_kwargs = {
            "instance": instance,
            "many": False,
            "partial": partial,
            "context": {'user_courses': self.user_filter, 'request': self.request},
        }

        if data:
            try:
                data = get_or_create_user(self.request, data)
                if data:
                    serializer_kwargs["data"] = data
            except Exception:
                raise

        return super().get_serializer(**serializer_kwargs)

    def delete(self, request, *args, **kwargs):
        course_id = kwargs.get("pk")

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return JsonResponse({"error": _("A valid course must be selected")}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.has_course_rights(course_id):
            return JsonResponse(
                {"error": _("You are not allowed to delete this course")}, status=status.HTTP_403_FORBIDDEN
            )

        if course.slots.exists():
            return JsonResponse(
                {"error": _("Slots are linked to this course, it can't be deleted")}, status=status.HTTP_403_FORBIDDEN
            )

        super().delete(request, *args, **kwargs)

        return JsonResponse({"msg": _("Course successfully deleted")}, status=status.HTTP_200_OK)


class SlotList(ManyMixin, generics.ListCreateAPIView):
    """
    Courses list
    """

    model = Slot
    serializer_class = SlotSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    permission_classes = [CustomDjangoModelPermissions]
    filterset_fields = [
        'course',
        'course_type',
        'event',
        'campus',
        'building',
        'room',
        'date',
        'start_time',
        'end_time',
        'speakers',
        'published',
        'place',
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = Slot.objects.all()
        return queryset


class SlotDetail(generics.RetrieveDestroyAPIView):
    serializer_class = SlotSerializer
    permission_classes = [CustomDjangoModelPermissions]
    authentication_classes = [
        TokenAuthentication,
    ]

    def delete(self, request, *args, **kwargs):
        if Immersion.objects.filter(slot_id=kwargs.get("pk")).exists():
            return JsonResponse(data={"error": _("This slot has registered immersions: delete not allowed")})

        super().delete(request, *args, **kwargs)
        return JsonResponse(
            data={
                "msg": _("Slot #%s deleted") % kwargs["pk"],
            }
        )

    def get_queryset(self):
        return Slot.objects.all()


class BuildingList(ManyMixin, generics.ListCreateAPIView):
    """
    Buildings list
    """

    serializer_class = BuildingSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = [
        'campus',
    ]
    permission_classes = [CustomDjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        queryset = Building.objects.order_by('label')

        if user.is_authenticated and not user.is_superuser:
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


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingDetail(generics.RetrieveDestroyAPIView):
    """
    Training detail / destroy
    """

    serializer_class = TrainingSerializer

    def delete(self, request, *args, **kwargs):
        if Course.objects.filter(training_id=kwargs.get("pk")).exists():
            return JsonResponse(data={"error": _("Some courses are attached to this training: delete not allowed")})

        super().delete(request, *args, **kwargs)
        return JsonResponse(
            data={
                "msg": _("Training #%s deleted") % kwargs["pk"],
            }
        )

    def get_queryset(self):
        return Training.objects.filter(highschool=self.request.user.highschool)


class OffOfferEventList(SpeakersManyMixin, generics.ListAPIView):
    """
    Off offer events list
    """

    serializer_class = OffOfferEventSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['establishment', 'structure', 'highschool']

    def __init__(self, *args, **kwargs):
        self.message = {}
        self.status = ""
        self.user = None
        self.user_events = False
        self.user_filter = False
        self.filters = {}

        super().__init__(*args, **kwargs)

    def get_queryset(self):
        queryset = OffOfferEvent.objects.all()
        user = self.request.user
        self.user_filter = False
        user_events = self.request.GET.get('user_events', False) == 'true'

        force_user_filter = [
            user_events,
            user.is_speaker()
            and not any(
                [
                    user.is_master_establishment_manager(),
                    user.is_establishment_manager(),
                    user.is_high_school_manager(),
                    user.is_structure_manager(),
                    user.is_operator(),
                    user.is_structure_consultant(),
                ]
            ),
        ]

        if any(force_user_filter):
            self.user_filter = True

        if not user.is_superuser:
            if any(force_user_filter):
                queryset = queryset.filter(speakers__in=user.linked_users())
            elif user.is_high_school_manager():
                queryset = queryset.filter(highschool=user.highschool)
            elif user.is_establishment_manager() and user.establishment:
                queryset = OffOfferEvent.objects.filter(
                    Q(establishment=user.establishment) | Q(structure__in=user.establishment.structures.all())
                ).distinct()
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
                return JsonResponse(data={"msg": _("Insufficient privileges")}, status=status.HTTP_403_FORBIDDEN)

        if obj.slots.exists():
            return JsonResponse(
                data={"error": _("Some slots are attached to this event: it can't be deleted")},
                status=status.HTTP_403_FORBIDDEN,
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

        attestations = (
            VisitorRecordDocument.objects.filter(
                Q(validity_date__lt=today) | Q(validity_date__isnull=True),
                archive=False,
                record=OuterRef("pk"),
                requires_validity_date=True,
            )
            .exclude(Q(validity_date__isnull=True, document='') | Q(validity_date__isnull=False), mandatory=False)
            .order_by()
            .annotate(count=Func(F('id'), function='Count'))
            .values('count')
        )

        records = (
            VisitorRecord.objects.filter(validation=operations[operation])
            .annotate(
                user_first_name=F("visitor__first_name"),
                user_last_name=F("visitor__last_name"),
                invalid_dates=Subquery(attestations),
            )
            .values(
                "id",
                "user_first_name",
                "user_last_name",
                "birth_date",
                "creation_date",
                "validation_date",
                "rejected_date",
                "invalid_dates",
                "rejection_reason",
            )
        )

        # List of the ids of the extracted records
        record_ids = [r['id'] for r in records]

        # Getting the attestations linked to the records
        docs_qs = VisitorRecordDocument.objects.filter(
            record_id__in=record_ids,
            archive=False,
            document__isnull=False
        ).select_related('attestation')

        # List of attestations
        attestations_by_record = {}
        for doc in docs_qs:
            att = doc.attestation
            if att:
                attestations_by_record.setdefault(doc.record_id, []).append({
                    'id': doc.pk,
                    'label': att.label,
                    'url': doc.document.url if doc.document else '',
                    'validity_date': doc.validity_date.strftime("%Y-%m-%d") if doc.validity_date else None,
                    'requires_validity_date': doc.requires_validity_date,
                })

        for rec in records:
            rec['attestations'] = attestations_by_record.get(rec['id'], [])

        data['data'] = list(records)

        return JsonResponse(data)


@method_decorator(groups_required("REF-ETAB-MAITRE", "REF-TEC"), name="dispatch")
class VisitorRecordRejectValidate(View):
    def post(self, request, *args, **kwargs):
        today = timezone.localdate()
        msgs = []
        data: Dict[str, Any] = {"msg": "", "data": None}

        # can't be none. No routes allowed for that
        record_id: str = self.kwargs["record_id"]
        operation: str = self.kwargs["operation"]
        rejection_reason: str = request.POST.get("rejection_reason", "")
        validation_data = request.POST.get("validity_dates", "[]")
        delete_attachments: bool = False
        set_status_params = {}

        try:
            validation_data = json.loads(validation_data)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "msg": "Invalid JSON validation data"}, status=400)

        if operation == "validate":
            validation_value = "VALIDATED"
            validation_email_template = "CPT_MIN_VALIDE"
            delete_attachments = get_general_setting("DELETE_RECORD_ATTACHMENTS_AT_VALIDATION")
        elif operation == "reject":
            validation_value = "REJECTED"
            validation_email_template = "CPT_MIN_REJET"
        else:
            data["msg"] = _("Error - Bad operation selected. Allowed: validate, reject")
            return JsonResponse(data)

        # Direct validation of attestations (POST validation_data from visitor_validation template)
        for document_data in validation_data:
            doc_id = document_data.get("id")
            doc_validity_date = document_data.get("validity_date", "")

            try:
                document = VisitorRecordDocument.objects.get(pk=doc_id, record_id=record_id)
                if doc_validity_date:
                    document.validity_date = parse_date(doc_validity_date)
                    document.save()
            except VisitorRecordDocument.DoesNotExist:
                pass
            # Add exception for parse_date ?

        try:
            record: VisitorRecord = VisitorRecord.objects.prefetch_related('attestation').get(id=record_id)

            # Check documents
            attestations = record.attestation.filter(
                Q(validity_date__lte=today) | Q(validity_date__isnull=True),
                archive=False,
                requires_validity_date=True,
            )

            if validation_value == "VALIDATED" and attestations.exists():
                data['msg'] = _("Error: record has missing or invalid attestation dates")
                return JsonResponse(data, safe=False)

            if delete_attachments:
                # Delete only attestations that does not require a validity date
                for attestation in record.attestation.filter(requires_validity_date=False):
                    attestation.delete()

        except VisitorRecord.DoesNotExist:
            data["msg"] = _("Error - record not found: %s") % record_id
            return JsonResponse(data)

        if all([validation_value == "VALIDATED", record.validation != record.TO_REVALIDATE, record.disability]):
            set_status_params = {
                "request": request,
                "notify_disability": True
            }

        res = record.set_status(validation_value, **set_status_params)
        record.validation_date = timezone.localtime() if validation_value == "VALIDATED" else None
        record.rejected_date = timezone.localtime() if validation_value == "REJECTED" else None
        record.rejection_reason = rejection_reason if validation_value == "REJECTED" else None
        record.save()
        ret = record.visitor.send_message(self.request, validation_email_template)
        data["data"] = {"record_id": record.id}

        if res.get("msg"):
            msgs.append(res.get("msg"))

        if ret:
            msgs.append(_("Record updated but notification not sent : %s") % ret)
        else:
            msgs.append(_("Record updated, notification sent"))

        data['msg'] = "<br>".join(map(str, msgs))

        return JsonResponse(data)


@is_ajax_request
@is_post_request
@groups_required("REF-ETAB", "REF-LYC")
def signCharter(request):
    data = {"msg": "", "error": ""}
    charter_sign = get_general_setting('CHARTER_SIGN')  # useful somewhere ?
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
    authentication_classes = [
        TokenAuthentication,
    ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        extra_filter = {}
        registered_only = request.GET.get("registered_only", False) in (1, "1", "true", "True")
        period = request.GET.get("period", None)
        period_id = None

        try:
            global_mail = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            response["msg"] = "'GLOBAL_MAILING_LIST' setting does not exist (check admin GeneralSettings values)"
            return JsonResponse(data=response, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if registered_only:
            extra_filter["immersions__isnull"] = False

            # Period filter
            try:
                period_id = int(period)
                period = Period.objects.get(pk=period_id)
                extra_filter.update(
                    {
                        "immersions__slot__date__gte": period.immersion_start_date,
                        "immersions__slot__date__lte": period.immersion_end_date,
                    }
                )
            except (ValueError, TypeError):
                # Invalid value for period (or period is None)
                if period is not None:
                    response["msg"] = f"Warning : invalid period value ('{period}'), integer expected."
            except Period.DoesNotExist:
                response["msg"] = f"Warning : invalid filter : period '{period_id}' not found"

        mailing_list = [
            email
            for email in ImmersionUser.objects.prefetch_related(
                "student_record", "high_school_student_record", "visitor_record", "immersions__slot"
            )
            .filter(
                Q(student_record__isnull=False)
                | Q(high_school_student_record__validation=2, high_school_student_record__isnull=False)
                | Q(visitor_record__validation=2, visitor_record__isnull=False)
            )
            .filter(**extra_filter)
            .values_list('email', flat=True)
            .distinct()
        ]

        response["data"] = {global_mail: mailing_list}
        return JsonResponse(data=response)


class MailingListStructuresView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}
        for structure in Structure.objects.filter(mailing_list__isnull=False):
            mail = structure.mailing_list
            mailing_list = [
                email
                for email in Immersion.objects.filter(cancellation_type__isnull=True)
                .filter(Q(slot__course__structure=structure) | Q(slot__event__structure=structure))
                .values_list('student__email', flat=True)
                .distinct()
            ]
            response["data"][mail] = mailing_list

        return JsonResponse(data=response)


class MailingListEstablishmentsView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}
        for establishment in Establishment.objects.filter(mailing_list__isnull=False):
            mailing_list = [
                email
                for email in Immersion.objects.filter(cancellation_type__isnull=True)
                .filter(
                    Q(slot__course__structure__establishment=establishment)
                    | Q(slot__event__establishment=establishment)
                )
                .values_list('student__email', flat=True)
                .distinct()
            ]
            response["data"][establishment.mailing_list] = mailing_list

        return JsonResponse(data=response)


class MailingListHighSchoolsView(APIView):
    authentication_classes = [
        TokenAuthentication,
    ]

    def get(self, request, *args, **kwargs):
        response: Dict[str, Any] = {"msg": "", "data": None}
        response["data"] = {}

        for hs in HighSchool.agreed.filter(mailing_list__isnull=False):
            mailing_list = [
                email
                for email in Immersion.objects.filter(cancellation_type__isnull=True)
                .filter(Q(slot__course__highschool=hs) | Q(slot__event__highschool=hs))
                .values_list('student__email', flat=True)
                .distinct()
            ]
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
            "place": request.POST.get("place", Slot.FACE_TO_FACE),
            "recipient": request.POST.get("recipient", "user"),
            "educonnect": request.POST.get("educonnect", False) == "true",
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
                context_params=context_params, user=self.request.user, request=self.request, body=body
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
            msg: str = _(
                """An error occurred while running annual purge command. """
                """For more details, please contact the administrator."""
            )
            logger.error(msg)
            response["msg"] = msg

        # Step 2 : clear accounts that are no longer in establishment's LDAPs
        try:
            call_command("delete_account_not_in_ldap")
            response["ok"] = True
        except CommandError:
            msg: str = _(
                """An error occurred while deleting expired LDAP accounts. """
                """For more details, please contact the administrator."""
            )
            logger.error(msg)
            response["msg"] = msg

        response["time"] = round(time.thread_time() - command_time, 3)

        return JsonResponse(response)


@is_ajax_request
@is_post_request
@groups_required("REF-STR")
def ajax_update_structures_notifications(request):

    settings = response = {}
    ids = request.POST.get('ids') # for registrants list
    dis_ids = request.POST.get('dis_ids') # for disabled people notifications

    try:
        ids = json.loads(ids)
    except:
        ids = []

    try:
        dis_ids = json.loads(dis_ids)
    except:
        dis_ids = []

    structures = request.user.get_authorized_structures().filter(id__in=ids).values_list('id', flat=True)
    dis_structures = request.user.get_authorized_structures().filter(id__in=dis_ids).values_list('id', flat=True)

    settings, created = RefStructuresNotificationsSettings.objects.get_or_create(user=request.user)

    if not structures and not dis_structures:
        settings.delete()
    else:
        settings.structures.set(structures, clear=True)
        settings.disability_structures.set(dis_structures, clear=True)

    if settings:
        response["msg"] = gettext("Settings updated")
    else:
        response["msg"] = gettext("Nothing to do")

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_can_register_slot(request, slot_id=None):
    """
    Returns registering slot status for a logged user
    Warning not quota & remaining seats checking !

    GET parameters:
    slot_id
    """
    now = timezone.now()
    today = timezone.localdate()

    user = request.user
    response = {'msg': '', 'data': []}
    slot_data = {
        'can_register': False,
        'already_registered': False,
    }

    if not user.is_authenticated:
        response['msg'] = gettext("Error : user not authenticated")
        return JsonResponse(response, safe=False)

    if not slot_id:
        response['msg'] = gettext("Error : missing slot id")
        return JsonResponse(response, safe=False)

    now = timezone.localtime()

    slot = Slot.objects.get(id=slot_id)

    if not slot:
        response['msg'] = gettext("Error : slot not found")
        return JsonResponse(response, safe=False)

    can_register_slot, reason = user.can_register_slot(slot)

    # Should not happen !
    if not slot.published:
        response['msg'] = _("Registering an unpublished slot is forbidden")
        return JsonResponse(response, safe=False)

    # Only valid Highschool students
    if user.is_high_school_student():
        if not user.is_valid():
            response['msg'] = _("Cannot register slot due to Highschool student account state")
            return JsonResponse(response, safe=False)

        record = user.get_high_school_student_record()
        if not record or not record.is_valid():
            response['msg'] = _("Cannot register slot due to Highschool student record state")
            return JsonResponse(response, safe=False)

    # Only valid Visitors records
    if user.is_visitor():
        if not user.is_valid():
            response['msg'] = _("Cannot register slot due to visitor account state")
            return JsonResponse(response, safe=False)

        record = user.get_visitor_record()
        if not record or not record.is_valid():
            response['msg'] = _("Cannot register slot due to visitor record state")
            return JsonResponse(response, safe=False)

    # Out of date mandatory attestations
    if user.has_obsolete_attestations():
        response['msg'] = _("Cannot register slot due to out of date attestations")
        return JsonResponse(response, safe=False)

    # ==========================
    # Period date
    period = slot.period

    if period:
        if now < period.registration_start_date:
            response['msg'] = _("You can't register to this slot yet")
            return JsonResponse(response, safe=False)

        if today > period.immersion_end_date or slot.registration_limit_date < now:
            response['msg'] = _("You can't register to this slot anymore")
            return JsonResponse(response, safe=False)
    # ========================

    # If user == REF-LYC
    # Need to test if I can register a group with the available seats for groups
    # else
    # Need to test if I can register someone with the individual seats
    if request.user.is_high_school_manager():
        if not slot.available_group_seats():
            response['msg'] = _("No group seat available for selected slot")
            return JsonResponse(response, safe=False)
    elif slot.available_seats() == 0:
        # Check free seat in slot for individual registration
        response['msg'] = _("No seat available for selected slot")
        return JsonResponse(response, safe=False)

    # Slot registration limit date
    if timezone.localtime() > slot.registration_limit_date:
        response['msg'] = _("Cannot register slot due to passed registration date")
        return JsonResponse(response, safe=False)

    # Slot registration restrictions
    if not can_register_slot:
        response = {'error': True, 'msg': reason}
        return JsonResponse(response, safe=False)

    # Check current student immersions and valid dates
    if user.immersions.filter(slot=slot, cancellation_type__isnull=True).exists():
        response['msg'] = _("Already registered to this slot")
        slot_data['already_registered'] = True
        slot_data['can_register'] = False
        response['data'].append(slot_data.copy())
        return JsonResponse(response, safe=False)

    else:

        slot_data['can_register'] = True

    response['data'].append(slot_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_search_slots_list(request, slot_id=None):

    today = timezone.now()
    response = {'msg': '', 'data': []}
    user = request.user
    is_authenticated = user.is_authenticated

    user_highschool = user.highschool if is_authenticated else ''

    slots = (
        Slot.objects.filter(published=True)
        .filter(Q(date__isnull=True) | Q(date__gte=today.date()) | Q(date=today.date(), end_time__gte=today.time()))
    )

    if is_authenticated and not user.is_high_school_manager():
        slots = slots.exclude(Q(allow_group_registrations=True) & Q(allow_individual_registrations=False) & Q(public_group=False))

    group_registered_persons_query = (
        ImmersionGroupRecord.objects.filter(slot=OuterRef("pk"), cancellation_type__isnull=True)
        .annotate(group_registered_persons=(F('students_count') + F('guides_count')))
        .annotate(total=Coalesce(Func('group_registered_persons', function='SUM'), 0))
        .values('total')
    )

    fields = [
        "id",
        "slot_type",
        "published",
        "label",
        "course_url",
        "course_type_full_label",
        "establishment_short_label",
        "establishment_label",
        "structure_code",
        "structure_label",
        "structure_establishment_short_label",
        "highschool_city",
        "highschool_label",
        "highschool_address",
        "event_description",
        "date",
        "start_time",
        "end_time",
        "campus_label",
        "building_url",
        "city",
        "building_label",
        "place",
        "room",
        "meeting_place",
        "n_register",
        "n_places",
        "n_group_places",
        "group_mode",
        "public_group",
        "speakers_list",
        "course_training_label",
        "course_training_url",
        "additional_information",
        "registration_limit_date",
        "event_type",
        "passed_registration_limit_date",
        "allow_individual_registrations",
        "allow_group_registrations",
        "user_has_group_immersions",
        "user_is_registered"
    ]

    # defaults
    immersions_count = Value(0)
    group_immersions_count = Value(0)

    if is_authenticated:
        fields.append('url')

        immersions_count = Count(
            "immersions",
            filter=Q(
                immersions__student=user,
                immersions__cancellation_type__isnull=True
            ),
            distinct=True
        )

    if user_highschool:
        group_immersions_count = Count(
            'group_immersions',
            filter=Q(
                group_immersions__highschool=user_highschool,
                group_immersions__cancellation_type__isnull=True
            ),
            distinct=True
        )

    slots = (
        slots.annotate(
            label=Coalesce(F("course__label"), F("event__label")),
            course_url=Coalesce(
                F("course__url"),
                Value(''),
            ),
            slot_type=Case(
                When(course__isnull=False, then=Value(gettext("Course"))),
                When(event__isnull=False, then=Value(gettext("Event"))),
            ),
            course_training_label=Coalesce(
                F("course__training__label"),
                Value(''),
            ),
            course_training_url=Coalesce(
                F("course__training__url"),
                Value(''),
            ),
            course_type_full_label=Coalesce(
                F("course_type__full_label"),
                Value(''),
            ),
            event_description=Coalesce(
                F("event__description"),
                Value(''),
            ),
            building_label=F("building__label"),
            building_url=Coalesce(
                F("building__url"),
                Value(''),
            ),
            establishment_label=Coalesce(
                F("course__structure__establishment__label"),
                F("event__establishment__label"),
            ),
            establishment_short_label=Coalesce(
                F("course__structure__establishment__short_label"),
                F("event__establishment__short_label"),
            ),
            structure_code=Coalesce(
                F("course__structure__code"),
                F("event__structure__code"),
            ),
            structure_label=Coalesce(
                F("course__structure__label"),
                F("event__structure__label"),
            ),
            structure_establishment_short_label=Coalesce(
                F("course__structure__establishment__short_label"),
                F("event__structure__establishment__short_label"),
            ),
            highschool_city=Coalesce(
                F("course__highschool__city"),
                F("event__highschool__city"),
            ),
            highschool_address=Coalesce(
                F("course__highschool__address"),
                F("event__highschool__address"),
            ),
            highschool_label=Coalesce(
                F("course__highschool__label"),
                F("event__highschool__label"),
            ),
            campus_label=Coalesce(
                F('campus__label'),
                Value(''),
            ),
            meeting_place=Case(
                When(place=Slot.FACE_TO_FACE, then=F('room')),
                When(place=Slot.OUTSIDE, then=F('room')),
                When(place=Slot.REMOTE, then=Value(gettext('Remote'))),
            ),
            event_type=Coalesce(
                F('event__event_type__label'),
                Value(''),
            ),
            city=Coalesce(
                F("campus__city"),
                F("course__highschool__city"),
                F("event__highschool__city"),
            ),
            n_register=Count(
                "immersions",
                filter=Q(immersions__cancellation_type__isnull=True),
                distinct=True,
            ),
            attendances_to_enter=Count(
                "immersions",
                filter=Q(
                    immersions__attendance_status=0,
                    immersions__cancellation_type__isnull=True,
                ),
                distinct=True,
            ),
            speakers_list=Coalesce(
                ArrayAgg(
                    JSONObject(
                        last_name=F("speakers__last_name"),
                        first_name=F("speakers__first_name"),
                        email=F("speakers__email"),
                    ),
                    filter=Q(speakers__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            passed_registration_limit_date=ExpressionWrapper(
                Q(registration_limit_date__lt=timezone.now()), output_field=CharField()
            ),
            group_immersions_count=group_immersions_count,
            user_has_group_immersions=Case(
                When(Q(group_immersions_count__gte=1), then=True),
                default=False
            ),
            immersions_count=immersions_count,
            user_is_registered=Case(
                When(Q(immersions_count__gte=1), then=True),
                default=False
            ),
        )
        .annotate(
            group_registered_persons=Subquery(group_registered_persons_query),
        )
        .order_by("date", "start_time")
        .values(*fields, 'group_registered_persons')
    )

    response['data'] = {"slots": list(slots)}
    return JsonResponse(response, safe=False)


@is_ajax_request
def ajax_get_slot_restrictions(request, slot_id=None):
    """
    Returns slot's restrictions
    GET parameters:
    slot_id
    """

    response = {'msg': '', 'data': []}

    if not slot_id:
        response['msg'] = gettext("Error : missing slot id")
        return JsonResponse(response, safe=False)

    slot = (
        Slot.objects.filter(id=slot_id)
        .annotate(
            allowed_establishments_list=Coalesce(
                ArrayAgg(
                    F('allowed_establishments__short_label'),
                    filter=Q(allowed_establishments__isnull=False),
                    distinct=True,
                ),
                Value([]),
            ),
            allowed_highschools_list=Coalesce(
                ArrayAgg(
                    JSONObject(city=F('allowed_highschools__city'), label=F('allowed_highschools__label')),
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
        )
        .values(
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
        )
    )

    if not slot:
        response['msg'] = gettext("Error : slot not found")
        return JsonResponse(response, safe=False)

    response['data'] = {'restrictions': list(slot)}

    return JsonResponse(response, safe=False)


class TrainingAllList(ManyMixin, generics.ListCreateAPIView):
    """
    Training list without restrictions for REF-LYC
    """

    # queryset = Training.objects.all()
    serializer_class = TrainingSerializer
    permission_classes = [
        IsRefLycPermissions,
    ]
    filterset_fields = [
        'structures',
        'highschool',
    ]

    # Auth : default (see settings/base.py)

    def get_queryset(self):
        user = self.request.user
        trainings_queryset = (
            Training.objects.prefetch_related('highschool', 'structures__establishment', 'courses')
            .filter(active=True)
            .annotate(
                nb_courses=Count('courses'),
            )
        )

        return trainings_queryset

    def post(self, request, *args, **kwargs):
        self.user = request.user
        return super().post(request, *args, **kwargs)