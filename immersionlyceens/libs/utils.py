# pylint: disable=E1101
"""File for utils content"""
from datetime import datetime
from typing import Any, Dict

from django.template import Engine, Template, engines
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


def get_general_setting(name=None):
    """
    Get setting 'name' in GeneralSettings model and returns its value
    Raise ValueError if not found or None if 'name' is not set
    """
    if not name:
        return None

    try:
        value = core_models.GeneralSettings.objects.get(setting=name).parameters
    except core_models.GeneralSettings.DoesNotExist:
        # Variable not found
        raise NameError
    except AttributeError:
        # Variable is None
        raise ValueError

    # Variable is empty
    if not value:
        raise ValueError

    return value.get('value', '')


def get_information_text(code=None):
    """
    Get InformationText model by code and returns its value
    Raise ValueError if not found or None if 'name' is not set
    """
    if not code:
        return None

    try:
        value = core_models.InformationText.objects.get(code=code, active=True).content
    except core_models.InformationText.DoesNotExist:
        # Text not found
        raise NameError
    except AttributeError:
        # Text is None
        raise ValueError

    # Text is empty
    if not value:
        raise ValueError

    return value


def render_text(template_data: str, data: Dict[str, Any]) -> str:
    """
    Render a text base on jinja2 engine
    :param template_data:
    :param data:
    :return:
    """
    django_engine: Engine = engines["django"]
    template: Template = django_engine.from_string(template_data)
    return template.render(context=data)


def get_custom_theme_files(type=None):
    if not type:
        return None

    try:
        files = core_models.CustomThemeFile.objects.filter(type=type)
    except core_models.CustomThemeFile.DoesNotExist:
        raise NameError
    except AttributeError:
        raise ValueError

    # Variable is empty
    if not files:
        raise ValueError

    return files
