import json
import logging

from immersionlyceens.apps.core.models import HighSchool, HigherEducationInstitution

logger = logging.getLogger(__name__)

def process_request_filters(request):
    """
    Take request objects with POST data and returns highschools and
    higher education institutions data for charts filters
    """

    highschools = []
    highschools_ids = []
    higher_institutions = []
    higher_institutions_ids = []

    try:
        level_filter = int(request.POST.get('level', 0))
    except ValueError:
        level_filter = 0 # default : all levels

    _insts = request.POST.get('insts')

    if _insts:
        try:
            insts = json.loads(_insts)

            hs = {h.pk:h for h in HighSchool.objects.all()}
            higher = {h.uai_code:h for h in HigherEducationInstitution.objects.all()}

            highschools = sorted(
                 f"{hs[inst[1]].city.title()} - {hs[inst[1]].label}" for inst in insts if inst[0] == 0 
            )
            higher_institutions = sorted(
                 f"{higher[inst[1]].city.title()} - {higher[inst[1]].label}" for inst in insts if inst[0] == 1 
            )

            highschools_ids = [ inst[1] for inst in insts if inst[0]==0 ]
            higher_institutions_ids = [ inst[1] for inst in insts if inst[0]==1 ]

        except Exception as e:
            logger.exception("Filter form values error")

    return level_filter, highschools_ids, highschools, higher_institutions_ids, higher_institutions
