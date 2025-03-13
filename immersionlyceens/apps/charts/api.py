import csv
import logging
import math

from collections import defaultdict
from functools import reduce
from django.db.models import Q, F, Count
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


@is_post_request
@groups_required('REF-ETAB', "REF-ETAB-MAITRE", "REF-TEC", "REF-LYC")
def global_domains_charts_by_population(request):
    """
    Data for amcharts 4
    Pie chart format
    Filter by pupils from a high school or an establishment
    all parameters are in request.POST
    """
    user = request.user
    immersions_filter = {}
    _highschools_ids = []
    _higher_institutions_ids = []
    level_value = request.POST.get("level", 0)
    level = None

    # Parse filters in POST request
    if user.is_high_school_manager() and user.highschool:
        _highschools_ids = [user.highschool.id]
    else:
        _highschools_ids = request.POST.getlist("highschools_ids[]")
        _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")

    if level_value not in [0, "0", "visitors"]:
        try:
            level_value = int(level_value)
            level = HighSchoolLevel.objects.get(pk=level_value)
        except (TypeError, ValueError, HighSchoolLevel.DoesNotExist):
            level_value = 0

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

    immersions = Immersion.objects.prefetch_related(
        'slot__course__training__training_subdomains__training_domain',
        'student__high_school_student_record__highschool'
    ).filter(cancellation_type__isnull=True)

    # Level filter
    if level_value != 0:
        if level_value == 'visitors':
            immersions = immersions.filter(student__visitor_record__validation=2)
        elif level:
            if not level.is_post_bachelor:
                immersions = immersions.filter(
                    student__high_school_student_record__level=level,
                    student__high_school_student_record__validation=2
                )
            else:
                immersions = immersions.filter(
                    Q(student__high_school_student_record__level=level,
                      student__high_school_student_record__validation=2)
                    | Q(student__student_record__level__in=StudentLevel.objects.all())
                )

    # Filter on highschools or higher education institutions
    if _highschools_ids:
        immersions_filter["student__high_school_student_record__highschool__id__in"] = _highschools_ids

    if _higher_institutions_ids:
        immersions_filter["student__student_record__uai_code__in"] = _higher_institutions_ids

    # Apply high school or establishment selection filter, with Q
    if immersions_filter:
        immersions = immersions.filter(
            reduce(lambda x, y: x | y, [Q(**{'%s' % k : v}) for k, v in immersions_filter.items()])
        )

    # Get domains and subdomains label + subdomains registrations count
    domains_data = immersions\
        .annotate(
            domain_label=F('slot__course__training__training_subdomains__training_domain__label'),
            domain_id=F('slot__course__training__training_subdomains__training_domain__id'))\
        .values(
            'domain_label',
            'domain_id')\
        .annotate(cnt=Count('domain_id'))\
        .order_by('domain_label')

    for d_data in domains_data:
        if d_data['cnt']:
            data = {
                "domain": d_data['domain_label'],
                "count": d_data['cnt'],
                "subData": [],
            }

            subdomains_data = immersions \
                .filter(slot__course__training__training_subdomains__training_domain__id=d_data['domain_id'])\
                .annotate(
                    subdomain_label=F('slot__course__training__training_subdomains__label'),
                    subdomain_id=F('slot__course__training__training_subdomains__training_domain__id')) \
                .values(
                    'subdomain_label',
                    'subdomain_id')\
                .annotate(cnt=Count('slot__course__training__training_subdomains'))\
                .order_by('subdomain_label')

            for sub_d_data in subdomains_data:
                sub_data = {
                    "name": sub_d_data['subdomain_label'],
                    "count": sub_d_data['cnt'],
                }
                data['subData'].append(sub_data.copy())

            datasets.append(data.copy())


    response = {
        'datasets': datasets,
        'series': series,
    }

    return JsonResponse(response, safe=False)


@is_post_request
@groups_required('REF-ETAB', "REF-ETAB-MAITRE", "REF-TEC", "REF-LYC")
def global_domains_charts_by_trainings(request):
    """
    Data for amcharts 4
    Pie chart format
    Filter by trainings of a high school or an establishment
    all parameters are in request.POST
    """
    user = request.user
    immersions_filter = {}
    _highschools_ids = []
    _structures_ids = []
    _higher_institutions_ids = []
    level_value = request.POST.get("level", 0)

    level = None

    # Parse filters in POST request
    if user.is_high_school_manager() and user.highschool:
        _highschools_ids = [user.highschool.id]
    elif user.is_establishment_manager():
        structures = user.get_authorized_structures()
        _structures_ids = [s.id for s in structures]
    else:
        _highschools_ids = request.POST.getlist("highschools_ids[]")
        _structures_ids = request.POST.getlist("structures_ids[]")
        _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")

    if level_value not in [0, "0", "visitors"]:
        try:
            level_value = int(level_value)
            level = HighSchoolLevel.objects.get(pk=level_value)
        except (TypeError, ValueError, HighSchoolLevel.DoesNotExist):
            level_value = 0

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

    immersions = Immersion.objects.prefetch_related(
        'slot__course__training__training_subdomains__training_domain',
        'student__high_school_student_record__highschool'
    ).filter(cancellation_type__isnull=True)

    # Level filter
    if level_value != 0:
        if level_value == 'visitors':
            immersions = immersions.filter(student__visitor_record__validation=2)
        elif level:
            if not level.is_post_bachelor:
                immersions = immersions.filter(student__high_school_student_record__level=level)
            else:
                immersions = immersions.filter(
                    Q(student__high_school_student_record__level=level)
                    | Q(student__student_record__level__in=StudentLevel.objects.all())
                )

    # Filter on highschools or higher education institutions trainings/domains
    if _highschools_ids:
        immersions_filter["slot__course__highschool__in"] = _highschools_ids

    if _structures_ids:
        immersions_filter["slot__course__structure__in"] = _structures_ids

    if _higher_institutions_ids:
        structures = Structure.objects.filter(establishment__id__in=_higher_institutions_ids).distinct()
        immersions_filter["slot__course__structure__in"] = structures

    # Apply high school or establishment selection filter
    if immersions_filter:
        immersions = immersions.filter(
            reduce(lambda x, y: x | y, [Q(**{'%s' % k : v}) for k, v in immersions_filter.items()])
        )


    # Get domains and subdomains label + subdomains registrations count
    domains_data = immersions \
        .annotate(
            domain_label=F('slot__course__training__training_subdomains__training_domain__label'),
            domain_id=F('slot__course__training__training_subdomains__training_domain__id')) \
        .values(
            'domain_label',
            'domain_id') \
        .annotate(cnt=Count('domain_id')) \
        .order_by('domain_label')

    for d_data in domains_data:
        if d_data['cnt']:
            data = {
                "domain": d_data['domain_label'],
                "count": d_data['cnt'],
                "subData": [],
            }

            subdomains_data = immersions \
                .filter(slot__course__training__training_subdomains__training_domain__id=d_data['domain_id']) \
                .annotate(
                    subdomain_label=F('slot__course__training__training_subdomains__label'),
                    subdomain_id=F('slot__course__training__training_subdomains__training_domain__id')) \
                .values(
                    'subdomain_label',
                    'subdomain_id') \
                .annotate(cnt=Count('slot__course__training__training_subdomains'))

            for sub_d_data in subdomains_data:
                sub_data = {
                    "name": sub_d_data['subdomain_label'],
                    "count": sub_d_data['cnt'],
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
    include_structures = request.GET.get('include_structures', False) == "true"

    if user.is_master_establishment_manager() or user.is_operator():
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

    allowed_groups = [
        user.is_master_establishment_manager(),
        user.is_establishment_manager(),
        user.is_operator()
    ]

    if any(allowed_groups) and filter_by_my_trainings and include_structures:
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
def get_registration_charts_by_population(request):
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
    high_school_user_filters = {}
    level_filter = {}
    immersions_filter = {}
    allowed_structures = user.get_authorized_structures()

    try:
        structure_id = int(structure_id)
        structure = Structure.objects.get(pk=structure_id)
    except (ValueError, TypeError, Structure.DoesNotExist):
        structure_id = None

    # Highschool id override for high school managers
    if user.is_high_school_manager() and user.highschool:
        highschool_id = user.highschool.id

    try:
        int(highschool_id)
        # Filter by the selected high school students
        high_school_user_filters['high_school_student_record__highschool__id'] = highschool_id
        immersions_filter['student__high_school_student_record__highschool__id'] = highschool_id
    except (TypeError, ValueError):
        pass

    if level_value != "visitors":
        try:
            level_value = int(level_value)
        except ValueError:
            level_value = 0

        if level_value == 0 or level_value not in [s.id for s in HighSchoolLevel.objects.filter(active=True)]:
            level_value = 0 # force it
            student_levels = [l.label for l in HighSchoolLevel.objects.filter(active=True).order_by('order')]

            if not user.is_high_school_manager():
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
    datasets = [{
        'name': gettext("Attended to at least one immersion"),
        'none': 0
    }, {
        'name': gettext("Registrations to at least one immersion"),
        'none': 0
    }, {
        'name': gettext("Registrations count"),
        'none': 0
    }]

    # Horizontal bars : switched axis
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
            "calculateTotals": True,
            "extraMax": 0.1
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

    immersions_queryset = Immersion.objects \
        .prefetch_related(
            'student__high_school_student_record__level',
            'student__student_record__level',
            'student__visitor_record',
            'slot__course') \
        .all()

    if level_value == 0:
        levels = [l for l in HighSchoolLevel.objects.filter(active=True).order_by('order')]

        if not user.is_high_school_manager():
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
            immersions = immersions_queryset.filter(student__visitor_record__validation=2)
        elif not level.is_post_bachelor:
            level_label = level.label
            users = user_queryset.filter(
                high_school_student_record__level=level.pk,
                high_school_student_record__validation=2
            )
            immersions = immersions_queryset.filter(
                student__high_school_student_record__level=level.pk,
                student__high_school_student_record__validation=2
            )
        else: # post bachelor levels : highschool and higher education institutions levels
            level_label = level.label
            users = user_queryset.filter(
                Q(high_school_student_record__level__is_post_bachelor=True,
                  high_school_student_record__validation=2) |
                Q(student_record__level__isnull=False)
            )
            immersions = immersions_queryset.filter(
                Q(student__high_school_student_record__level__is_post_bachelor=True,
                  student__high_school_student_record__validation=2) |
                Q(student__student_record__level__isnull=False)
            )

        # Attended to 1 at least immersion
        datasets[0][level_label] = immersions.filter(
            attendance_status=1,
            slot__course__isnull=False,
            **immersions_filter)\
            .values('student')\
            .distinct()\
            .count()

        # Registered to one immersion
        datasets[1][level_label] = immersions.filter(
            cancellation_type__isnull=True,
            slot__course__isnull=False,
            **immersions_filter)\
            .values('student')\
            .distinct()\
            .count()

        # platform : current highschool filter only
        datasets[2][level_label] = users.filter(**high_school_user_filters).count()

    # Median calculation for a specific high school
    if highschool_id != 'all':
        one_immersion_attendance_pupils_counts = []
        one_immersion_registration_pupils_counts = []
        all_registrations_pupils_counts = []

        for hs in HighSchool.agreed.all():
            qs = Immersion.objects.filter(
                slot__course__isnull=False,
                student__high_school_student_record__highschool=hs,
                student__high_school_student_record__validation=2
            )

            one_immersion_attendance_pupils_counts.append(
                qs.filter(attendance_status=1).values('student').distinct().count()
            )

            one_immersion_registration_pupils_counts.append(
                qs.values('student').distinct().count()
            )

            all_registrations_pupils_counts.append(
                HighSchoolStudentRecord.objects.filter(highschool=hs, validation=2).count()
            )

        median = parse_median(one_immersion_attendance_pupils_counts)
        if median is not None:
            datasets[0]['name'] += f" [bold](m = {median})[/bold]"

        median = parse_median(one_immersion_registration_pupils_counts)
        if median is not None:
            datasets[1]['name'] += f" [bold](m = {median})[/bold]"

        median = parse_median(all_registrations_pupils_counts)
        if median is not None:
            datasets[2]['name'] += f" [bold](m = {median})[/bold]"

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series
    }

    return JsonResponse(response, safe=False)


@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC", "REF-LYC", "REF-STR")
def get_registration_charts_by_trainings(request):
    """
    Data for amcharts 4
    Horizontal bars format
    Courses slots only

    Registration charts by trainings offered by establishments and high schools
    Optional filters : establishments, structures and / or high schools with postbac immersions
    """
    user = request.user
    level_value = request.GET.get("level", 0) # default : all
    highschool_id = request.GET.get("highschool_id", '')
    structure_id = request.GET.get("structure_id")
    structure = None
    immersions_filter = {}
    allowed_structures = user.get_authorized_structures()

    try:
        structure_id = int(structure_id)
        structure = Structure.objects.get(pk=structure_id)
    except (ValueError, TypeError, Structure.DoesNotExist):
        structure_id = None

    # Highschool id override for high school managers
    if user.is_high_school_manager() and user.highschool:
        highschool_id = user.highschool.id

    if highschool_id == "all":
        immersions_filter['slot__course__highschool__isnull'] = False
    else:
        try:
            int(highschool_id)
            immersions_filter['slot__course__highschool__id'] = highschool_id
        except (TypeError, ValueError):
            pass

    if user.is_high_school_manager():
        immersions_filter['slot__course__highschool__id'] = highschool_id
    elif user.is_establishment_manager():
        immersions_filter['slot__course__structure__in'] = allowed_structures
    elif user.is_structure_manager() and structure and structure in allowed_structures:
        immersions_filter['slot__course__structure__id'] = structure_id

    if level_value != "visitors":
        try:
            level_value = int(level_value)
        except ValueError:
            level_value = 0

        if level_value == 0 or level_value not in [s.id for s in HighSchoolLevel.objects.filter(active=True)]:
            level_value = 0 # force it
            student_levels = [
                l.label for l in HighSchoolLevel.objects.filter(active=True).order_by('order')
            ] + [_("Visitors")]
        else:
            student_levels = [
                HighSchoolLevel.objects.get(pk=level_value).label
            ]
    else:
        # This is not very clean : we consider the "Visitors" class as a plain student level
        student_levels = [_("Visitors")]

    request.session["current_level_filter"] = level_value

    # Each dataset represents a category
    datasets = [{
        'name': gettext("Attended to at least one immersion"),
        'none': 0
    }, {
        'name': gettext("Registrations to at least one immersion"),
        'none': 0
    }, {
        'name': gettext("Registrations count"),
        'none': 0
    }]

    # Horizontal bars : switched axis
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
            "calculateTotals": True,
            "extraMax": 0.1
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

    immersions_queryset = Immersion.objects \
        .prefetch_related(
            'student__high_school_student_record__level',
            'student__student_record__level',
            'student__visitor_record',
            'slot__course') \
        .all()

    if level_value == 0:
        levels = [
            l for l in HighSchoolLevel.objects.filter(active=True).order_by('order')
        ] + ['visitors']
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
            immersions = immersions_queryset.filter(student__visitor_record__validation=2)
        elif not level.is_post_bachelor:
            level_label = level.label
            users = user_queryset.filter(
                high_school_student_record__validation=2,
                high_school_student_record__level=level.pk
            )
            immersions = immersions_queryset.filter(
                student__high_school_student_record__level=level.pk,
                student__high_school_student_record__validation=2
            )
        else: # post bachelor levels : highschool and higher education institutions levels
            level_label = level.label
            users = user_queryset.filter(
                Q(high_school_student_record__level__is_post_bachelor=True,
                  high_school_student_record__validation=2, ) |
                Q(student_record__level__isnull=False)
            )
            immersions = immersions_queryset.filter(
                Q(student__high_school_student_record__level__is_post_bachelor=True,
                  student__high_school_student_record__validation=2) |
                Q(student__student_record__level__isnull=False)
            )
        # Attended to 1 at least immersion
        datasets[0][level_label] = immersions.filter(
            attendance_status=1,
            slot__course__isnull=False,
            **immersions_filter)\
            .values('student')\
            .distinct()\
            .count()

        # Registered to one immersion
        datasets[1][level_label] = immersions.filter(
            cancellation_type__isnull=True,
            slot__course__isnull=False,
            **immersions_filter)\
            .values('student')\
            .distinct()\
            .count()

        # platform registrations
        datasets[2][level_label] = users.count()

    # Median calculation for structure managers (of filtering on a specific structure)
    if structure:
        # =======================================================
        # Attended to at least 1 immersion median
        # =======================================================
        establishment_structures = Structure.objects.filter(establishment=structure.establishment).distinct()

        one_immersion_attendance_students_counts = []
        one_immersion_registration_students_counts = []

        for establishment_structure in establishment_structures:
            qs = Immersion.objects.filter(
                slot__course__structure=establishment_structure
            )
            if qs.count():
                one_immersion_attendance_students_counts.append(
                    qs.filter(attendance_status=1).values('student').distinct().count()
                )

                one_immersion_registration_students_counts.append(
                    qs.values('student').distinct().count()
                )

        median = parse_median(one_immersion_attendance_students_counts)
        if median is not None:
            datasets[0]['name'] += f" [bold](m = {median})[/bold]"

        median = parse_median(one_immersion_registration_students_counts)
        if median is not None:
            datasets[1]['name'] += f" [bold](m = {median})[/bold]"

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series
    }

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_registration_charts_cats_by_trainings(request):
    """
    Data for amcharts 4
    Horizontal bars format, part 2
    parameters are in request.POST
    Filter by trainings
    """

    immersions_filter = {}

    # Parse filters in POST request
    _highschools_ids = request.POST.getlist("highschools_ids[]")
    _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")
    _structures_ids = request.POST.getlist("structure_ids[]")
    level_value = request.POST.get("level", 0)
    max_x = 0 # for scale adjustment

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
    if _highschools_ids:
        immersions_filter["slot__course__highschool__in"] = _highschools_ids

    if _structures_ids:
        immersions_filter["slot__course__structures__in"] = _structures_ids

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
            "calculateTotals": True,
            "extraMax": 0.1
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

    immersions_queryset = Immersion.objects.prefetch_related(
        'student__high_school_record__level', 'student__student_record__level', 'student__visitor_record',
        'slot__course__training__structure'
    )

    # High schools
    for highschool in HighSchool.objects.filter(id__in=_highschools_ids):
        hs_immersions = immersions_queryset.filter(slot__course__highschool=highschool)

        dataset_one_immersion = { 'name': highschool.label, 'none': 0 }
        dataset_attended_one = { 'name': highschool.label, 'none': 0 }

        for level in levels:
            if level == 'visitors':
                level_label = gettext("Visitors")
                immersions = hs_immersions.filter(
                    student__visitor_record__isnull=False,
                    student__visitor_record__validation=2
                )
            elif not level.is_post_bachelor:
                level_label = level.label
                immersions = hs_immersions.filter(
                    student__high_school_student_record__level=level,
                    student__high_school_student_record__validation=2
                )
            else: # is_post_bachelor : highschool and higher education institutions levels
                level_label = level.label

                # Filter by trainings of this high school : postbac pupils + students
                immersions = hs_immersions.filter(
                    Q(student__high_school_student_record__level=level,
                      student__high_school_student_record__validation=2) |
                    Q(student__student_record__level__in=StudentLevel.objects.all())
                )

            dataset_one_immersion[level_label] = immersions\
                .filter(cancellation_type__isnull=True)\
                .values('student')\
                .distinct()\
                .count()

            dataset_attended_one[level_label] = immersions\
                .filter(attendance_status=1)\
                .values('student')\
                .distinct()\
                .count()

        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # Higher institutions
    for establishment_id in _higher_institutions_ids:
        structures = Structure.objects.filter(establishment__id=establishment_id)
        estab_immersions = immersions_queryset.filter(slot__course__structure__in=structures)

        try:
            establishment = Establishment.objects.get(pk=establishment_id)
            label = establishment.label
        except Establishment.DoesNotExist:
            label = gettext("Establishment not found")

        dataset_one_immersion = {'name': label, 'none': 0 }
        dataset_attended_one = {'name': label, 'none': 0 }

        for level in levels:
            if level == 'visitors':
                level_label = gettext("Visitors")
                immersions = estab_immersions.filter(
                    student__visitor_record__isnull=False,
                    student__visitor_record__validation=2
                )
            elif not level.is_post_bachelor:
                level_label = level.label
                immersions = estab_immersions.filter(
                    student__high_school_student_record__level=level,
                    student__high_school_student_record__validation=2
                )
            else:  # post bachelor levels : include students
                level_label = level.label
                immersions = estab_immersions.filter(
                    Q(student__student_record__isnull=False)
                    | Q(student__high_school_student_record__validation=2,
                        student__high_school_student_record__level__in=HighSchoolLevel.objects.filter(
                            is_post_bachelor=True))
                )

            # registered to at least 1 immersion
            dataset_one_immersion[level_label] = immersions\
                .filter(cancellation_type__isnull=True) \
                .values('student') \
                .distinct()\
                .count()

            # attended to 1 immersion
            dataset_attended_one[level_label] = immersions\
                .filter(attendance_status=1)\
                .values('student')\
                .distinct()\
                .count()

        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # Structures when filtering on my trainings
    for structure_id in _structures_ids:
        strs_immersions = immersions_queryset.filter(slot__course__structure__id=structure_id)

        try:
            structure = Structure.objects.get(pk=structure_id)
            label = f"{structure.establishment.short_label} - {structure.label}"
        except Structure.DoesNotExist:
            label = gettext("Structure not found")

        dataset_one_immersion = {'name': label, 'none': 0 }
        dataset_attended_one = {'name': label, 'none': 0 }

        for level in levels:
            if level == 'visitors':
                level_label = gettext("Visitors")
                immersions = strs_immersions.filter(
                    student__visitor_record__isnull=False,
                    student__visitor_record__validation=2
                )
            elif not level.is_post_bachelor:
                level_label = level.label
                immersions = strs_immersions.filter(
                    student__high_school_student_record__level=level,
                    student__high_school_student_record__validation=2
                )
            else:  # post bachelor levels : include students
                level_label = level.label
                immersions = strs_immersions.filter(
                    Q(student__student_record__isnull=False)
                    | Q(student__high_school_student_record__validation=2,
                        student__high_school_student_record__level__in=HighSchoolLevel.objects.filter(is_post_bachelor=True))
                )

            # registered to at least 1 immersion
            dataset_one_immersion[level_label] = immersions\
                .filter(cancellation_type__isnull=True)\
                .values('student')\
                .distinct()\
                .count()

            # attended to 1 immersion
            dataset_attended_one[level_label] = immersions\
                .filter(attendance_status=1)\
                .values('student')\
                .distinct()\
                .count()

        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # =========

    # Adjust X axis scale to have the same max value on all bars
    max_x = max([
        max(map(lambda x:sum([v for k,v in x.items() if k != 'name']), datasets['one_immersion'])),
        max(map(lambda x:sum([v for k,v in x.items() if k != 'name']), datasets['attended_one']))
    ])

    if max_x:
        axes['x'][0]['max'] = math.ceil(max_x * 1.1)

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

    return JsonResponse(response, safe=False)


@is_post_request
@is_ajax_request
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC")
def get_registration_charts_cats_by_population(request):
    """
    Data for amcharts 4
    Horizontal bars format, part 2
    parameters are in request.POST
    """

    immersions_filter = {}
    # Parse filters in POST request
    _highschools_ids = request.POST.getlist("highschools_ids[]")
    _higher_institutions_ids = request.POST.getlist("higher_institutions_ids[]")
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
    if _highschools_ids:
        immersions_filter["student__high_school_student_record__highschool__id__in"] = _highschools_ids

    if _higher_institutions_ids:
        immersions_filter["student__student_record__uai_code__in"] = _higher_institutions_ids

    # We need data for 2 or 3 graphs (3 if filter_by_my_trainings is False)
    # Axes are common, just make sure we always use 'name' as attribute name for category
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
            "calculateTotals": True,
            "extraMax": 0.1
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

    users_queryset = ImmersionUser.objects.prefetch_related(
        "high_school_student_record__highschool", "student_record", "visitor_record").all()

    immersions_queryset = Immersion.objects.prefetch_related(
        'student__high_school_record__level', 'student__student_record__level', 'student__visitor_record',
        'slot__course__training__structure'
    )

    # High schools
    for highschool in HighSchool.objects.filter(id__in=_highschools_ids):
        hs_immersions = immersions_queryset.filter(
            student__high_school_student_record__highschool=highschool,
            student__high_school_student_record__validation = 2
        )

        dataset_platform_regs = { 'name': highschool.label, 'none': 0 }
        dataset_one_immersion = { 'name': highschool.label, 'none': 0 }
        dataset_attended_one = { 'name': highschool.label, 'none': 0 }

        for level in levels:
            if level == 'visitors':
                continue
            else:
                level_label = level.label
                immersions = hs_immersions.filter(
                    student__high_school_student_record__level=level
                )
                users = users_queryset.filter(
                    high_school_student_record__highschool = highschool,
                    high_school_student_record__level = level,
                )

            dataset_platform_regs[level_label] = users.count()  # plaform

            dataset_one_immersion[level_label] = immersions\
                .filter(cancellation_type__isnull=True)\
                .values('student')\
                .distinct()\
                .count()

            dataset_attended_one[level_label] = immersions\
                .filter(attendance_status=1)\
                .values('student')\
                .distinct()\
                .count()

        datasets['platform_regs'].append(dataset_platform_regs.copy())
        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # Higher institutions
    for uai_code in _higher_institutions_ids:
        hii_qs = users_queryset.filter(student_record__uai_code=uai_code)
        hii_immersions = immersions_queryset.filter(student__student_record__uai_code=uai_code)

        try:
            hei = HigherEducationInstitution.objects.get(pk=uai_code)
            label = hei.label
        except HigherEducationInstitution.DoesNotExist:
            label = "{} ({})".format(uai_code, gettext("no name match yet"))

        dataset_platform_regs = {'name': label, 'none': 0 }
        dataset_one_immersion = {'name': label, 'none': 0 }
        dataset_attended_one = {'name': label, 'none': 0 }

        level_label = gettext('Post-bac')

        # registered on plaform
        dataset_platform_regs[level_label] = hii_qs.count()

        # registered to at least one immersion
        dataset_one_immersion[level_label] = hii_immersions\
            .filter(cancellation_type__isnull=True)\
            .values('student')\
            .distinct()\
            .count()

        # attended to 1 immersion
        dataset_attended_one[level_label] = hii_immersions\
            .filter(attendance_status=1) \
            .values('student') \
            .distinct()\
            .count()

        datasets['platform_regs'].append(dataset_platform_regs.copy())
        datasets['one_immersion'].append(dataset_one_immersion.copy())
        datasets['attended_one'].append(dataset_attended_one.copy())

    # =========

    # Adjust X axis scale to have the same max value on all bars
    max_x = max([
        max(map(lambda x: sum([v for k, v in x.items() if k != 'name']), datasets['platform_regs'])),
        max(map(lambda x: sum([v for k, v in x.items() if k != 'name']), datasets['one_immersion'])),
        max(map(lambda x: sum([v for k, v in x.items() if k != 'name']), datasets['attended_one'])),
    ])

    if max_x:
        axes['x'][0]['max'] = math.ceil(max_x * 1.1)

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
@groups_required("REF-ETAB", "REF-ETAB-MAITRE", "REF-TEC", "REF-STR")
def get_slots_charts(request):
    """
    Slots data for amcharts 4
    Horizontal bars format, part 2
    """

    user = request.user

    immersions_filter = {}
    # Parse filters in POST request
    establishment_id = request.GET.get("establishment_id")
    empty_structures = request.GET.get("empty_structures", False) == 'true'

    # We need data for 2 or 3 graphs (3 if filter_by_my_trainings is False)
    # Axes are common, just make sure we always use 'name' as attribute name for category
    axes = {
        'x': [{
            "type": "ValueAxis",
            "min": 0,
            "maxPrecision": 0,
            "calculateTotals": True,
            "extraMax": 0.1
        }],
        'y': [{
            "type": "CategoryAxis",
            "dataFields": {
                "category": "name",
            }
        }],
    }

    establishments_slots_count = {}
    for establishment in Establishment.objects.filter(active=True):
        establishments_slots_count[establishment.id] = \
            Slot.objects.filter(
                course__structure__establishment=establishment,
                published=True
            ).count()

    if user.is_master_establishment_manager() or user.is_operator():
        if establishment_id:
            structures = Structure.objects.filter(establishment=establishment_id, active= True)
        else:
            structures = Structure.objects.filter(active=True)
    else:
        structures = Structure.objects.filter(establishment=user.establishment, active=True)

    # Each dataset represents a structure
    datasets = []

    for structure in structures:
        slots_count = Slot.objects.filter(
            course__isnull=False,
            course__structure=structure,
            published=True
        ).count()

        if empty_structures or slots_count:
            if user.is_master_establishment_manager() or user.is_operator():
                name = f"{structure.label} ({structure.establishment.short_label})"
            else:
                name = structure.label

            # Avoid division by 0 error
            if establishments_slots_count[structure.establishment.id]:
                percentage = round(slots_count / establishments_slots_count[structure.establishment.id] * 100, 1)
            else:
                percentage = 0

            datasets.append({
                'name': name,
                'slots_count': slots_count,
                'percentage': percentage,
                'none': 0
            })

    datasets = sorted(datasets, key=lambda k:k['slots_count'])

    # Series
    series = [{
        "name": "Structure",
        "type": "ColumnSeries",

        "dataFields": {
            "valueX": "slots_count",
            "categoryY": "name",
        },
        "columns": {
            "template": {
                "width": "20%",
                "tooltipText": "{percentage} %",
            },
        }
    }]

    response = {
        'axes': axes,
        'datasets': datasets,
        'series': series
    }

    print(f"response : {response}")

    return JsonResponse(response, safe=False)

