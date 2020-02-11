# -*- coding: utf-8 -*-

import mimetypes
import os
from wsgiref.util import FileWrapper

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, GeneralSettings, InformationText, PublicDocument,
)

from django.conf import settings
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render


def home(request):
    """Homepage view"""
    context = {
        'welcome_txt': InformationText.objects.get(code="ACCUEIL").content,
        'procedure_txt': InformationText.objects.get(code="INFO_BULLE_PROCEDURE").content,
        'offer_txt': InformationText.objects.get(code="INFO_BULLE_OFFRE").content,
        'accomp_txt': InformationText.objects.get(code="INFO_BULLE_ACCOMPAGNEMENT").content,
        'twitter_url': GeneralSettings.objects.get(setting="TWITTER_ACCOUNT_URL").value,
    }
    return render(request, 'home.html', context)


def offer(request):
    """Offer view"""
    context = {}
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
