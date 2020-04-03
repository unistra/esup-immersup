from django.views.generic import TemplateView

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext, ugettext_lazy as _

from immersionlyceens.apps.core.models import (
    Immersion, ImmersionUser, TrainingDomain, TrainingSubdomain
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


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
