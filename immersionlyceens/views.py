# -*- coding: utf-8 -*-

import mimetypes
import os
from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render

from immersionlyceens.apps.core.models import (
    AccompanyingDocument,
    GeneralSettings,
    InformationText,
    PublicDocument,
)


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
        twitter_url = InformationText.objects.get(code="TWITTER_ACCOUNT_URL").value
    except InformationText.DoesNotExist:
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
    context = {}
    return render(request, 'offer.html', context)


def accompanying(request):
    """Accompanying view"""
    context = {}
    return render(request, 'accompanying.html', context)


def procedure(request):
    """Procedure view"""
    context = {}
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
