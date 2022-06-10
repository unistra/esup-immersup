from django.utils.translation import gettext
from immersionlyceens.apps.core.models import Establishment

def establishments(request):
    return {'core_establishments': Establishment.activated.all().order_by('label')}

def master_establishment(request):
    master_establishment_label = gettext("Please add a master establishment !")

    try:
        master_establishment = Establishment.activated.get(master=True)
        master_establishment_label = master_establishment.label
    except Establishment.DoesNotExist:
        pass

    return {
        'master_establishment_label': master_establishment_label
    }