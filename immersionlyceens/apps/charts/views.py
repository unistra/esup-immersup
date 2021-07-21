import json
import logging
import requests
from datetime import datetime

from django.utils.translation import gettext, ugettext_lazy as _
from django.shortcuts import redirect, render
from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import HighSchool, HigherEducationInstitution
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

from .utils import process_request_filters

logger = logging.getLogger(__name__)

@groups_required('SCUIO-IP', 'REF-LYC')
def highschool_charts(request):
    """
    High school(s) charts by student levels
    """
    filter = {}

    if request.user.is_high_school_manager() and request.user.highschool:
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

    if request.user.is_high_school_manager() and request.user.highschool:
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

    # Get filters from request POST data
    level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions = \
        process_request_filters(request)

    # High school levels
    # the third one ('above bachelor') will also include the higher education institutions students
    levels = [(0, _("All"))] + HighSchoolStudentRecord.LEVELS

    context = {
        'highschools_ids': highschools_ids,
        'highschools': highschools,
        'higher_institutions_ids': higher_institutions_ids,
        'higher_institutions': higher_institutions,
        'levels': levels,
        'level_filter': level_filter,
    }

    return render(request, 'charts/global_domains_charts.html', context=context)


@groups_required('SCUIO-IP', 'REF-LYC')
def trainings_charts(request):
    """
    Registration statistics by trainings
    """
    filter = {}
    high_school_name = None

    if request.user.is_high_school_manager() and request.user.highschool:
        high_school_name = request.user.highschool.label
        filter['pk'] = request.user.highschool.id

    highschools = [
        {'id': h.id, 'label':h.label, 'city': h.city }
        for h in HighSchool.objects.filter(**filter).order_by('city','label')
    ]

    context = {
        'high_school_name': high_school_name,
        'levels': HighSchoolStudentRecord.LEVELS,
        'highschools': highschools,
        'highschool_id': filter.get('pk', ''),
    }
    return render(request, 'charts/trainings_charts.html', context=context)


@groups_required('SCUIO-IP')
def global_registrations_charts(request):
    """
    Registration and participation charts by student levels
    """

    # Get filters from request POST data
    part2_level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions = \
        process_request_filters(request)

    # High school levels
    # the third one ('above bachelor') will also include the higher education institutions students
    levels = [(0, _("All"))] + HighSchoolStudentRecord.LEVELS

    context = {
        'highschools_ids': highschools_ids,
        'highschools': highschools,
        'higher_institutions_ids': higher_institutions_ids,
        'higher_institutions': higher_institutions,
        'levels': levels,
        'part1_level_filter': request.session.get("current_level_filter", 0),
        'level_filter': part2_level_filter,
    }

    return render(request, 'charts/registrations_charts.html', context=context)


@groups_required('SCUIO-IP')
def global_slots_charts(request):
    """
    Slots statistics by components and trainings
    """

    context = {
    }

    return render(request, 'charts/global_slots_charts.html', context=context)