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

from immersionlyceens.apps.core.models import AccompanyingDocument, PublicDocument


def home(request):
    return render(request, 'base.html')


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

    except Exception as e:
        return HttpResponseNotFound()

    return response
