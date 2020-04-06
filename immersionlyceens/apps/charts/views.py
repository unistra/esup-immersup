import json
import logging
import requests
from datetime import datetime

from django.utils.translation import gettext, ugettext_lazy as _
from django.shortcuts import redirect, render
from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import HighSchool
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


logger = logging.getLogger(__name__)

@groups_required('SCUIO-IP', 'REF-LYC')
def highschool_charts(request):
    """
    High school(s) charts by student levels
    """
    filter = {}

    if request.user.is_high_school_manager():
        filter['pk'] = request.user.highschool.id

    highschools = [
        {'id': h.id, 'label':h.label, 'city': h.city }
        for h in HighSchool.objects.filter(**filter).order_by('city','label')
    ]

    context = {
        'highschools': highschools,
        'highschool_id': filter.get('pk', '')
    }

    return render(request, 'charts/highschool_charts.html', context=context)


@groups_required('SCUIO-IP', 'REF-LYC')
def highschool_domains_charts(request):
    """
    High school(s) charts by domains
    """
    filter = {}

    if request.user.is_high_school_manager():
        filter['pk'] = request.user.highschool.id

    highschools = [
        {'id': h.id, 'label':h.label, 'city': h.city }
        for h in HighSchool.objects.filter(**filter).order_by('city','label')
    ]

    levels = [(0, _("All"))] + HighSchoolStudentRecord.LEVELS

    context = {
        'highschools': highschools,
        'highschool_id': filter.get('pk', ''),
        'levels': levels,
    }

    return render(request, 'charts/highschool_domains_charts.html', context=context)


@groups_required('SCUIO-IP')
def global_domains_charts(request):
    """
    All institutions charts by domains, with filters on institutions
    """
    filter = {}

    highschools = [
        {'id': h.id, 'label':h.label, 'city': h.city }
        for h in HighSchool.objects.filter(**filter).order_by('city','label')
    ]

    levels = [(0, _("All"))] + HighSchoolStudentRecord.LEVELS

    context = {
        'highschools': highschools,
        'highschool_id': filter.get('pk', ''),
        'levels': levels,
    }

    return render(request, 'charts/global_domains_charts.html', context=context)