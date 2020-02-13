from datetime import datetime

from immersionlyceens.apps.core import models as core_models

def check_active_year():
    """
    Get the active year and check if today is in dates range
    Returns a 3 elements :
    - bool: registration available
    - bool: today() is in range
    - the active year
    """
    # TODO : add date to check as a parameter ?

    registration_is_available = False
    today_in_range = False
    active_year = None

    try:
        today = datetime.today().date()
        active_year = core_models.UniversityYear.objects.get(active=True)
        registration_is_available = active_year.registration_start_date <= today <= active_year.end_date
        today_in_range = active_year.start_date <= today <= active_year.end_date
    except (core_models.UniversityYear.DoesNotExist, core_models.UniversityYear.MultipleObjectsReturned):
        pass

    return registration_is_available, today_in_range, active_year
