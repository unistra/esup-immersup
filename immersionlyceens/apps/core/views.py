import json
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core import serializers
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect

from immersionlyceens.apps.core.models import Component

logger = logging.getLogger(__name__)

# Create your views here.

# TODO: !!!!!!!!!!!!!!!!!!!!!!! AUTHORIZATION REQUIRED !!!!!!!!!!!!!!!!!!!!!!!
def import_holidays(request):
    """Import holidays from API if it's convigured"""
    from immersionlyceens.apps.core.models import Holiday
    from immersionlyceens.apps.core.models import UniversityYear

    redirect_url = '/admin/core/holiday'

    if settings.WITH_HOLIDAY_API \
            and settings.HOLIDAY_API_URL\
            and settings.HOLIDAY_API_MAP\
            and settings.HOLIDAY_API_DATE_FORMAT:
        url = settings.HOLIDAY_API_URL

        # get holidays data
        data = []
        try:
            u = UniversityYear.objects.get(active=True)
        except Exception as exc:
            logger.error(str(exc))
            return redirect(redirect_url)

        # get API holidays
        try:
            data = requests.get(url.format(year=u.start_date.year)).json()
            for elem in requests.get(url.format(year=u.end_date.year)).json():
                data.append(elem)
        except Exception as exc:
            logging.error(str(exc))

        # store
        for holiday in data:
            if isinstance(holiday, dict):
                _label = None
                _date = None

                # get mapped fields
                try:
                    _date_unformated = holiday[settings.HOLIDAY_API_MAP['date']]
                    _date = datetime.strptime(_date_unformated, settings.HOLIDAY_API_DATE_FORMAT)
                    _label = holiday[settings.HOLIDAY_API_MAP['label']] + ' ' + str(_date.year)
                except ValueError as exc:
                    logger.error(str(exc))

                # Save
                try:
                    Holiday(label=_label, date=_date).save()
                except IntegrityError as exc:
                    logger.warn(str(exc))


    # TODO: dynamic redirect
    return redirect(redirect_url)


# TODO : AUTH
def list_of_components(request):
    template = 'slots/list_components.html'

    if request.user.is_scuio_ip_manager() or request.user.is_superuser():
        # components = sorted(Component.objects.all(), lambda e: e.code)
        components = Component.objects.all()
        return render(request, template, context={'components': components})

    elif request.user.is_component_manager():
        if request.user.components.count() > 1:
            print(request.user.components.count())
            return render(request, template, context={'components': request.user.components.all()})
        else:  # Only one
            components = sorted(request.user.components.all()[0].id, lambda e: e.code)
            return redirect('slots_list', component=components)

    else:
        # TODO: error handler
        return render(request, 'base.html')


# TODO : AUTH
def list_of_slots(request, component):
    template = 'slots/list_slots.html'

    if request.user.is_component_manager():
        if component not in [c.id for c in request.user.components.all()]:
            pass
            # TODO: Not authorized
    elif not request.user.is_scuio_ip_manager() or not request.user.is_superuser():
        pass
    else:
        return render(request, 'base.html')

    context = {
        'component': Component.objects.get(id=component)
    }
    return render(request, template, context=context)


# TODO: AUTH
def add_slot(request):
    return render(request, 'slot/add_slot.html')

# TODO: AUTH
def modify_slot(request, slot_id):
    return render(request, 'base.html')

# TODO: AUTH
def del_slot(request, slot_id):
    return render(request, 'base.html')
