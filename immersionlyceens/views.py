import datetime
import json
import mimetypes
import os
import sys
from email.policy import default
from wsgiref.util import FileWrapper

import requests
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.core.files.storage import default_storage
from django.db.models import (BooleanField, Case, CharField, Count, DateField,
                              Exists, ExpressionWrapper, F, Func, OuterRef, Q,
                              QuerySet, Subquery, Value, When)
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

from immersionlyceens.apps.core.models import (AccompanyingDocument,
                                               AttestationDocument, Course,
                                               Establishment, FaqEntry,
                                               HighSchool, InformationText,
                                               Period, PublicDocument,
                                               PublicType, Slot, Training,
                                               TrainingSubdomain,
                                               UserCourseAlert)
from immersionlyceens.exceptions import DisplayException
from immersionlyceens.libs.utils import get_general_setting


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
        twitter_url = get_general_setting("TWITTER_ACCOUNT_URL")
    except (ValueError, NameError):
        twitter_url = ''

    context = {
        'welcome_txt': welcome_txt,
        'procedure_txt': procedure_txt,
        'offer_txt': offer_txt,
        'accomp_txt': accomp_txt,
        'twitter_url': twitter_url,
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

    today = datetime.datetime.today()
    subdomains = TrainingSubdomain.activated.filter(training_domain__active=True).order_by('training_domain', 'label')
    slots_count = Slot.objects.filter(published=True, event__isnull=True).filter(
        Q(date__isnull=True)
        | Q(date__gte=today.date())
        | Q(date=today.date(), end_time__gte=today.time())

    ).distinct().count()

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


def offer_subdomain(request, subdomain_id):
    """Subdomain offer view"""
    student = None
    record = None
    remaining_regs_count = None
    course_alerts = None

    if not request.user.is_anonymous \
        and (request.user.is_high_school_student() or request.user.is_student() or request.user.is_visitor()):
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

        course_alerts = UserCourseAlert.objects.filter(email=request.user.email, email_sent=False).values_list(
            "course_id", flat=True
        )

    trainings = Training.objects.filter(training_subdomains=subdomain_id, active=True)
    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)

    data = []

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    now = timezone.now()
    today = timezone.localdate()

    for training in trainings:
        training_courses = (
            Course.objects.prefetch_related('training')
            .filter(training__id=training.id, published=True)
            .order_by('label')
        )

        for course in training_courses:
            slots = Slot.objects.filter(
                course__id=course.id, published=True, date__gte=today
            ).order_by('date', 'start_time', 'end_time')

            training_data = {
                'training': training,
                'course': course,
                'slots': None,
                'alert': (not slots or all([s.available_seats() == 0 for s in slots])),
            }

            # If the current user is a student, check whether he can register
            if student and record and remaining_regs_count:
                for slot in slots:
                    slot.already_registered = False
                    slot.can_register = False
                    slot.cancelled = False
                    slot.opening_soon = False
                    slot.passed_registration_limit_date = \
                        slot.registration_limit_date < timezone.now() if slot.registration_limit_date else False
                    slot.passed_cancellation_limit_date = \
                        slot.cancellation_limit_date < timezone.now() if slot.cancellation_limit_date else False

                    # FIXME: still used somewhere ?
                    remaining_period_registrations = 0

                    # get slot period (for dates)
                    try:
                        period = Period.from_date(pk=slot.period.pk, date=slot.date)
                        remaining_period_registrations = remaining_regs_count.get(period.pk, 0)
                    except Period.DoesNotExist:
                        raise
                    except Period.MultipleObjectsReturned:
                        raise

                    # Already registered / cancelled ?
                    for immersion in student.immersions.all():
                        if immersion.slot == slot:
                            slot.already_registered = True
                            slot.cancelled = immersion.cancellation_type is not None

                    # Can register ?
                    # not registered + free seats + dates in range + cancelled to register again
                    # ignore "remaining_period_registrations > 0" ?
                    if not slot.already_registered or slot.cancelled:
                        can_register, reasons = student.can_register_slot(slot)

                        if slot.available_seats() > 0 and can_register:
                            if period.registration_start_date <= today <= period.immersion_end_date\
                                and slot.registration_limit_date >= now:
                                slot.can_register = True
                            elif now < slot.registration_limit_date:
                                slot.opening_soon = True
            else:
                for slot in slots:
                    slot.cancelled = False
                    slot.can_register = False
                    slot.already_registered = False

            training_data['slots'] = slots

            data.append(training_data.copy())

    # For navigation
    open_training_id, open_course_id = None, None

    slot_id = request.session.get("last_registration_slot_id", None)
    if slot_id:
        try:
            slot = Slot.objects.prefetch_related("course__training").get(pk=slot_id)
            # TODO: Check for events !!!!
            if slot.course:
                open_training_id = slot.course.training.id
                open_course_id = slot.course.id
        except Slot.DoesNotExist:
            pass

    # clean for next reload
    request.session.pop("last_registration_slot_id", None)

    context = {
        'subdomain': subdomain,
        'data': data,
        'today': today,
        'student': student,
        'open_training_id': open_training_id,
        'open_course_id': open_course_id,
        'course_alerts': course_alerts,
        'is_anonymous': request.user.is_anonymous,
    }

    return render(request, 'offer_subdomains.html', context)


def offer_off_offer_events(request):
    """ Events Offer view """

    filters = {}
    today = timezone.now().date()
    student = None
    record = None
    Q_Filter = None
    semester = None


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

    filters["date__gte"] = today
    events = Slot.objects.prefetch_related(
            'event__establishment', 'event__structure', 'event__highschool', 'speakers', 'immersions') \
            .filter(**filters).order_by('event__establishment__label', 'event__highschool__label', 'event__label', 'date' )

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    now = timezone.now()
    today = timezone.localdate()

    # If the current user is a student/highschool student, check whether he can register
    if student and record:
        for event in events:
            event.already_registered = False
            event.can_register = False
            event.cancelled = False
            event.opening_soon = False
            # Already registered / cancelled ?
            for immersion in student.immersions.all():
                if immersion.slot.pk == event.pk:
                    event.already_registered = True
                    event.cancelled = immersion.cancellation_type is not None

            # Can register ?
            # not registered + free seats + dates in range + cancelled to register again
            if not event.already_registered or event.cancelled:
                # TODO: refactor !!!!
                can_register, reasons = student.can_register_slot(event)

                try:
                    period = Period.from_date(pk=event.period.pk, date=event.date)
                except Period.DoesNotExist:
                    raise

                if event.available_seats() > 0 and can_register:
                    if period.registration_start_date <= today <= period.immersion_end_date \
                            and event.registration_limit_date >= now:
                        event.can_register = True
                    elif now < event.registration_limit_date:
                        event.opening_soon = True
    else:
        for event in events:
            event.cancelled = False
            event.can_register = False
            event.already_registered = False


    events_count = events.count()
    context = {
        'events_count': events_count,
        'events_txt': events_txt,
        'events': events,
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
    type_, exc, traceback = sys.exc_info()
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

    establishments = Establishment.activated.all().values('city', 'label', 'email')
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

    affiliated_highschools = HighSchool.objects.filter(active=True, with_convention=True) \
                                .values("city", "label", "email")

    try:
        affiliated_highschools_intro_txt = InformationText.objects.get(code="INTRO_LYCEES_CONVENTIONNES", \
                                                                      active=True).content
    except InformationText.DoesNotExist:
        # TODO: Default txt value ?
        affiliated_highschools_intro_txt = ''

    try:
        not_affiliated_highschools_intro_txt = InformationText.objects.get(code="INTRO_LYCEES_NON_CONVENTIONNES", \
                                                                      active=True).content
    except InformationText.DoesNotExist:
        # TODO: Default txt value ?
        not_affiliated_highschools_intro_txt = ''

    not_affiliated_highschools = HighSchool.objects.filter(active=True, with_convention=False) \
                                .values("city", "label", "email")

    context = {
        'affiliated_highschools': json.dumps(list(affiliated_highschools)),
        'affiliated_highschools_intro_txt': affiliated_highschools_intro_txt,
        'not_affiliated_highschools': json.dumps(list(not_affiliated_highschools)),
        'not_affiliated_highschools_intro_txt': not_affiliated_highschools_intro_txt,
    }
    return render(request, 'highschools.html', context)


def search_slots(request):
    today = timezone.now()

    try:
        intro_offer_search = InformationText.objects.get(
            code="INTRO_OFFER_SEARCH", active=True
        ).content
    except InformationText.DoesNotExist:
        # TODO: Default txt value ?
        intro_offer_search = ""

    context = {
        "intro_offer_search": intro_offer_search,
    }
    return render(request, "search_slots.html", context)
