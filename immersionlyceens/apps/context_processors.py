from immersionlyceens.apps.core.models import Establishment

def establishments(request):
    return {'core_establishments': Establishment.activated.all().order_by('label')}