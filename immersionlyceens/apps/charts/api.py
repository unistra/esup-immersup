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

    providers = [
        gettext('Pupil in year 12 / 11th grade student'), # level = 1
        gettext('Pupil in year 13 / 12th grade student'), # level = 2
        gettext('Above A Level / High-School Degree') # level = 3
    ]

    options = {
        'scales': {
            'xAxes' : [{
                'stacked': True,
            }],
            'yAxes': [
                {
                    'stacked': True,
                    'ticks': {
                        'beginAtZero': True,
                        'stepSize': 1,
                    },
                }
            ]
        }
    }

    response = {
        'label': _("Registered students by level"),
        'labels': labels,
        'providers': providers,
        'title': _("High school students by level"),
        'options': options,
        'level_1': [],
        'level_2': [],
        'level_3': [],
    }

    # level 1
    qs = ImmersionUser.objects.filter(high_school_student_record__highschool__id=highschool_id)

    for level in [1, 2, 3]:
        users = qs.filter(high_school_student_record__level=level)
        platform = users.count()
        registered = users.filter(immersions__isnull=False).distinct().count()
        att = users.filter(immersions__attendance_status=1).distinct().count()

        response['level_%s' % level] = [platform, registered, att]

    return JsonResponse(response, safe=False)
