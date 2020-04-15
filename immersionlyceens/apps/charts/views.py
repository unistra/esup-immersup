import json
import logging
import requests
from datetime import datetime

from django.utils.translation import gettext, ugettext_lazy as _
from django.shortcuts import redirect, render
from immersionlyceens.decorators import groups_required

from immersionlyceens.apps.core.models import HighSchool, HigherEducationInstitution
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
    highschools = []
    highschools_ids = []
    higher_institutions = []
    higher_institutions_ids = []

    _insts = request.POST.get('insts')

    try:
        level_filter = int(request.POST.get('level', 0))
    except ValueError:
        level_filter = 0 # default : all levels

    if _insts:
        try:
            insts = json.loads(_insts)

            hs = {h.pk:h for h in HighSchool.objects.all()}
            higher = {h.uai_code:h for h in HigherEducationInstitution.objects.all()}

            highschools = sorted(
                [ "%s - %s" % (hs[inst[1]].city.title(), hs[inst[1]].label) for inst in insts if inst[0] == 0 ]
            )
            higher_institutions = sorted(
                [ "%s - %s" % (higher[inst[1]].city.title(), higher[inst[1]].label) for inst in insts if inst[0] == 1 ]
            )

            highschools_ids = [ inst[1] for inst in insts if inst[0]==0 ]
            higher_institutions_ids = [ inst[1] for inst in insts if inst[0]==1 ]

        except Exception as e:
            logger.exception("Filter form values error")

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

    if request.user.is_high_school_manager():
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

    # TODO : reuse global_domains_charts ?

    highschools = []
    highschools_ids = []
    higher_institutions = []
    higher_institutions_ids = []

    _insts = request.POST.get('insts')

    try:
        part2_level_filter = int(request.POST.get('level', 0))
    except ValueError:
        part2_level_filter = 0 # default : all levels

    if _insts:
        try:
            insts = json.loads(_insts)

            hs = {h.pk:h for h in HighSchool.objects.all()}
            higher = {h.uai_code:h for h in HigherEducationInstitution.objects.all()}

            highschools = sorted(
                [ "%s - %s" % (hs[inst[1]].city.title(), hs[inst[1]].label) for inst in insts if inst[0] == 0 ]
            )
            higher_institutions = sorted(
                [ "%s - %s" % (higher[inst[1]].city.title(), higher[inst[1]].label) for inst in insts if inst[0] == 1 ]
            )

            highschools_ids = [ inst[1] for inst in insts if inst[0]==0 ]
            higher_institutions_ids = [ inst[1] for inst in insts if inst[0]==1 ]

        except Exception as e:
            logger.exception("Filter form values error")

    # High school levels
    # the third one ('above bachelor') will also include the higher education institutions students
    levels = [(0, _("All"))] + HighSchoolStudentRecord.LEVELS

    context = {
        'highschools_ids': highschools_ids,
        'highschools': highschools,
        'higher_institutions_ids': higher_institutions_ids,
        'higher_institutions': higher_institutions,
        'levels': levels,
        'part1_level_filter': 0,
        'part2_level_filter': part2_level_filter,
    }

    return render(request, 'charts/registrations_charts.html', context=context)