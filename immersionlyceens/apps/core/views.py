import json
import logging
from datetime import datetime

import requests
from immersionlyceens.apps.core.models import Component
from immersionlyceens.decorators import groups_required

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core import serializers
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy as _

from .forms import CourseForm
from .models import Component, Course, ImmersionUser

logger = logging.getLogger(__name__)

# Create your views here.

# TODO: !!!!!!!!!!!!!!!!!!!!!!! AUTHORIZATION REQUIRED !!!!!!!!!!!!!!!!!!!!!!!
def import_holidays(request):
    """Import holidays from API if it's convigured"""
    from immersionlyceens.apps.core.models import Holiday
    from immersionlyceens.apps.core.models import UniversityYear

    redirect_url = '/admin/core/holiday'

    if (
        settings.WITH_HOLIDAY_API
        and settings.HOLIDAY_API_URL
        and settings.HOLIDAY_API_MAP
        and settings.HOLIDAY_API_DATE_FORMAT
    ):
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
# groups_required('SCUIO-IP','REF-CMP')
def components_list(request):
    template = 'slots/list_components.html'

    if request.user.is_scuio_ip_manager or request.user.is_superuser():
        # components = sorted(Component.objects.all(), lambda e: e.code)
        components = Component.activated.all()
        return render(request, template, context={'components': components})

    elif request.user.is_component_manager:
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
def slots_list(request, component):
    template = 'slots/list_slots.html'

    if request.user.is_component_manager():
        if component not in [c.id for c in request.user.components.all()]:
            pass
            # TODO: Not authorized
    elif not request.user.is_scuio_ip_manager() or not request.user.is_superuser():
        pass
    else:
        return render(request, 'base.html')

    context = {'component': Component.activated.get(id=component)}
    return render(request, template, context=context)


# TODO: AUTH
def add_slot(request):
    return render(request, 'slots/add_slot.html')


# TODO: AUTH
def modify_slot(request, slot_id):
    return render(request, 'slots/modify_slot.html')


# TODO: AUTH
def del_slot(request, slot_id):
    return render(request, 'base.html')


@groups_required('SCUIO-IP', 'REF-CMP')
def courses_list(request):
    component_id = None
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by(
        "code", "label"
    )

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id

    context = {"components": allowed_comps, "component_id": component_id}

    return render(request, 'core/courses_list.html', context)


@groups_required('SCUIO-IP', 'REF-CMP')
def course(request):
    teachers_list = []
    component_id = None
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by(
        "code", "label"
    )

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id

    if request.method == 'POST' and request.POST.get('save'):
        course_form = CourseForm(request.POST)

        # Teachers
        teachers_list = request.POST.get('teachers_list', [])

        try:
            teachers_list = json.loads(teachers_list)
        except Exception:
            messages.error(request, _("At least one teacher is required"))

        else:
            if course_form.is_valid():
                course = course_form.save()

                for teacher in teachers_list:
                    teacher_user = None
                    if isinstance(teacher, dict):
                        try:
                            teacher_user = ImmersionUser.objects.get(username=teacher['username'])
                        except ImmersionUser.DoesNotExist:
                            teacher_user = ImmersionUser.objects.create(
                                username=teacher['username'],
                                last_name=teacher['lastname'],
                                first_name=teacher['firstname'],
                                email=teacher['email'],
                            )

                            messages.success(request, _("User '%s' created" % teacher['username']))

                        try:
                            Group.objects.get(name='ENS-CH').user_set.add(teacher_user)
                        except Exception:
                            messages.error(
                                request,
                                _(
                                    "Couldn't add group 'ENS-CH' to user '%s'"
                                    % teacher['username']
                                ),
                            )

                        if teacher_user:
                            course.teachers.add(teacher_user)

                messages.success(request, _("Course successfully saved"))
                return HttpResponseRedirect('/core/course')
            else:
                for err_field, err_list in course_form.errors.get_json_data().items():
                    for error in err_list:
                        if error.get("message"):
                            messages.error(request, error.get("message"))
    else:
        course_form = CourseForm()

    context = {
        "components": allowed_comps,
        "component_id": component_id,
        "course_form": course_form,
        "teachers": json.dumps(teachers_list),
    }

    return render(request, 'core/course.html', context)


@groups_required('ENS-CH',)
def mycourses(request):
    return render(request, 'core/mycourses.html')


@groups_required('ENS-CH',)
def myslots(request):
    return render(request, 'core/myslots.html')
