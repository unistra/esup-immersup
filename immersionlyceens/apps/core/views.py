import logging
from datetime import datetime

import requests
from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import render, redirect
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

        try:
            data = requests.get(url.format(year=u.start_date.year)).json()
            print(data)
            for elem in requests.get(url.format(year=u.end_date.year)).json():
                data.append(elem)
        except Exception as exc:
            logging.error(str(exc))

        for holiday in data:
            if isinstance(holiday, dict):
                _date_unformated = holiday[settings.HOLIDAY_API_MAP['date']]
                _date = datetime.strptime(_date_unformated, settings.HOLIDAY_API_DATE_FORMAT)
                _label = holiday[settings.HOLIDAY_API_MAP['label']] + ' ' + str(_date.year)

                try:
                    h = Holiday(label=_label, date=_date).save()
                except IntegrityError:
                    print('dd')
                    pass

    # TODO: dynamic redirect
    return redirect(redirect_url)
