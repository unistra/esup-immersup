import ast
import csv
import json
import logging

from collections import defaultdict
from functools import reduce
from django.db.models import Q, Count
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext, gettext_lazy as _

from immersionlyceens.decorators import groups_required, is_ajax_request, is_post_request

from immersionlyceens.apps.core.models import (
    Structure, Immersion, ImmersionUser, TrainingDomain, TrainingSubdomain, HigherEducationInstitution,
    HighSchool, Training, Slot, Course, HighSchoolLevel, PostBachelorLevel, StudentLevel, Establishment
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord

from .utils import parse_median

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
    """
    Return a json for datatables, with a list of high schools / structures to filter
    registrations with
    """

    response = {'msg': '', 'data': []}
    user = request.user
    filter_by_my_trainings = request.GET.get('filter_by_my_trainings') == "true"

    if user.is_master_establishment_manager():
        # get highschools and higher education institutions
        highschool_filters = {
            'student_records__isnull': False
        }

        # Keep only highschool with postbac immersions
        if filter_by_my_trainings:
            highschool_filters['postbac_immersion'] = True

        highschools = HighSchool.objects.filter(**highschool_filters).distinct()

        for highschool in highschools:
            institution_data = {
                'institution': highschool.label,
                'institution_id': highschool.id,
                'structure_id': '',
                'type': _('Highschool'),
                'type_code': 0,
                'city': f"{highschool.zip_code} - {highschool.city}",
                'department': highschool.department,
                'country': '',
            }

            response['data'].append(institution_data.copy())

        if filter_by_my_trainings:
            for establishment in Establishment.objects.filter(active=True):
                institution_data = {
                    'institution': establishment.label,
                    'institution_id': establishment.id,
                    'structure_id': '',
                    'type': _('Higher education institution'),
                    'type_code': 1,
                    'city': establishment.city,
                    'department': establishment.department,
                    'country': '',
                }

                response['data'].append(institution_data.copy())
        else:
            higher_institutions_uai = {
                obj.uai_code:obj for obj in HigherEducationInstitution.objects.all()
            }

            uai_codes = StudentRecord.objects.all().values_list('uai_code', flat=True).distinct()

            for uai_code in uai_codes:
                institution = higher_institutions_uai.get(uai_code, None)

                """
                if institution and institution.establishment is not None:
                    continue
                """

                institution_data = {
                    'institution': '',
                    'institution_id': uai_code,
                    'structure_id': '',
                    'type': _('Higher education institution'),
                    'type_code': 1,
                    'city': '',
                    'department': '',
                    'country': '',
                }
                # Try to find institution by name or UAI code (a not so good design)
                if institution:
                    institution_data['institution'] = institution.label
                    institution_data['city'] = f"{institution.zip_code} - {institution.city}",
                    institution_data['department'] = institution.department,
                    institution_data['country'] = institution.country,
                else:
                    institution_data['institution'] = uai_code

                response['data'].append(institution_data.copy())

    if (user.is_master_establishment_manager() or user.is_establishment_manager()) and filter_by_my_trainings:
        for structure in user.get_authorized_structures():
            establishment = structure.establishment

            institution_data = {
                'institution': establishment.label,
                'structure': structure.label,
                'structure_id': structure.id,
                'institution_id': '',
                'type': _('Higher education institution'),
                'type_code': 2,
                'city': f"{establishment.zip_code} - {establishment.city}",
                'department': establishment.department,
                'country': '',
            }

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

    filter_by_my_trainings :
      - if True, consider only the highschool trainings
      - if False, filter by the highschool students

    """
    user = request.user
    show_empty_trainings = request.GET.get("empty_trainings", False) == "true"
    structure_id = request.GET.get("structure_id")
    highschool_id = request.GET.get("highschool_id")
    filter_by_my_trainings = request.GET.get("filter_by_my_trainings", False) == "true"

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

        # Filter by the selected high school students
        if not filter_by_my_trainings:
            trainings_filter[
                'courses__slots__immersions__student__high_school_student_record__highschool__id'] = highschool_id

    if filter_by_my_trainings:
        if user.is_high_school_manager():
            trainings_filter['highschool__id'] = highschool_id
        elif user.is_establishment_manager():
            trainings_filter['structures__in'] = user.get_authorized_structures()

    # Do not include trainings with no registration/students
    if not show_empty_trainings:
        trainings_filter['courses__slots__immersions__isnull'] = False
        trainings_filter['courses__slots__immersions__cancellation_type__isnull'] = True

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

    if user.is_master_establishment_manager() or user.is_operator() or (user.is_high_school_manager() and not filter_by_my_trainings):
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
    """
    if user.is_high_school_manager() and user.highschool:
        trainings_filter['highschool'] = user.highschool
    """
    if any(structure_col_conditions):
        # Already done when filter_by_my_trainings is True, is it necessary again here ?
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
    if filter_by_my_trainings or not request.user.is_high_school_manager():
        pre_bachelor_levels = HighSchoolLevel.objects.filter(active=True, is_post_bachelor=False)
    else:
        pre_bachelor_levels = HighSchoolLevel.objects.filter(active=True)

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

    # Add some columns if filtering by trainings and not by high school students
    if filter_by_my_trainings or not request.user.is_high_school_manager():
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


@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC", "REF-LYC", "REF-STR")
def get_registration_charts(request):
    """
    Data for amcharts 4
    Horizontal bars format
    Courses slots only
    """
    user = request.user
    level_value = request.GET.get("level", 0) # default : all
    highschool_id = request.GET.get("highschool_id", 'all')
    structure_id = request.GET.get("structure_id")
    structure = None
    filter_by_my_trainings = request.GET.get("filter_by_my_trainings", False) == "true"
    high_school_user_filters = {}
    level_filter = {}
    immersions_filter = {}
    allowed_structures = user.get_authorized_structures()

    # Force filter_by_my_trainings to True for these 2 groups
    if user.is_structure_manager() or user.is_establishment_manager():
        filter_by_my_trainings = True

    try:
        structure_id = int(structure_id)
        structure = Structure.objects.get(pk=structure_id)
    except (ValueError, TypeError, Structure.DoesNotExist):
        structure_id = None

    # Highschool id override for high school managers
    if user.is_high_school_manager() and user.highschool:
        highschool_id = user.highschool.id

    if highschool_id == "all_highschools" and filter_by_my_trainings:
        immersions_filter['immersions__slot__course__highschool__isnull'] = False
    else:
        try:
            int(highschool_id)
            # Filter by the selected high school students

            if not filter_by_my_trainings:
                high_school_user_filters['high_school_student_record__validation'] = 2
                high_school_user_filters['high_school_student_record__highschool__id'] = highschool_id
                immersions_filter['immersions__student__high_school_student_record__highschool__id'] = highschool_id
            else:
                immersions_filter['immersions__slot__course__highschool__id'] = highschool_id
        except (TypeError, ValueError):
            pass

    if filter_by_my_trainings:
        if user.is_high_school_manager():
            immersions_filter['immersions__slot__course__highschool__id'] = highschool_id
        elif user.is_establishment_manager():
            immersions_filter['immersions__slot__course__structure__in'] = allowed_structures
        elif user.is_structure_manager() and structure and structure in user.get_authorized_structures():
            immersions_filter['immersions__slot__course__structure__id'] = structure_id

    if level_value != "visitors":
        try:
            level_value = int(level_value)
        except ValueError:
            level_value = 0

        if level_value == 0 or level_value not in [s.id for s in HighSchoolLevel.objects.filter(active=True)]:
            level_value = 0 # force it
            student_levels = [l.label for l in HighSchoolLevel.objects.filter(active=True).order_by('order')]

            if not user.is_high_school_manager() or filter_by_my_trainings:
                student_levels.append(_("Visitors"),)
        else:
            student_levels = [
                HighSchoolLevel.objects.get(pk=level_value).label
            ]
    else:
        # This is not very clean : we consider the "Visitors" class as a plain student level
        student_levels = [_("Visitors")]

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

    user_queryset = ImmersionUser.objects \
        .prefetch_related(
            'high_school_student_record__level',
            'student_record__level',
            'immersions__cancellation_type',
            'immersions__slot__course',
            'visitor_record')\
        .all()

    if level_value == 0:
        levels = [l for l in HighSchoolLevel.objects.filter(active=True).order_by('order')]

        if not user.is_high_school_manager() or filter_by_my_trainings:
            levels.append('visitors')

    elif level_value == 'visitors':
        levels =  ['visitors']
    else:
        l = HighSchoolLevel.objects.get(pk=level_value)
        level_filter = {'level': level_value}
        levels = [l]

    for level in levels:
        if level == 'visitors':
            level_label = gettext("Visitors")
            users = user_queryset.filter(visitor_record__validation=2)
        elif not level.is_post_bachelor:
            level_label = level.label
            users = user_queryset.filter(**high_school_user_filters, high_school_student_record__level=level.pk)
        else: # post bachelor levels : highschool and higher education institutions levels
            level_label = level.label
            users = user_queryset.filter(
                Q(high_school_student_record__level__is_post_bachelor=True, **high_school_user_filters) |
                Q(student_record__level__isnull=False)
            )

        # Attended to 1 at least immersion
        datasets[0][level_label] = users.filter(
            immersions__attendance_status=1,
            immersions__slot__course__isnull=False,
            **immersions_filter)\
            .distinct().count()

        # Registered to one immersion
        datasets[1][level_label] = users.filter(
            immersions__isnull=False,
            immersions__cancellation_type__isnull=True,
            immersions__slot__course__isnull=False,
            **immersions_filter)\
            .distinct().count()

        # platform : current highschool filter only
        datasets[2][level_label] = users.filter(**high_school_user_filters).count()

    # Median calculation for a specific high school
    if highschool_id != 'all' and not filter_by_my_trainings:
        # Attended to at least 1 immersion median
        pupils_counts = [
            x['cnt'] for x in HighSchoolStudentRecord.objects
                .prefetch_related('student__immersions__slot__course')
                .values('highschool')
                .filter(
                validation=2,
                student__immersions__attendance_status=1,
                student__immersions__slot__course__isnull=False
            )
                .annotate(cnt=Count('highschool', distinct=True))
        ]

        median = parse_median(pupils_counts)
        if median is not None:
            datasets[0]['name'] += f" (m = {median})"

        # =======================================================
        # Registered to at least 1 immersion median
        pupils_counts = [
            x['cnt'] for x in HighSchoolStudentRecord.objects
                .prefetch_related('student__immersions__slot__course')
                .values('highschool')
                .filter(
                    validation=2,
                    student__immersions__isnull=False,
                    student__immersions__cancellation_type__isnull=True,
                    student__immersions__slot__course__isnull=False
                )
                .annotate(cnt=Count('highschool', distinct=True))
        ]

        median = parse_median(pupils_counts)
        if median:
            datasets[1]['name'] += f" (m = {median})"

        # =======================================================
        # All registrations median
        pupils_counts = [
            x['cnt'] for x in HighSchoolStudentRecord.objects.values('highschool')
                .filter(**level_filter, validation=2)
                .annotate(cnt=Count('highschool', distinct=True))
        ]

        median = parse_median(pupils_counts)
        if median is not None:
            datasets[2]['name'] += f" (m = {median})"


    # Median calculation for structure managers
    elif structure and filter_by_my_trainings:
        # =======================================================
        # Attended to at least 1 immersion median
        # =======================================================
        establishment_structures = Structure.objects.filter(establishment=structure.establishment).distinct()

        persons_counts = [
            x['cnt'] for x in Slot.objects
                .prefetch_related('course__structure', 'immersions')
                .filter(
                    course__structure__in=establishment_structures,
                    immersions__attendance_status=1,
                )
                .values('course__structure')
                .annotate(cnt=Count('immersions__student', distinct=True))
        ]

        median = parse_median(persons_counts)
        if median is not None:
            datasets[0]['name'] += f" (m = {median})"

        # =======================================================
        # Registered to at least 1 immersion median
        # =======================================================
        persons_counts = [
            x['cnt'] for x in Slot.objects
                .prefetch_related('course__structure', 'immersions')
                .filter(
                    course__structure__in=establishment_structures,
                    immersions__cancellation_type__isnull=True,
                )
                .values('course__structure')
                .annotate(cnt=Count('immersions__student', distinct=True))
        ]

        median = parse_median(persons_counts)
        if median is not None:
            datasets[1]['name'] += f" (m = {median})"

        # =======================================================
        # No global registrations median for structure managers
        # =======================================================

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series
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
    filter_by_my_trainings = request.POST.get("filter_by_my_trainings", False) == "true"

    # Parse filters in POST request
    _highschools_ids = request.POST.getlist("highschools_ids[]")
    _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")
    _structures_ids = request.POST.getlist("structure_ids[]")
    level_value = request.POST.get("level", 0)

    if level_value != 'visitors':
        try:
            level_value = int(request.POST.get("level", 0))
        except ValueError:
            level_value = 0

    if level_value == 0 or level_value not in [l.id for l in HighSchoolLevel.objects.all()] + ['visitors']:
        level_value = 0 # force it if not in allowed values
        student_levels = []
        levels = []
        for l in HighSchoolLevel.objects.order_by('order'):
            student_levels.append(l.label)
            levels.append(l)

        student_levels.append(_('Visitors'))
        levels.append('visitors')
    else:
        if level_value == 'visitors':
            student_levels = [_('Visitors')]
            levels = ['visitors']
        else:
            student_levels = [
                HighSchoolLevel.objects.get(pk=level_value).label
            ]
            levels = [HighSchoolLevel.objects.get(pk=level_value)]

    # Filter on highschools, higher education institutions or structures
    if not filter_by_my_trainings:
        if _highschools_ids:
            immersions_filter["student__high_school_student_record__highschool__id__in"] = _highschools_ids

        if _higher_institutions_ids:
            immersions_filter["student__student_record__uai_code__in"] = _higher_institutions_ids
    else:
        if _highschools_ids:
            immersions_filter["slot__course__highschool__in"] = _highschools_ids
        if _structures_ids:
            immersions_filter["slot__course__structure__in"] = _structures_ids
        if _higher_institutions_ids:
            structures = Structure.objects.filter(establishment__in=_higher_institutions_ids)
            immersions_filter["slot__course__structure__in"] = structures

    # We need data for 2 or 3 graphs (3 if filter_by_my_trainings is False)
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
        'one_immersion': [],
        'attended_one': [],
    }

    if not filter_by_my_trainings:
        datasets["platform_regs"] = []

    qs = ImmersionUser.objects.prefetch_related(
        "high_school_student_record__highschool", "student_record", "visitor_record").all()

    immersions_queryset = Immersion.objects.prefetch_related(
        'student__high_school_record__level', 'student__student_record__level', 'student__visitor_record',
        'slot__course__structure'
    )

    # High schools
    for highschool in HighSchool.objects.filter(id__in=_highschools_ids):
        hs_qs = qs.filter(
            high_school_student_record__highschool=highschool,
            high_school_student_record__validation=2
        )

        if not filter_by_my_trainings:
            dataset_platform_regs = { 'name': highschool.label }

        dataset_one_immersion = { 'name': highschool.label }
        dataset_attended_one = { 'name': highschool.label }

        for level in levels:
            if level == 'visitors':

                # When filtering on highschool students, do not include visitors level
                if not filter_by_my_trainings:
                    continue

                level_label = gettext("Visitors")
                users = qs.filter(visitor_record__isnull=False, visitor_record__validation=2)
            elif not level.is_post_bachelor:
                level_label = level.label
                users = hs_qs.filter(high_school_student_record__level=level)
            else: # is_post_bachelor : highschool and higher education institutions levels
                level_label = level.label

                if not filter_by_my_trainings:
                    users = hs_qs.filter(
                        high_school_student_record__level=level,
                        high_school_student_record__validation=2
                    )
                else:
                    users = qs.filter(
                        Q(high_school_student_record__highschool=highschool,
                          high_school_student_record__level=level,
                          high_school_student_record__validation=2) |
                        Q(student_record__level__in=StudentLevel.objects.all()),
                    )

            if not filter_by_my_trainings:
                dataset_platform_regs[level_label] = users.count()  # plaform

            dataset_one_immersion[level_label] = users.filter(
                immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count()  # registered
            dataset_attended_one[level_label] = users.filter(
                immersions__attendance_status=1).distinct().count()  # attended to 1 immersion

        if not filter_by_my_trainings:
            datasets['platform_regs'].append(dataset_platform_regs.copy())

        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # Higher institutions
    if filter_by_my_trainings:
        for establishment_id in _higher_institutions_ids:
            structures = Structure.objects.filter(establishment__id=establishment_id)

            estab_qs = qs.filter(immersions__slot__course__structure__in=structures)
            estab_immersions = immersions_queryset.filter(slot__course__structure__in=structures)

            try:
                establishment = Establishment.objects.get(pk=establishment_id)
                label = establishment.label
            except Establishment.DoesNotExist:
                label = gettext("Establishment not found")

            if not filter_by_my_trainings:
                dataset_platform_regs = {'name': label}

            dataset_one_immersion = {'name': label}
            dataset_attended_one = {'name': label}

            for level in levels:
                if level == 'visitors':
                    level_label = gettext("Visitors")
                    users = estab_qs.filter(visitor_record__isnull=False, visitor_record__validation=2)
                    immersions = estab_immersions.filter(
                        student__visitor_record__isnull=False,
                        student__visitor_record__validation=2
                    )
                elif not level.is_post_bachelor:
                    level_label = level.label
                    users = estab_qs.filter(
                        high_school_student_record__level=level,
                        high_school_student_record__validation=2
                    )
                    immersions = estab_immersions.filter(
                        student__high_school_student_record__level=level,
                        student__high_school_student_record__validation=2
                    )
                else:  # post bachelor levels : include students
                    level_label = level.label
                    users = estab_qs.filter(
                        Q(student_record__isnull=False)
                        | Q(high_school_student_record__validation=2,
                            high_school_student_record__level__in=HighSchoolLevel.objects.filter(is_post_bachelor=True))
                    )
                    immersions = estab_immersions.filter(
                        Q(student__student_record__isnull=False)
                        | Q(student__high_school_student_record__validation=2,
                            student__high_school_student_record__level__in=HighSchoolLevel.objects.filter(
                                is_post_bachelor=True))
                    )

                # registered to at least 1 immersion
                dataset_one_immersion[level_label] = users.filter(
                    immersions__isnull=False,
                    immersions__cancellation_type__isnull=True).distinct().count()

                # attended to 1 immersion
                dataset_attended_one[level_label] = immersions.filter(
                    attendance_status=1).values('student').distinct().count()

            datasets['one_immersion'].append(dataset_one_immersion.copy())
            datasets['attended_one'].append(dataset_attended_one.copy())

    else:
        for uai_code in _higher_institutions_ids:
            hii_qs = qs.filter(student_record__uai_code=uai_code)

            try:
                hei = HigherEducationInstitution.objects.get(pk=uai_code)
                label = hei.label
            except HigherEducationInstitution.DoesNotExist:
                label = "{} ({})".format(uai_code, gettext("no name match yet"))

            if not filter_by_my_trainings:
                dataset_platform_regs = {'name': label}

            dataset_one_immersion = {'name': label}
            dataset_attended_one = {'name': label}

            for level in levels:
                if level == 'visitors':
                    level_label = gettext("Visitors")
                    users = hii_qs.filter(visitor_record__isnull=False, visitor_record__validation=2)
                elif not level.is_post_bachelor:
                    level_label = level.label
                    # No high school levels for these students, but we need this to keep consistent data between institutions
                    users = hii_qs.none()
                else:  # post bachelor levels :
                    level_label = level.label
                    users = hii_qs.filter(student_record__level__in=StudentLevel.objects.all())

                if not filter_by_my_trainings:
                    dataset_platform_regs[level_label] = users.count() # plaform

                dataset_one_immersion[level_label] = users.filter(
                    immersions__isnull=False, immersions__cancellation_type__isnull=True).distinct().count() # registered
                dataset_attended_one[level_label] = users.filter(
                    immersions__attendance_status=1).distinct().count() # attended to 1 immersion

            if not filter_by_my_trainings:
                datasets['platform_regs'].append(dataset_platform_regs.copy())

            datasets['one_immersion'].append(dataset_one_immersion.copy())
            datasets['attended_one'].append(dataset_attended_one.copy())

    # Structures when filtering on my trainings
    for structure_id in _structures_ids:
        strs_qs = qs.filter(
            immersions__slot__course__structure__id=structure_id
        )

        strs_immersions = immersions_queryset.filter(slot__course__structure__id=structure_id)

        try:
            structure = Structure.objects.get(pk=structure_id)
            label = f"{structure.establishment.short_label} - {structure.label}"
        except Structure.DoesNotExist:
            label = gettext("Structure not found")

        if not filter_by_my_trainings:
            dataset_platform_regs = {'name': label}

        dataset_one_immersion = {'name': label}
        dataset_attended_one = {'name': label}

        for level in levels:
            if level == 'visitors':
                level_label = gettext("Visitors")
                users = strs_qs.filter(visitor_record__isnull=False, visitor_record__validation=2)
                immersions = strs_immersions.filter(
                    student__visitor_record__isnull=False,
                    student__visitor_record__validation=2
                )
            elif not level.is_post_bachelor:
                level_label = level.label
                users = strs_qs.filter(
                    high_school_student_record__level=level,
                    high_school_student_record__validation=2
                )
                immersions = strs_immersions.filter(
                    student__high_school_student_record__level=level,
                    student__high_school_student_record__validation=2
                )
            else:  # post bachelor levels : include students
                level_label = level.label
                users = strs_qs.filter(
                    Q(student_record__isnull=False)
                    | Q(high_school_student_record__validation=2,
                        high_school_student_record__level__in=HighSchoolLevel.objects.filter(is_post_bachelor=True))
                )
                immersions = strs_immersions.filter(
                    Q(student__student_record__isnull=False)
                    | Q(student__high_school_student_record__validation=2,
                        student__high_school_student_record__level__in=HighSchoolLevel.objects.filter(is_post_bachelor=True))
                )

            if not filter_by_my_trainings:
                dataset_platform_regs[level_label] = users.count()  # plaform

            # registered to at least 1 immersion
            dataset_one_immersion[level_label] = users.filter(
                immersions__isnull=False,
                immersions__cancellation_type__isnull=True).distinct().count()

            # attended to 1 immersion
            dataset_attended_one[level_label] = immersions.filter(
                attendance_status=1).values('student').distinct().count()

        if not filter_by_my_trainings:
            datasets['platform_regs'].append(dataset_platform_regs.copy())

        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # =========

    response = {
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

    if not filter_by_my_trainings:
        response['platform_regs'] = {
            'axes': axes,
            'datasets': datasets['platform_regs'],
            'series': series,
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