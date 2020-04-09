import ast
import json
import logging

from functools import reduce
from django.db.models import Q
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext, ugettext_lazy as _

from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request

from immersionlyceens.apps.core.models import (
    Immersion, ImmersionUser, TrainingDomain, TrainingSubdomain, HigherEducationInstitution,
    HighSchool
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord


logger = logging.getLogger(__name__)

def highschool_charts(request, highschool_id):
    """
    Data for amcharts 4
    Vertical bars format
    """
    student_levels = [
        gettext('Pupil in year 12 / 11th grade student'), # level = 1
        gettext('Pupil in year 13 / 12th grade student'), # level = 2
        gettext('Above A Level / High-School Degree') # level = 3
    ]

    # Each dataset represents a student level
    datasets = [
        {
            'name': gettext("Registered users count"),
        },
        {
            'name':  gettext("Registered to at least one immersion"),
        },
        {
            'name':  gettext("Attended to at least one immersion"),
        },
    ]

    axes = {
        'x': [{
            "type": "CategoryAxis",
            "dataFields": {
                "category": "name",
            }
        }],
        'y': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
        }],
    }

    series = [
        {
            "name": student_levels[0],
            "type": "ColumnSeries",
            "stacked": True,

            "dataFields": {
                "valueY": student_levels[0],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": student_levels[0] + "\n{valueY}",
                },
            }
        },
        {
            "name": student_levels[1],
            "type": "ColumnSeries",
            "stacked": True,
            "dataFields": {
                "valueY": student_levels[1],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": student_levels[1] + "\n{valueY}",
                },
            }
        },
        {
            "name": student_levels[2],
            "type": "ColumnSeries",
            "stacked": True,
            "dataFields": {
                "valueY": student_levels[2],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": student_levels[2] + "\n{valueY}",
                },
            }
        },
    ]

    qs = ImmersionUser.objects.filter(high_school_student_record__highschool__id=highschool_id)

    for level in [1, 2, 3]:
        users = qs.filter(high_school_student_record__level=level)
        datasets[0][student_levels[level-1]] = users.count() # plaform
        datasets[1][student_levels[level-1]] = users.filter(immersions__isnull=False).distinct().count() # registered
        datasets[2][student_levels[level-1]] = users.filter(immersions__attendance_status=1).distinct().count() # attended to 1 immersion

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


def highschool_domains_charts(request, highschool_id, level=0):
    """
    Data for amcharts 4
    Pie chart format
    """
    datasets = []

    series = [
        {
            "type": "PieSeries",
            "dataFields": {
                "value": "count",
                "category": "domain",
            },
        },
    ]

    domains = [ domain for domain in TrainingDomain.objects.all().order_by('label') ]

    for domain in domains:
        qs = Immersion.objects.prefetch_related(
            'slot__course__training__training_subdomains__training_domain',
            'student__high_school_student_record__highschool')\
            .filter(
            slot__course__training__training_subdomains__training_domain__id=domain.id,
            student__high_school_student_record__highschool__id=highschool_id,
        )

        if level in [1,2,3]:
            qs = qs.filter(student__high_school_student_record__level=level)

        data = {
            "domain": domain.label,
            "count": qs.count(),
            "subData": [],
        }

        for subdomain in domain.Subdomains.all():
            sub_data = {
                "name": subdomain.label,
                "count": qs.filter(slot__course__training__training_subdomains=subdomain).count(),
            }
            data['subData'].append(sub_data.copy())

        datasets.append(data.copy())

    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@is_post_request
@groups_required('SCUIO-IP')
def global_domains_charts(request):
    """
    Data for amcharts 4
    Pie chart format
    all parameters are in request
    """
    immersions_filter = {}

    # Parse filters in POST request
    _highschools_ids = request.POST.get("highschools_ids")
    _higher_institutions_ids = request.POST.get("higher_institutions_ids")

    try:
        level = int(request.POST.get("level", 0))
    except ValueError:
        level = 0

    # Filter on highschools or higher education institutions
    if _highschools_ids:
        try:
            highschools_ids = ast.literal_eval(_highschools_ids)
            if highschools_ids:
                immersions_filter["student__high_school_student_record__highschool__id__in"] = highschools_ids
        except Exception as e:
            logger.exception("Cannot parse 'highschools_ids' parameter")

    if _higher_institutions_ids:
        try:
            higher_institutions_ids = ast.literal_eval(_higher_institutions_ids)
            if higher_institutions_ids:
                immersions_filter["student__student_record__uai_code__in"] = higher_institutions_ids
        except Exception as e:
            logger.exception("Cannot parse 'higher education institutions ids' parameter")

    datasets = []

    series = [
        {
            "type": "PieSeries",
            "dataFields": {
                "value": "count",
                "category": "domain",
            },
        },
    ]

    domains = [ domain for domain in TrainingDomain.objects.all().order_by('label') ]

    for domain in domains:
        # Get all immersions for this domain, filter in schools as requested
        qs = Immersion.objects.prefetch_related(
            'slot__course__training__training_subdomains__training_domain',
            'student__high_school_student_record__highschool')\
            .filter(
            slot__course__training__training_subdomains__training_domain__id=domain.id,
        )

        # Level filter
        if level in [1, 2]:  # high schools levels only : exclude higher education students
            qs = qs.filter(student__high_school_student_record__level=level)
            qs = qs.exclude(student__student_record__isnull=False)
        elif level == 3:
            # 3rd high school students level + all higher education levels
            higher_levels = [l[0] for l in StudentRecord.LEVELS]
            qs = qs.filter(
                Q(student__high_school_student_record__level=level)
                | Q(student__student_record__level__in=higher_levels))

        if immersions_filter:
            qs = qs.filter(reduce(lambda x, y: x | y, [Q(**{'%s' % k : v}) for k, v in immersions_filter.items()]))

        data = {
            "domain": domain.label,
            "count": qs.count(),
            "subData": [],
        }

        for subdomain in domain.Subdomains.all():
            sub_data = {
                "name": subdomain.label,
                "count": qs.filter(slot__course__training__training_subdomains=subdomain).count(),
            }
            data['subData'].append(sub_data.copy())

        datasets.append(data.copy())

    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required("SCUIO-IP")
def get_charts_filters_data(request):
    response = {'msg': '', 'data': []}

    # get highschools and higher education institutions
    highschools = HighSchool.objects.filter(student_records__isnull=False).distinct()

    for highschool in highschools:
        institution_data = {
            'institution': highschool.label,
            'institution_id': highschool.id,
            'type': _('highschool'),
            'type_code': 0,
            'city': "%s - %s" % (highschool.zip_code, highschool.city),
            'department': "%s" % highschool.zip_code[0:2], # Todo add departments model somewhere
            'country': '',
        }

        response['data'].append(institution_data.copy())

    higher_institutions_uai = { obj.uai_code:obj for obj in HigherEducationInstitution.objects.all() }

    uai_codes = StudentRecord.objects.all().values_list('uai_code', flat=True).distinct()

    for uai_code in uai_codes:
        institution_data = {
            'institution': '',
            'institution_id': uai_code,
            'type': _('Higher education institution'),
            'type_code': 1,
            'city': '',
            'department': '',
            'country': '',
        }
        # Try to find institution by name or UAI code (a not so good design)
        institution = higher_institutions_uai.get(uai_code, None)
        if institution:
            institution_data['institution'] = institution.label
            institution_data['city'] = "%s - %s" % (institution.zip_code, institution.city),
            institution_data['department'] = institution.department,
            institution_data['country'] = institution.country,
        else:
            institution_data['institution'] = uai_code

        response['data'].append(institution_data.copy())

    return JsonResponse(response, safe=False)

