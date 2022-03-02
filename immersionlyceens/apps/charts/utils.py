import json
import logging

from immersionlyceens.apps.core.models import HighSchool, HigherEducationInstitution

logger = logging.getLogger(__name__)

def parse_median(data):
    """
    Calculate the median value of a list of numbers
    """
    if not isinstance(data, list) or not data:
        return None

    data = sorted(data)
    len_data = len(data)

    if len_data % 2 == 0:
        return (data[(len_data - 1) // 2] + data[(len_data + 1) // 2]) / 2.0
    else:
        return data[(len_data - 1) // 2]

def process_request_filters(request, my_trainings=False):
    """
    Take request objects with POST data and returns highschools and
    higher education institutions data for charts filters
    """

    highschools = []
    highschools_ids = []
    higher_institutions = []
    higher_institutions_ids = []
    structure_ids = []
    filter_by_my_trainings = my_trainings

    hs_filter = {}
    if request.user.is_high_school_manager() and request.user.highschool:
        hs_filter['pk'] = request.user.highschool.id

    try:
        level_filter = int(request.POST.get('level', 0))
    except ValueError:
        level_filter = 0 # default : all levels

    _insts = request.POST.get('insts')

    if _insts:
        try:
            insts = json.loads(_insts)

            hs = {h.pk:h for h in HighSchool.objects.filter(**hs_filter)}
            higher = {h.uai_code:h for h in HigherEducationInstitution.objects.all()}
            strs = {s.id:s for s in request.user.get_authorized_structures()}

            highschools = sorted(
                 f"{hs[inst[1]].city.title()} - {hs[inst[1]].label}" for inst in insts if inst[0] == 0 
            )
            higher_institutions = sorted(
                 f"{higher[inst[1]].city.title()} - {higher[inst[1]].label}" for inst in insts if inst[0] == 1 
            )
            structures = sorted(
                f"{strs[inst[2]].establishment.city.title()} - {strs[inst[2]].label}" for inst in insts if inst[0] == 2
            )

            highschools_ids = [ inst[1] for inst in insts if inst[0]==0 ]
            higher_institutions_ids = [ inst[1] for inst in insts if inst[0]==1 ]
            structure_ids = [ inst[2] for inst in insts if inst[0]==2 ]

        except Exception as e:
            logger.exception("Filter form values error")

    return level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions, structure_ids
