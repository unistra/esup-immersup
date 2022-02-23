import ast
import csv
import json
import logging

from collections import defaultdict
from functools import reduce
from django.db.models import Q
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext, gettext_lazy as _

from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request

from immersionlyceens.apps.core.models import (
    Structure, Immersion, ImmersionUser, TrainingDomain, TrainingSubdomain, HigherEducationInstitution,
    HighSchool, Training, Slot, Course, HighSchoolLevel, PostBachelorLevel, StudentLevel
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord


logger = logging.getLogger(__name__)

@groups_required("REF-ETAB", "REF-LYC", "REF-ETAB-MAITRE", "REF-TEC")
def highschool_charts(request, highschool_id):
    """
    Data for amcharts 4
    Vertical bars format
    """
    # TODO : Merge with get_registration_chart ?

    # Each dataset represents a student level
    datasets = [
        {
            'name': gettext("Registrations count"),
        },
        {
            'name':  gettext("Registrations to at least one immersion"),
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

    series = []
    for level in HighSchoolLevel.objects.order_by('order'):
        series.append(
            {
                "name": level.label,
                "type": "ColumnSeries",
                "stacked": True,

                "dataFields": {
                    "valueY": level.label,
                    "categoryX": "name",
                },
                "columns": {
                    "template": {
                        "width": "30%",
                        "tooltipText": level.label + "\n{valueY}",
                    },
                }
            },
        )

    qs = ImmersionUser.objects\
        .prefetch_related('high_school_student_record__highschool', 'immersions__cancellation_type')\
        .filter(high_school_student_record__highschool__id=highschool_id)

    for level in HighSchoolLevel.objects.order_by('order'):
        users = qs.filter(high_school_student_record__level=level.id)
        datasets[0][level.label] = users.count() # plaform
        datasets[1][level.label] = users.filter(
            immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count() # registered
        datasets[2][level.label] = users.filter(immersions__attendance_status=1).distinct().count() # attended to 1 immersion

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@groups_required("REF-ETAB", "REF-LYC", "REF-ETAB-MAITRE", "REF-TEC")
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
            cancellation_type__isnull=True
        )

        try:
            high_school_level = HighSchoolLevel.objects.get(pk=level)
        except HighSchoolLevel.DoesNotExist:
            high_school_level = None
            level = 0

        if high_school_level and not high_school_level.is_post_bachelor:
            qs = qs.filter(student__high_school_student_record__level=level)

        if qs.count():
            data = {
                "domain": domain.label,
                "count": qs.count(),
                "subData": [],
            }

            for subdomain in domain.Subdomains.all():
                subcount = qs.filter(slot__course__training__training_subdomains=subdomain).count()

                if subcount:
                    sub_data = {
                        "name": subdomain.label,
                        "count": subcount,
                    }
                    data['subData'].append(sub_data.copy())

            datasets.append(data.copy())

    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@is_post_request
@groups_required('REF-ETAB', "REF-ETAB-MAITRE", "REF-TEC")
def global_domains_charts(request):
    """
    Data for amcharts 4
    Pie chart format
    all parameters are in request.POST
    """
    immersions_filter = {}

    # Parse filters in POST request
    _highschools_ids = request.POST.getlist("highschools_ids[]")
    _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")

    try:
        level = int(request.POST.get("level", 0))
    except ValueError:
        level = 0

    # Filter on highschools or higher education institutions
    if _highschools_ids:
        immersions_filter["student__high_school_student_record__highschool__id__in"] = _highschools_ids

    if _higher_institutions_ids:
        immersions_filter["student__student_record__uai_code__in"] = _higher_institutions_ids

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
        # Get all immersions for this domain, filter by schools as requested
        qs = Immersion.objects.prefetch_related(
            'slot__course__training__training_subdomains__training_domain',
            'student__high_school_student_record__highschool')\
            .filter(
            slot__course__training__training_subdomains__training_domain__id=domain.id,
            cancellation_type__isnull=True
        )

        # Level filter
        # FixMe : find a way to define these levels
        if level in [1, 2]:  # high schools levels only : exclude higher education students
            qs = qs.filter(student__high_school_student_record__level=level)
            qs = qs.exclude(student__student_record__isnull=False)
        elif level == 3:
            # 3rd high school students level + all higher education levels
            higher_levels = [l.id for l in StudentLevel.objects.order_by('order')]
            qs = qs.filter(
                Q(student__high_school_student_record__level=level)
                | Q(student__student_record__level__in=higher_levels))

        if immersions_filter:
            qs = qs.filter(reduce(lambda x, y: x | y, [Q(**{'%s' % k : v}) for k, v in immersions_filter.items()]))

        if qs.count():
            data = {
                "domain": domain.label,
                "count": qs.count(),
                "subData": [],
            }

            for subdomain in domain.Subdomains.all():
                subcount = qs.filter(slot__course__training__training_subdomains=subdomain).count()

                if subcount:
                    sub_data = {
                        "name": subdomain.label,
                        "count": subcount,
                    }
                    data['subData'].append(sub_data.copy())

            datasets.append(data.copy())

    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_charts_filters_data(request):
    response = {'msg': '', 'data': []}

    # get highschools and higher education institutions
    highschools = HighSchool.objects.filter(student_records__isnull=False).distinct()

    for highschool in highschools:
        institution_data = {
            'institution': highschool.label,
            'institution_id': highschool.id,
            'type': _('Highschool'),
            'type_code': 0,
            'city': f"{highschool.zip_code} - {highschool.city}",
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
            institution_data['city'] = f"{institution.zip_code} - {institution.city}",
            institution_data['department'] = institution.department,
            institution_data['country'] = institution.country,
        else:
            institution_data['institution'] = uai_code

        response['data'].append(institution_data.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", "REF-LYC", "REF-ETAB-MAITRE", "REF-TEC")
def get_highschool_trainings_charts(request):
    """
    Statistics by training
     - for a single high school (if referent)
     - REF-ETAB users can choose a high school or leave empty for all institutions
    """

    highschool_id = request.GET.get("highschool_id")
    show_empty_trainings = request.GET.get("empty_trainings", False) == "true"

    response = {'msg': '', 'data': []}

    students_filter = {
        'high_school_student_record__isnull': False
    }
    immersions_filter = {
        'student__high_school_student_record__isnull': False
    }

    trainings_filter = {
        'active': True
    }

    # Do not include trainings with no registration/students
    if not show_empty_trainings:
        trainings_filter['courses__slots__immersions__isnull'] = False

    trainings = Training.objects.prefetch_related('training_subdomains__training_domain').filter(**trainings_filter)

    # Default table ordering
    response['order'] = [
      [0, "asc"],
      [1, "asc"],
    ]

    # Filters
    response['yadcf'] = []

    # override highschool id if request.user is a high school manager
    if request.user.is_high_school_manager() and request.user.highschool:
        highschool_id = request.user.highschool.id

    if highschool_id:
        students_filter['high_school_student_record__highschool__id'] = highschool_id
        immersions_filter['student__high_school_student_record__highschool__id'] = highschool_id

    # Next columns definition
    # We need this because some high school levels can be deactivated
    response['columns'] = [
        {
            "data": 'training_label',
            "name": _("Training"),
            "filter": "training_filter"
        },
        {
            "data": 'domain_label',
            "name": _("Domain/Subdomain"),
            "filter": "domain_filter"
        },
        {
            "data": 'unique_students',
            "name": _("Students cnt"),
        },
        *[{
            'data': f"unique_students_lvl{level.id}",
            "name": f"{_('Students cnt')}<br>{level.label}",
            'visible': False
          } for level in HighSchoolLevel.objects.filter(active=True)
        ],
        {
            "data": 'all_registrations',
            "name": _("Registrations"),
        },
        *[{
            'data': f"registrations_lvl{level.id}",
            "name": f"{_('Registrations')}<br>{level.label}",
            'visible': False
          } for level in HighSchoolLevel.objects.filter(active=True)
        ]
    ]

    response['yadcf'] += [{
        'column_selector': _("Domain/Subdomain") + ":name",
        'text_data_delimiter': "<br>",
        'filter_default_label': "",
        'filter_match_mode': "contains",
        'filter_container_id': "domain_filter",
        'style_class': "form-control form-control-sm",
        'filter_reset_button_text': False,
    },
        {
            'column_selector': _("Training") + ":name",
            'filter_default_label': "",
            'filter_match_mode': "exact",
            'filter_container_id': "training_filter",
            'style_class': "form-control form-control-sm",
            'filter_reset_button_text': False,
        }
    ]

    for training in trainings:
        base_persons_qs = ImmersionUser.objects\
            .prefetch_related('immersions__slot__course__training', 'high_school_student_record__highschool')\
            .filter(
                **students_filter,
                immersions__slot__course__training=training,
                immersions__cancellation_type__isnull=True
            )

        base_immersions_qs = Immersion.objects\
            .prefetch_related('slot__course__training', 'student__high_school_student_record__highschool')\
            .filter(
                **immersions_filter,
                slot__course__training=training,
                cancellation_type__isnull=True
            )

        # Get domains and add subdomains as a list under each, will join them right below in "domain_label"
        domain_labels = defaultdict(list)
        for subdomain in training.training_subdomains.all():
            domain_labels[subdomain.training_domain.label].append(f"- {subdomain.label}")

        row = {
            'training_label': training.label,
            'domain_label': "<br>".join([x for dom, subs in sorted(domain_labels.items()) for x in [dom] + subs]),
            # students registered to at least one immersion for this training
            'unique_students': base_persons_qs.distinct().count(),
            # registrations on all slots (not cancelled)
            'all_registrations': base_immersions_qs.count(),
        }

        for level in HighSchoolLevel.objects.filter(active=True):
            if not level.is_post_bachelor:
                row[f"unique_students_lvl{level.id}"] = base_persons_qs.filter(
                    high_school_student_record__level=level).distinct().count()

                row[f"registrations_lvl{level.id}"] = base_immersions_qs.filter(
                    student__high_school_student_record__level=level).count()
            else:
                row[f"unique_students_lvl{level.id}"] = base_persons_qs.filter(
                    Q(high_school_student_record__level=level) |
                    Q(student_record__level__in=[s.id for s in StudentLevel.objects.filter(active=True)]))\
                    .distinct().count()

                row[f"registrations_lvl{level.id}"] = base_immersions_qs.filter(
                    Q(student__high_school_student_record__level=level) |
                    Q(student__student_record__level__in=[s.id for s in StudentLevel.objects.filter(active=True)]))\
                    .count()

        response['data'].append(row.copy())

    return JsonResponse(response, safe=False)


@is_ajax_request
@groups_required("REF-ETAB", "REF-LYC", "REF-ETAB-MAITRE", "REF-TEC", "REF-STR")
def get_global_trainings_charts(request):
    """
    Statistics by training for establishments and highschools
    """
    user = request.user
    show_empty_trainings = request.GET.get("empty_trainings", False) == "true"
    structure_id = request.GET.get("structure_id")
    highschool_id = request.GET.get("highschool_id")

    response = {'msg': '', 'data': []}

    trainings_filter = {
        'active': True,
    }

    students_filter = {}
    immersions_filter = {}

    if structure_id and user.is_structure_manager() and user.structures.exists():
        trainings_filter['structures'] = structure_id

    # override highschool id if user is a high school manager
    if user.is_high_school_manager() and user.highschool:
        highschool_id = user.highschool.id

    if highschool_id:
        students_filter['high_school_student_record__highschool__id'] = highschool_id
        immersions_filter['student__high_school_student_record__highschool__id'] = highschool_id

    # Do not include trainings with no registration/students
    if not show_empty_trainings:
        trainings_filter['courses__slots__immersions__isnull'] = False

    # Default table ordering
    response['order'] = [
      [0, "asc"],
      [1, "asc"],
      [2, "asc"],
    ]

    structure_col_conditions = [
        user.is_master_establishment_manager(),
        user.is_establishment_manager(),
        user.is_operator(),
    ]

    response['columns'] = []
    response['yadcf'] = []

    if user.is_master_establishment_manager() or user.is_operator():
        response['columns'].append({
            "data": 'establishment',
            "name": "establishment",
            "title": _("Establishment"),
            "filter": "establishment_filter"
        })
        response['yadcf'].append({
          'column_selector': "establishment:name",
          'filter_default_label': "",
          'filter_match_mode': "exact",
          'filter_container_id': "establishment_filter",
          'style_class': "form-control form-control-sm",
          'filter_reset_button_text': False,
        })

    # Limit to current highschool or establishment for these users
    if user.is_high_school_manager() and user.highschool:
        trainings_filter['highschool'] = user.highschool
    elif any(structure_col_conditions):
        if user.is_establishment_manager() and user.establishment:
            trainings_filter['structures__in'] = user.get_authorized_structures()

        response['columns'].append({
            "data": "structure",
            "name": "structures",
            "title": _("Structure(s)"),
            "filter": "structure_filter"
        })
        response['yadcf'].append({
            'column_selector': "structures:name",
            'text_data_delimiter': "<br>",
            'filter_default_label': "",
            'filter_match_mode': "contains",
            'filter_container_id': "structure_filter",
            'style_class': "form-control form-control-sm",
            'filter_reset_button_text': False,
        })



    # High school managers will see different high school pupils levels
    if user.is_high_school_manager():
        pre_bachelor_levels = HighSchoolLevel.objects.filter(active=True)
    else:
        pre_bachelor_levels = HighSchoolLevel.objects.filter(active=True, is_post_bachelor=False)

    post_bachelor_levels = HighSchoolLevel.objects.filter(active=True, is_post_bachelor=True)

    # Next columns definition
    # We need this because some high school levels can be deactivated
    response['columns'] += [{
            "data": 'domain_label',
            "name": "domain_subdomain",
            "title": _("Domain/Subdomain"),
            "filter": "domain_filter"
        },
        {
            "data": 'training_label',
            "name": "training",
            "title": _("Training"),
            "filter": "training_filter"
        },
        {
            "data": 'unique_persons',
            "name": "persons_cnt",
            "title": _("Persons cnt"),
        },
        *[{
            "data": f"unique_students_lvl{level.id}",
            "name": f"pupils_cnt_{level.label}",
            "title": _("Pupils cnt<br>%s") % level.label,
            "visible": False,
          } for level in pre_bachelor_levels
        ],
        {
            "data": "unique_students",
            "name": "students_cnt",
            "title": _("Students cnt"),
            "visible": False,
        },
        {
            "data": "unique_visitors",
            "name": "visitors_cnt",
            "title": _("Visitors cnt"),
            "visible": False
        },
        {
            "data": 'all_registrations',
            "name": "registrations",
            "title": _("Registrations"),
        },
        *[{
            'data': f"registrations_lvl{level.id}",
            "name": f"registrations_{level.label}",
            "title": _("Registrations<br>%s") % level.label,
            'visible': False,
          } for level in pre_bachelor_levels
        ],
        {
            "data": "students_registrations",
            "name": "students_registrations",
            "title": _("Students<br>registrations"),
            "visible": False
        },
        {
            "data": "visitors_registrations",
            "name": "visitors_registrations",
            "title": _("Visitors<br>registrations"),
            "visible": False
        },
    ]

    # Columns list for "show all" and "hide all" shortcuts
    response['cnt_columns'] = [
      *[f"pupils_cnt_{level.label}" for level in pre_bachelor_levels],
    ]

    response['registrations_columns'] = [
      *[f"registrations_{level.label}" for level in pre_bachelor_levels],
    ]

    # Add some columns if user is not a high school manager
    if not user.is_high_school_manager():
        response['cnt_columns'] += ["students_cnt", "visitors_cnt"]
        response['registrations_columns'] += ["students_registrations", "visitors_registrations"]

    # ============

    # Datatable filters definitions
    response['yadcf'] += [{
            'column_selector': "domain_subdomain:name",
            'text_data_delimiter': "<br>",
            'filter_default_label': "",
            'filter_match_mode': "contains",
            'filter_container_id': "domain_filter",
            'style_class': "form-control form-control-sm",
            'filter_reset_button_text': False,
        },
        {
            'column_selector': "training:name",
            'filter_default_label': "",
            'filter_match_mode': "exact",
            'filter_container_id': "training_filter",
            'style_class': "form-control form-control-sm",
            'filter_reset_button_text': False,
        }
    ]

    trainings = Training.objects.prefetch_related(
        'training_subdomains__training_domain',
        'structures',
        'highschool',
    ).filter(**trainings_filter).distinct()

    for training in trainings:
        structure = ""

        if training.highschool:
            establishment = _("High school") + f" {training.highschool.label} ({training.highschool.city})"
        else:
            establishment = "<br>".join(set(sorted([s.establishment.label for s in training.structures.all()])))
            structure = "<br>".join(sorted([s.label for s in training.structures.filter(active=True)]))

        base_persons_qs = ImmersionUser.objects\
            .prefetch_related('immersions__slot__course__training', 'high_school_student_record__highschool')\
            .filter(
                **students_filter,
                immersions__slot__course__training=training,
                immersions__cancellation_type__isnull=True
            )

        base_immersions_qs = Immersion.objects\
            .prefetch_related('slot__course__training', 'student__high_school_student_record__highschool')\
            .filter(
                **immersions_filter,
                slot__course__training=training,
                cancellation_type__isnull=True
            )

        # Get domains and add subdomains as a list under each, will join them right below in "domain_label"
        domain_labels = defaultdict(list)
        for subdomain in training.training_subdomains.all():
            domain_labels[subdomain.training_domain.label].append(f"- {subdomain.label}")

        row = {
            'establishment': establishment,
            'structure': structure,
            'training_label': training.label,
            'domain_label': "<br>".join([x for dom, subs in sorted(domain_labels.items()) for x in [dom] + subs]),
            # persons (pupils, students, visitors) registered to at least one immersion for this training
            'unique_persons': base_persons_qs.distinct().count(),
            # students registered to at least one immersion for this training
            'unique_visitors': base_persons_qs.filter(visitor_record__isnull=False).distinct().count(),
            # registrations on all slots (not cancelled)
            'all_registrations': base_immersions_qs.count(),
            # visitors registrations count
            'visitors_registrations': base_immersions_qs.filter(student__visitor_record__isnull=False).count(),
        }

        # Pre-bachelor levels :
        for level in pre_bachelor_levels:
            row[f"unique_students_lvl{level.id}"] = base_persons_qs.filter(
                high_school_student_record__level=level).distinct().count()

            row[f"registrations_lvl{level.id}"] = base_immersions_qs.filter(
                student__high_school_student_record__level=level).count()

        # Post bachelor levels : include pupils + students
        row["unique_students"] = base_persons_qs.filter(
            Q(high_school_student_record__level__in=post_bachelor_levels) |
            Q(student_record__level__in=[s.id for s in StudentLevel.objects.filter(active=True)]))\
            .distinct().count()

        row[f"students_registrations"] = base_immersions_qs.filter(
            Q(student__high_school_student_record__level__in=post_bachelor_levels) |
            Q(student__student_record__level__in=[s.id for s in StudentLevel.objects.filter(active=True)]))\
            .count()

        response['data'].append(row.copy())

    return JsonResponse(response, safe=False)


@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_registration_charts(request, level_value=0):
    """
    Data for amcharts 4
    Horizontal bars format
    """

    # TODO : Merge with highschool_charts ?

    if level_value == 0 or level_value not in [s.id for s in HighSchoolLevel.objects.all()]:
        level_value = 0 # force it
        student_levels = [
            l.label for l in HighSchoolLevel.objects.order_by('order')
        ]
    else:
        student_levels = [
            HighSchoolLevel.objects.get(pk=level_value).label
        ]

    request.session["current_level_filter"] = level_value

    # Each dataset represents a category
    datasets = [
        {
            'name': gettext("Attended to at least one immersion"),
        },
        {
            'name': gettext("Registrations to at least one immersion"),
        },
        {
            'name': gettext("Registrations count"),
        },
    ]

    # Horizontal bars : switched axis
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
        }],
        'y': [{
            "type": "CategoryAxis",
            "dataFields": {
                "category": "name",
            }
        }],
    }

    series = []

    for level in student_levels:
        series.append({
            "name": level,
            "type": "ColumnSeries",
            "stacked": True,

            "dataFields": {
                "valueX": level,
                "categoryY": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": level + "\n{valueX}",
                },
            }
        })

    qs = ImmersionUser.objects.all()

    if level_value == 0:
        levels =  [l for l in HighSchoolLevel.objects.order_by('order')]
    else:
        l = HighSchoolLevel.objects.get(pk=level_value)
        levels = [l]

    for level in levels:
        if not level.is_post_bachelor:
            users = qs.filter(high_school_student_record__level=level.pk)
        else: # post bachelor levels : highschool and higher education institutions levels
            users = qs.filter(Q(high_school_student_record__level__is_post_bachelor=True) |
                              Q(student_record__level__isnull=False))

        datasets[0][level.label] = users.filter(immersions__attendance_status=1).distinct().count() # attended to 1 immersion
        datasets[1][level.label] = users.filter(
            immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count()  # registered
        datasets[2][level.label] = users.count()  # platform

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_registration_charts_cats(request):
    """
    Data for amcharts 4
    Horizontal bars format, part 2
    parameters are in request.POST
    """

    immersions_filter = {}

    # Parse filters in POST request
    _highschools_ids = request.POST.getlist("highschools_ids[]")
    _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")

    try:
        level_value = int(request.POST.get("level", 0))
    except ValueError:
        level_value = 0

    if level_value == 0 or level_value not in [l.id for l in HighSchoolLevel.objects.all()]:
        level_value = 0 # force it if not in allowed values
        student_levels = []
        levels = []
        for l in HighSchoolLevel.objects.order_by('order'):
            student_levels.append(l.label)
            levels.append(l)
    else:
        student_levels = [
            HighSchoolLevel.objects.get(pk=level_value).label
        ]
        # dirty as there will be only one element
        levels = [HighSchoolLevel.objects.get(pk=level_value)]

    # Filter on highschools or higher education institutions
    if _highschools_ids:
        immersions_filter["student__high_school_student_record__highschool__id__in"] = _highschools_ids

    if _higher_institutions_ids:
        immersions_filter["student__student_record__uai_code__in"] = _higher_institutions_ids

    # We need data for 3 graphs
    # Axes are common, just make sure we always use 'name' as attribute name for category
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
        }],
        'y': [{
            "type": "CategoryAxis",
            "dataFields": {
                "category": "name",
            }
        }],
    }

    # Series (common)
    series = []
    for level in student_levels:
        series.append({
            "name": level,
            "type": "ColumnSeries",
            "stacked": True,

            "dataFields": {
                "valueX": level,
                "categoryY": "name",
            },
            "columns": {
                "template": {
                    "width": "30%",
                    "tooltipText": level + "\n{valueX}",
                },
            }
        })

    # Datasets definitions are also common : each category is an institution

    datasets = {
        'platform_regs': [],
        'one_immersion': [],
        'attended_one': [],
    }

    qs = ImmersionUser.objects.prefetch_related("high_school_student_record__highschool","student_record").all()

    # High schools
    for highschool in HighSchool.objects.filter(id__in=_highschools_ids):
        hs_qs = qs.filter(high_school_student_record__highschool=highschool)

        dataset_pr = { 'name': highschool.label }
        dataset_oi = { 'name': highschool.label }
        dataset_ao = { 'name': highschool.label }

        for level in levels:
            if not level.is_post_bachelor:
                users = hs_qs.filter(high_school_student_record__level=level)
            else:  # is_post_bachelor : highschool and higher education institutions levels
                users = hs_qs.filter(Q(high_school_student_record__level=level) |
                                     Q(student_record__level__in=StudentLevel.objects.all()))

            dataset_pr[level.label] = users.count()  # plaform
            dataset_oi[level.label] = users.filter(
                immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count()  # registered
            dataset_ao[level.label] = users.filter(
                immersions__attendance_status=1).distinct().count()  # attended to 1 immersion

        datasets['platform_regs'].append(dataset_pr.copy())
        datasets['one_immersion'].append(dataset_oi.copy())
        datasets['attended_one'].append(dataset_ao.copy())



    # Higher institutions
    for uai_code in _higher_institutions_ids:
        hii_qs = qs.filter(student_record__uai_code=uai_code)

        try:
            hei = HigherEducationInstitution.objects.get(pk=uai_code)
            label = hei.label
        except HigherEducationInstitution.DoesNotExist:
            label = "{} ({})".format(uai_code, gettext("no name match yet"))

        dataset_pr = {'name': label}
        dataset_oi = {'name': label}
        dataset_ao = {'name': label}

        for level in levels:
            if not level.is_post_bachelor:
                users = ImmersionUser.objects.none() # we need this to keep consistent data between institutions
            else:  # post bachelor levels :
                users = hii_qs.filter(student_record__level__in=StudentLevel.objects.all())

            dataset_pr[level.label] = users.count() # plaform
            dataset_oi[level.label] = users.filter(
                immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count() # registered
            dataset_ao[level.label] = users.filter(
                immersions__attendance_status=1).distinct().count() # attended to 1 immersion

        datasets['platform_regs'].append(dataset_pr.copy())
        datasets['one_immersion'].append(dataset_oi.copy())
        datasets['attended_one'].append(dataset_ao.copy())

    # =========

    response = {
        'platform_regs': {
            'axes': axes,
            'datasets': datasets['platform_regs'],
            'series': series,
        },
        'one_immersion': {
            'axes': axes,
            'datasets': datasets['one_immersion'],
            'series': series,
        },
        'attended_one': {
            'axes': axes,
            'datasets': datasets['attended_one'],
            'series': series,
        }
    }

    return JsonResponse(response, safe=False)

@is_ajax_request
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_slots_charts(request):
    """
    Data for amcharts 4
    Double pie chart format
    """
    datasets = []

    series = [
        {
            "type": "PieSeries",
            "dataFields": {
                "value": "slots_count",
                "category": "structure",
            },
        },
    ]

    for structure in Structure.objects.all():
        # Get all slots for this structure
        qs = Slot.objects.prefetch_related('course__structure', 'course__training')\
            .filter(course__structure=structure, published=True)

        slots_count = qs.count()

        if slots_count:
            data = {
                "structure": structure.label,
                "slots_count": slots_count,
                "subData": [],
            }

            for training in Training.objects.prefetch_related('courses__structure')\
                .filter(courses__structure=structure, active=True).distinct():
                subcount = qs.filter(course__training=training).count()

                if subcount:
                    sub_data = {
                        "name": training.label,
                        "slots_count": subcount,
                    }
                    data['subData'].append(sub_data.copy())

            datasets.append(data.copy())

    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_slots_data(request, csv_mode=False):
    """
    Data for datatables or csv extraction
    """

    if csv_mode:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="slots_statistics.csv"'
        header = [
            _('Structure'),
            _('Training'),
            _('Course'),
            _('Slots count'),
            _('Available seats'),
        ]
        writer = csv.writer(response)
        writer.writerow(header)
    else:
        response = {'msg': '', 'data': []}

    for course in Course.objects.prefetch_related('structure', 'training').filter(published=True)\
            .order_by("structure__label", "training__label", "label"):
        if csv_mode:
            writer.writerow([
                course.structure.label,
                course.training.label,
                course.label,
                course.published_slots_count(),
                course.free_seats(),
            ])
        else:
            course_data = {
                "structure": course.structure.label,
                "training": course.training.label,
                "course": course.label,
                "slots_count":course.published_slots_count(),
                "available_seats":course.free_seats(),
            }

            response['data'].append(course_data.copy())

    if csv_mode:
        return response
    else:
        return JsonResponse(response, safe=False)