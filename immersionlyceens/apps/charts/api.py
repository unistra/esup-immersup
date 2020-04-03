from django.views.generic import TemplateView

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext, ugettext_lazy as _

from immersionlyceens.apps.core.models import Immersion, ImmersionUser
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


def highschool_charts(request, highschool_id):
    # highschool_id = self.kwargs.get('highschool_id', None)

    labels = [
        gettext("Registered users count"),
        gettext("Registered to at least one immersion"),
        gettext("Attended to at least one immersion"),
    ]

    categories = [
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
        }],
    }

    series = [
        {
            "name": categories[0],
            "type": "ColumnSeries",
            "stacked": True,

            "dataFields": {
                "valueY": categories[0],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": categories[0] + "\n{valueY}",
                },
            }
        },
        {
            "name": categories[1],
            "type": "ColumnSeries",
            "stacked": True,
            "dataFields": {
                "valueY": categories[1],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": categories[1] + "\n{valueY}",
                },
            }
        },
        {
            "name": categories[2],
            "type": "ColumnSeries",
            "stacked": True,
            "dataFields": {
                "valueY": categories[2],
                "categoryX": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": categories[2] + "\n{valueY}",
                },
            }
        },
    ]

    qs = ImmersionUser.objects.filter(high_school_student_record__highschool__id=highschool_id)

    for level in [1, 2, 3]:
        users = qs.filter(high_school_student_record__level=level)
        datasets[0][categories[level-1]] = users.count() # plaform
        datasets[1][categories[level-1]] = users.filter(immersions__isnull=False).distinct().count() # registered
        datasets[2][categories[level-1]] = users.filter(immersions__attendance_status=1).distinct().count() # attended to 1 immersion

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)
