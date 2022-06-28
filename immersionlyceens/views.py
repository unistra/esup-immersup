import datetime
import mimetypes
import os
from email.policy import default
from wsgiref.util import FileWrapper

import requests
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models.query_utils import Q
from django.http import (
    FileResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
    HttpResponseNotFound, StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django.views import generic
from storages.backends.s3boto3 import S3Boto3Storage

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Calendar, Course, ImmersupFile, InformationText,
    PublicDocument, PublicType, Slot, Training, TrainingSubdomain,
    UserCourseAlert, Visit,
)
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
        offer_txt = InformationText.objects.get(code="OFFER", active=True).content
    except InformationText.DoesNotExist:
        offer_txt = ''

    subdomains = TrainingSubdomain.activated.filter(training_domain__active=True).order_by('training_domain', 'label')
    courses_count = Course.objects.filter(published=True).count()
    context = {
        'subdomains': subdomains,
        'courses_count': courses_count,
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

    context = {
        'procedure_txt': procedure_txt,
        'procedure_group_txt': procedure_group_txt,
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


def serve_immersup_file(request, file_code):
    """
    Returns a redirection to a stored file
    """

    try:
        immersupfile = get_object_or_404(ImmersupFile, pk=file_code)
        if isinstance(default_storage, S3Boto3Storage):
            response = requests.get(immersupfile.file.url, stream=True)
            return file_response(response.raw, as_attachment=True, content_type=response.headers['content-type'])
        else:
            return redirect(immersupfile.file.url)

    except Exception:
        return HttpResponseNotFound()


def offer_subdomain(request, subdomain_id):
    """Subdomain offer view"""
    student = None
    calendar = None
    cal_start_date = None
    cal_end_date = None
    reg_start_date = None
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

        remaining_regs_count = student.remaining_registrations_count()

        course_alerts = UserCourseAlert.objects.filter(email=request.user.email, email_sent=False).values_list(
            "course_id", flat=True
        )

    trainings = Training.objects.filter(training_subdomains=subdomain_id, active=True)
    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)

    data = []

    # determine dates range to use
    try:
        calendar = Calendar.objects.first()
    except Exception:
        pass

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()
    reg_start_date = reg_end_date = datetime.date(1, 1, 1)
    try:
        # Year mode
        if calendar and calendar.calendar_mode == 'YEAR':
            cal_start_date = calendar.year_registration_start_date
            cal_end_date = calendar.year_end_date
            reg_start_date = calendar.year_registration_start_date
        # semester mode
        elif calendar:
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                semester = 1
                cal_start_date = calendar.semester1_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester1_registration_start_date
                reg_semester2_start_date = calendar.semester2_registration_start_date
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                semester = 2
                cal_start_date = calendar.semester2_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester2_registration_start_date

    except AttributeError:
        raise Exception(_('Calendar not initialized'))

    for training in trainings:
        training_courses = (
            Course.objects.prefetch_related('training')
            .filter(training__id=training.id, published=True)
            .order_by('label')
        )

        for course in training_courses:
            slots = Slot.objects.filter(
                course__id=course.id, published=True, date__gte=today, date__lte=cal_end_date,
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
                    # Already registered / cancelled ?
                    for immersion in student.immersions.all():
                        if immersion.slot == slot:
                            slot.already_registered = True
                            slot.cancelled = immersion.cancellation_type is not None

                    # Can register ?
                    # not registered + free seats + dates in range + cancelled to register again
                    if not slot.already_registered or slot.cancelled:
                        can_register, reasons = student.can_register_slot(slot)
                        if slot.available_seats() > 0 and can_register:
                            # TODO: should be rewritten used before with remaining_seats annual or by semester!
                            if calendar.calendar_mode == 'YEAR':
                                if reg_start_date <= today <= cal_end_date:
                                    slot.can_register = True
                                elif calendar.calendar_mode == 'YEAR' and reg_start_date > today:
                                    slot.opening_soon = True
                            # Check if we could register with reg_date
                            elif semester == 1:
                                if reg_start_date <= today and slot.date < reg_semester2_start_date:
                                    slot.can_register = True
                                elif slot.date > reg_semester2_start_date or today < reg_start_date:
                                    slot.opening_soon = True
                            elif semester == 2:
                                if today >= reg_start_date:
                                    slot.can_register = True
                                elif today < reg_start_date:
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
            # TODO: Check for events & visits !!!!
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
        'reg_start_date': reg_start_date,
        'today': today,
        'cal_start_date': cal_start_date,
        'cal_end_date': cal_end_date,
        'student': student,
        'open_training_id': open_training_id,
        'open_course_id': open_course_id,
        'course_alerts': course_alerts,
        'is_anonymous': request.user.is_anonymous,
    }

    return render(request, 'offer_subdomains.html', context)


def visits_offer(request):
    """ Visits Offer view """

    filters = {}
    today = timezone.now().date()
    student = None
    course_alerts = None
    Q_filter = None

    try:
        visits_txt = InformationText.objects.get(code="INTRO_VISITE", active=True).content
    except InformationText.DoesNotExist:
        visits_txt = ''

    # Published visits only & no course nor event slot
    filters["course__isnull"] = True
    filters["event__isnull"] = True
    filters["visit__published"] = True

    # If user is highschool student filter on highschool
    try:
        if request.user.is_high_school_student() and not request.user.is_superuser:
            student = request.user
            record = student.get_high_school_student_record()
            user_highschool = record.highschool
            filters["visit__highschool"] = user_highschool
            Q_filter = (Q(levels_restrictions=False) | Q(allowed_highschool_levels__pk__contains=record.level.pk))

    except Exception as e:
        # AnonymousUser
        pass

    # TODO: implement class method in model to retrieve >=today slots for visits
    filters["date__gte"] = today
    visits = Slot.objects.prefetch_related(
            'visit__establishment', 'visit__structure', 'visit__highschool', 'speakers', 'immersions') \
            .filter(**filters).order_by('visit__highschool__city', 'visit__highschool__label', 'visit__purpose', 'date')

    if Q_filter:
        visits = visits.filter(Q_filter)

    # determine dates range to use
    # TODO: refactor in model !
    try:
        calendar = Calendar.objects.first()
    except Exception:
        pass

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()
    reg_start_date = reg_end_date = datetime.date(1, 1, 1)
    try:
        # Year mode
        if calendar and calendar.calendar_mode == 'YEAR':
            cal_start_date = calendar.year_registration_start_date
            cal_end_date = calendar.year_end_date
            reg_start_date = calendar.year_registration_start_date
        # semester mode
        elif calendar:
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                semester = 1
                cal_start_date = calendar.semester1_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester1_registration_start_date
                reg_semester2_start_date = calendar.semester2_registration_start_date
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                semester = 2
                cal_start_date = calendar.semester2_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester2_registration_start_date

    except AttributeError:
        raise Exception(_('Calendar not initialized'))

    # If the current user is a higschool student, check whether he can register
    if student and record:
        for visit in visits:
            visit.already_registered = False
            visit.can_register = False
            visit.cancelled = False
            visit.opening_soon = False
            # Already registered / cancelled ?
            for immersion in student.immersions.all():
                if immersion.slot.pk == visit.pk:
                    visit.already_registered = True
                    visit.cancelled = immersion.cancellation_type is not None

            # Can register ?
            # not registered + free seats + dates in range + cancelled to register again
            if not visit.already_registered or visit.cancelled:
                can_register, reasons = student.can_register_slot(visit)
                if visit.available_seats() > 0 and can_register:
                    # TODO: should be rewritten used before with remaining_seats annual or by semester!
                    if calendar.calendar_mode == 'YEAR':
                        if reg_start_date <= today <= cal_end_date:
                            visit.can_register = True
                        elif calendar.calendar_mode == 'YEAR' and reg_start_date > today:
                            visit.opening_soon = True
                    # Check if we could register with reg_date
                    elif semester == 1:
                        if reg_start_date <= today and visit.date < reg_semester2_start_date:
                            visit.can_register = True
                        elif visit.date > reg_semester2_start_date or today < reg_start_date:
                            visit.opening_soon = True
                    elif semester == 2:
                        if today >= reg_start_date:
                            visit.can_register = True
                        elif today < reg_start_date:
                            visit.opening_soon = True

    else:
        for visit in visits:
            visit.cancelled = False
            visit.can_register = False
            visit.already_registered = False

    visits_count = visits.count()



    context = {
        'visits_count': visits_count,
        'visits_txt': visits_txt,
        'visits': visits,
    }
    return render(request, 'visits_offer.html', context)


def offer_off_offer_events(request):
    """ Visits Offer view """

    filters = {}
    today = timezone.now().date()
    student = None
    calendar = None
    cal_start_date = None
    cal_end_date = None
    reg_start_date = None
    Q_Filter = None

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

    # Published event only & no course nor visit slot
    filters["course__isnull"] = True
    filters["visit__isnull"] = True
    filters["event__published"] = True

    # TODO: implement class method in model to retrieve >=today slots for visits
    filters["date__gte"] = today
    events = Slot.objects.prefetch_related(
            'event__establishment', 'event__structure', 'event__highschool', 'speakers', 'immersions') \
            .filter(**filters).order_by('event__establishment__label', 'event__highschool__label', 'event__label', 'date' )

    # determine dates range to use
    # TODO: refactor in model !
    try:
        calendar = Calendar.objects.first()
    except Exception:
        pass

    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()
    reg_start_date = reg_end_date = datetime.date(1, 1, 1)
    try:
        # Year mode
        if calendar and calendar.calendar_mode == 'YEAR':
            cal_start_date = calendar.year_registration_start_date
            cal_end_date = calendar.year_end_date
            reg_start_date = calendar.year_registration_start_date
        # semester mode
        elif calendar:
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                semester = 1
                cal_start_date = calendar.semester1_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester1_registration_start_date
                reg_semester2_start_date = calendar.semester2_registration_start_date
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
                semester = 2
                cal_start_date = calendar.semester2_start_date
                cal_end_date = calendar.semester2_end_date
                reg_start_date = calendar.semester2_registration_start_date

    except AttributeError:
        raise Exception(_('Calendar not initialized'))

    # If the current user is a stident/highschool student, check whether he can register
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
                if event.available_seats() > 0 and can_register:
                    # TODO: should be rewritten used before with remaining_seats annual or by semester!
                    if calendar.calendar_mode == 'YEAR':
                        if reg_start_date <= today <= cal_end_date:
                            event.can_register = True
                        elif calendar.calendar_mode == 'YEAR' and reg_start_date > today:
                            event.opening_soon = True
                    # Check if we could register with reg_date
                    elif semester == 1:
                        if reg_start_date <= today and visit.date < reg_semester2_start_date:
                            event.can_register = True
                        elif visit.date > reg_semester2_start_date or today < reg_start_date:
                            event.opening_soon = True
                    elif semester == 2:
                        if today >= reg_start_date:
                            event.can_register = True
                        elif today < reg_start_date:
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


def error_500(request):
    return render(request, '500.html', status=500)
