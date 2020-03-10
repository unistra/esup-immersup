# -*- coding: utf-8 -*-
import datetime
import mimetypes
import os
from wsgiref.util import FileWrapper

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Calendar, Course, GeneralSettings, InformationText, PublicDocument, Slot,
    Training, TrainingSubdomain,
)

from django.conf import settings
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext, ugettext_lazy as _


def home(request):
    """Homepage view"""

    try:
        welcome_txt = InformationText.objects.get(code="ACCUEIL").content
    except InformationText.DoesNotExist:
        welcome_txt = ''

    try:
        procedure_txt = InformationText.objects.get(code="INFO_BULLE_PROCEDURE").content
    except InformationText.DoesNotExist:
        procedure_txt = ''

    try:
        offer_txt = InformationText.objects.get(code="INFO_BULLE_OFFRE").content
    except InformationText.DoesNotExist:
        offer_txt = ''

    try:
        accomp_txt = InformationText.objects.get(code="INFO_BULLE_ACCOMPAGNEMENT").content
    except InformationText.DoesNotExist:
        accomp_txt = ''

    try:
        twitter_url = GeneralSettings.objects.get(setting="TWITTER_ACCOUNT_URL").value
    except GeneralSettings.DoesNotExist:
        twitter_url = ''

    context = {
        'welcome_txt': welcome_txt,
        'procedure_txt': procedure_txt,
        'offer_txt': offer_txt,
        'accomp_txt': accomp_txt,
        'twitter_url': twitter_url,
    }
    return render(request, 'home.html', context)


def offer(request):
    """Offer view"""

    subdomains = TrainingSubdomain.activated.filter(training_domain__active=True).order_by(
        'training_domain', 'label'
    )

    context = {
        'subdomains': subdomains,
    }
    return render(request, 'offer.html', context)


def accompanying(request):
    """Accompanying view"""
    context = {
        'accomp_txt': InformationText.objects.get(code="ACCOMPAGNEMENT").content,
        'accomp_docs': AccompanyingDocument.activated.all(),
    }
    return render(request, 'accompanying.html', context)


def procedure(request):
    """Procedure view"""
    context = {
        'procedure_txt': InformationText.objects.get(code="PROCEDURE_LYCEE").content,
        'procedure_group_txt': InformationText.objects.get(
            code="PROCEDURE_IMMERSION_GROUPE"
        ).content,
    }
    return render(request, 'procedure.html', context)


def serve_accompanying_document(request, accompanying_document_id):
    """Serve accompanying documents files"""
    try:
        doc = get_object_or_404(AccompanyingDocument, pk=accompanying_document_id)

        _file = doc.document.path
        _file_type = mimetypes.guess_type(_file)[0]

        chunk_size = 8192
        response = StreamingHttpResponse(
            FileWrapper(open(_file, 'rb'), chunk_size), content_type=_file_type
        )
        response['Content-Length'] = os.path.getsize(_file)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            os.path.basename(_file)
        )

    except Exception as e:
        return HttpResponseNotFound()

    return response


def serve_public_document(request, public_document_id):
    """Serve public documents files"""
    try:
        doc = get_object_or_404(PublicDocument, pk=public_document_id)

        _file = doc.document.path
        _file_type = mimetypes.guess_type(_file)[0]

        chunk_size = 8192
        response = StreamingHttpResponse(
            FileWrapper(open(_file, 'rb'), chunk_size), content_type=_file_type
        )
        response['Content-Length'] = os.path.getsize(_file)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            os.path.basename(_file)
        )

    except Exception as e:
        return HttpResponseNotFound()

    return response


def offer_subdomain(request, subdomain_id):
    """Subdomain offer view"""

    trainings = Training.objects.filter(training_subdomains=subdomain_id, active=True)
    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)

    data = []

    # determine dates range to use
    calendar = Calendar.objects.first()
    # TODO: poc for now maybe refactor dirty code in a model method !!!!
    today = datetime.datetime.today().date()
    reg_start_date = reg_end_date = datetime.date(1, 1, 1)
    try:
        # Year mode
        if calendar.calendar_mode == 'YEAR':
            cal_start_date = calendar.year_registration_start_date
            cal_end_date = calendar.year_end_date
            reg_start_date = calendar.year_registration_start_date
        # semester mode
        else:
            if calendar.semester1_start_date <= today <= calendar.semester1_end_date:
                cal_start_date = calendar.semester1_start_date
                cal_end_date = calendar.semester1_end_date
                reg_start_date = calendar.semester1_registration_start_date
            elif calendar.semester2_start_date <= today <= calendar.semester2_end_date:
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
                'slots': slots,
                'alert': (slots.filter(n_places=0).count() > 0 or not slots),
            }
            data.append(training_data.copy())

    context = {
        'subdomain': subdomain,
        'data': data,
        'reg_start_date': reg_start_date,
        'today': today,
        'cal_start_date': cal_start_date,
        'cal_end_date': cal_end_date,
    }

    return render(request, 'offer_subdomains.html', context)
