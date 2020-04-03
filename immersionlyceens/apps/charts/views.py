import json
import logging
import requests
from datetime import datetime

from django.utils.translation import gettext, ugettext_lazy as _
from django.shortcuts import redirect, render
from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import HighSchool


logger = logging.getLogger(__name__)

@groups_required('SCUIO-IP', 'REF-LYC')
def highschool_charts(request):
    """
    High school(s) charts
    """
    filter = {}

    if request.user.is_high_school_manager():
        filter['pk'] = request.user.highschool.id

    highschools = [
        {'id': h.id, 'label':h.label} for h in HighSchool.objects.filter(**filter).order_by('label')
    ]

    context = {
        'highschools': highschools,
        'highschool_id': filter.get('pk', '')
    }

    return render(request, 'charts/highschool_charts.html', context=context)