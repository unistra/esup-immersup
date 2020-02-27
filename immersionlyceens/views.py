# -*- coding: utf-8 -*-

import mimetypes
import os
from wsgiref.util import FileWrapper

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, GeneralSettings, InformationText, PublicDocument, Training,
    TrainingSubdomain,
)

from django.conf import settings
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render


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

    subdomains = TrainingSubdomain.activated.all().order_by('training_domain', 'label')

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

    trainings = Training.objects.filter(training_subdomains=subdomain_id)
    subdomain = get_object_or_404(TrainingSubdomain, pk=subdomain_id, active=True)
    # subdomain = TrainingSubdomain.activated.all().order_by('training_domain', 'label')

    context = {
        'trainings': trainings,
        'subdomain': subdomain,
    }
    return render(request, 'offer_subdomains.html', context)
