import json
import logging
import requests
from datetime import datetime

from django.utils.translation import gettext, gettext_lazy as _
from django.shortcuts import redirect, render
from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import (
    HighSchool, HigherEducationInstitution, HighSchoolLevel, PostBachelorLevel, StudentLevel, Establishment
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

from .utils import process_request_filters

logger = logging.getLogger(__name__)


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
def global_domains_charts(request, my_trainings=False):
    """
    All institutions charts by domains, with filters on institutions
    """
    filter_by_my_trainings = my_trainings

    # Get filters from request POST data
    part2_level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions, structure_ids = \
        process_request_filters(request, my_trainings)

    part2_filters = {
        'level': part2_level_filter,
        'highschools_ids': highschools_ids,
        'highschools': highschools,
        'higher_institutions_ids': higher_institutions_ids,
        'higher_institutions': higher_institutions,
        'structure_ids': structure_ids
    }

    # High school levels
    # the third one ('above bachelor') will also include the higher education institutions students
    # levels = [(0, _("All"))] + [(level.id, level.label) for level in HighSchoolLevel.objects.order_by('order')]

    context = {
        'filter_by_my_trainings': filter_by_my_trainings,
        'include_structures': False,
        'levels': HighSchoolLevel.objects.filter(active=True).order_by('order'),
        'part2_filters': part2_filters
    }

    return render(request, 'charts/global_domains_charts.html', context=context)


@groups_required('REF-ETAB-MAITRE', 'REF-ETAB', 'REF-TEC', 'REF-LYC', 'REF-STR')
def global_trainings_charts(request, my_trainings=False):
    """
    Registration statistics by trainings for establishments and highschools
    """
    filter = {}
    high_school_name = None
    high_school_levels_filters = { 'active': True }
    filter_by_my_trainings = my_trainings

    if request.user.is_high_school_manager() and request.user.highschool:
        high_school_name = f"{request.user.highschool.label} - {request.user.highschool.city}"
        filter['pk'] = request.user.highschool.id

    if filter_by_my_trainings or not request.user.is_high_school_manager():
        high_school_levels_filters['is_post_bachelor'] = False

    highschools = [
        {'id': h.id, 'label': h.label, 'city': h.city}
        for h in HighSchool.objects.filter(**filter).order_by('city', 'label')
    ]

    # This will be only useful to structure managers
    structures = [
        {'id': s.id, 'label': s.label}
        for s in request.user.structures.all().order_by('label')
    ]

    # Do not include post_bachelor pupils levels as they will be added to Students count
    context = {
        'highschools': highschools,
        'highschool_id': filter.get('pk', ''),
        'high_school_name': high_school_name,
        'structures': structures,
        'structure_id': structures[0]['id'] if structures else '',
        'filter_by_my_trainings': filter_by_my_trainings,
        'high_school_levels': HighSchoolLevel.objects.filter(**high_school_levels_filters).order_by('order'),
    }
    return render(request, 'charts/global_trainings_charts.html', context=context)


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC', 'REF-STR')
def global_registrations_charts(request, my_trainings=False):
    """
    Registration and participation charts by student levels
    """
    user = request.user
    highschool_id = None
    highschool_name = None
    highschool_filter = {}
    high_school_levels_filters = {'active': True}
    filter_by_my_trainings = my_trainings

    # Get filters from request POST data
    # TODO : move these into a dictionary
    part2_level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions, structure_ids = \
        process_request_filters(request, my_trainings)

    part2_filters = {
        'level': part2_level_filter,
        'highschools_ids': highschools_ids,
        'highschools': highschools,
        'higher_institutions_ids': higher_institutions_ids,
        'higher_institutions': higher_institutions,
        'structure_ids': structure_ids
    }

    if user.is_high_school_manager() and user.highschool:
        highschool_id = user.highschool.id
        highschool_name = f"{user.highschool.label} - {user.highschool.city}"
        highschool_filter['pk'] = highschool_id

    if filter_by_my_trainings or not user.is_high_school_manager():
        high_school_levels_filters['is_post_bachelor'] = False

    # This will be only useful to structure managers
    structures = [
        {'id': s.id, 'label': s.label}
        for s in user.get_authorized_structures().order_by('label')
    ]

    if filter_by_my_trainings:
        highschool_filter['postbac_immersion'] = True

    context = {
        'highschool_id': highschool_id,
        'highschool_name': highschool_name,
        'all_highschools': HighSchool.objects.filter(**highschool_filter).order_by('city', 'label'),
        'filter_by_my_trainings': filter_by_my_trainings,
        'structures': structures,
        'structure_id': structures[0]['id'] if structures and user.is_structure_manager() else '',
        'include_structures': True,
        'levels': HighSchoolLevel.objects.filter(active=True).order_by('order'),
        'part1_level_filter': request.session.get("current_level_filter", 0),
        'part2_filters': part2_filters
    }

    return render(request, 'charts/registrations_charts.html', context=context)


@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-STR')
def slots_charts(request, my_trainings=False):
    """
    Slots charts
    """
    user = request.user

    structures = user.get_authorized_structures()
    establishments = Establishment.objects.filter(active=True).order_by('label')

    establishment_id = request.GET.get("establishment_id", None)

    context = {
        'establishments': establishments,
        'establishment_id': establishment_id
    }

    return render(request, 'charts/slots_charts.html', context=context)
