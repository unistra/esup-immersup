import json
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core import serializers
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy as _

from immersionlyceens.decorators import groups_required

from .forms import CourseForm, SlotForm
from .models import Component, Course, ImmersionUser, Slot, Training, UniversityYear

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

    if request.user.is_scuio_ip_manager() or request.user.is_superuser:
        # components = sorted(Component.objects.all(), lambda e: e.code)
        components = Component.activated.all()
        return render(request, template, context={'components': components})

    elif request.user.is_component_manager:
        if request.user.components.count() > 1:
            return render(request, template, context={'components': request.user.components.all()})
        else:  # Only one
            components = request.user.components.all()
            return redirect('slots_list', component=components[0].id)

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
    elif not request.user.is_scuio_ip_manager() or not request.user.is_superuser:
        pass
    else:
        return render(request, 'base.html')

    context = {
        'component': Component.activated.get(id=component)
    }
    return render(request, template, context=context)


groups_required('SCUIO-IP','REF-CMP')
def add_slot(request, slot_id=None):
    slot_form = None
    context = {}
    slot = None
    if request.method == 'POST' and (request.POST.get('save') or \
            request.POST.get('duplicate') or \
            request.POST.get('save_add')):

        slot_form = SlotForm(request.POST, instance=slot)
        if slot_form.is_valid():
            slot_form.save()
            for teacher in request.POST.getlist('teachers', []):
                slot_form.instance.teachers.add(teacher)
        else:
            context = {
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            return redirect('components_list')
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            context = {
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": False,
            }
            return render(request, 'slots/add_slot.html', context=context)
        else:
            return redirect('/')
    else:
        slot_form = SlotForm()

    context = {
        "trainings": Training.objects.filter(active=True),
        "slot_form": slot_form,
        "ready_load": True,
    }
    return render(request, 'slots/add_slot.html', context=context)


# TODO: AUTH
def modify_slot(request, slot_id):

    slot = Slot.objects.get(id=slot_id)
    slot_form = SlotForm(instance=slot)

    if request.method == 'POST' and (request.POST.get('save') or \
            request.POST.get('duplicate') or \
            request.POST.get('save_add')):

        slot_form = SlotForm(request.POST, instance=slot)
        if slot_form.is_valid():
            slot_form.save()
            slot_form.instance.teachers.clear()
            for teacher in request.POST.getlist('teachers', []):
                slot_form.instance.teachers.add(teacher)
        else:

            context = {
                "slot": slot,
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            return redirect('modify_slot', slot_id=slot_id)
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            context = {
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": False,
            }
            return render(request, 'slots/add_slot.html', context=context)
        else:
            context = {
                "slot": slot,
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
            }
            return render(request, 'slots/add_slot.html', context=context)

    context = {
        "slot": slot,
        "trainings": Training.objects.filter(active=True),
        "slot_form": slot_form,
        "ready_load": True,
    }
    return render(request, 'slots/add_slot.html', context=context)



# TODO: AUTH
# @groups_required('SCUIO-IP','REF-CMP')
def del_slot(request, slot_id):
    from immersionlyceens.apps.core.models import Slot
    # todo: check if user can delete this slot
    slot = Slot.objects.get(id=slot_id)
    slot.delete()
    # todo check if obj is delete and return good response

    return HttpResponse('ok')


@groups_required('SCUIO-IP', 'REF-CMP')
def courses_list(request):
    can_update_courses = False
    component_id = None
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by(
        "code", "label"
    )

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id

    # Check if we can update courses
    try:
        active_year = UniversityYear.objects.get(active=True)
        can_update_courses = active_year.date_is_between(datetime.today().date())
    except UniversityYear.DoesNotExist:
        pass
    except UniversityYear.MultipleObjectsReturned:
        pass

    if not can_update_courses:
        messages.warning(request,
            _("Courses cannot be updated or deleted because the active university year has not begun yet."))

    context = {
        "components": allowed_comps,
        "component_id": component_id,
        "can_update_courses": can_update_courses
    }

    return render(request, 'core/courses_list.html', context)


groups_required('SCUIO-IP','REF-CMP')
def course(request, course_id=None, duplicate=False):
    teachers_list = []
    save_method = None
    course = None
    course_form = None
    update_rights = True
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by("code", "label")

    if course_id:
        try:
            course = Course.objects.get(pk=course_id)

            teachers_list = [{
                "username": t.username,
                "lastname": t.last_name,
                "firstname": t.first_name,
                "email": t.email,
                "display_name": "%s %s" % (t.last_name, t.first_name),
                "is_removable": not t.slots.filter(course=course_id).exists(),
            } for t in course.teachers.all()]

            if duplicate:
                data = {
                    'component':course.component,
                    'training':course.training,
                    'published':course.published,
                    'label':course.label,
                    'url':course.url,
                }
                course = Course(**data)
                # course_form = CourseForm(initial=data, request=request)
                course_form = CourseForm(instance=course, request=request)
            else:
                course_form = CourseForm(instance=course, request=request)
        except Course.DoesNotExist:
            course_form = CourseForm(request=request)

        # check user rights
        if course and not (course.get_components_queryset() & allowed_comps).exists():
            update_rights = False
            messages.error(request,
                _("You don't have enough privileges to update this course"))

    if request.POST.get('save'):
        save_method = 'save'
    elif request.POST.get('save_add_new'):
        save_method = 'save_add_new'
    elif request.POST.get('save_duplicate'):
        save_method = 'save_duplicate'

    if request.method == 'POST' and save_method:
        course_form = CourseForm(request.POST, instance=course, request=request)

        # Teachers
        teachers_list = request.POST.get('teachers_list', [])

        try:
            teachers_list = json.loads(teachers_list)
            assert(len(teachers_list) > 0)
        except Exception:
            messages.error(request, _("At least one teacher is required"))
        else:
            if course_form.is_valid():
                new_course = course_form.save()

                current_teachers = [
                    u for u in new_course.teachers.all().values_list('username', flat=True) ]
                new_teachers = [ teacher.get('username') for teacher in teachers_list ]

                # Teachers to add
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
                            new_course.teachers.add(teacher_user)

                # Teachers to remove
                remove_list = set(current_teachers) - set(new_teachers)
                for username in remove_list:
                    try:
                        user = ImmersionUser.objects.get(username=username)
                        new_course.teachers.remove(user)
                    except ImmersionUser.DoesNotExist:
                        pass

                if course:
                    messages.success(request, _("Course successfully updated"))
                else:
                    messages.success(request, _("Course successfully saved"))

                if save_method == "save":
                    return HttpResponseRedirect("/core/courses_list")
                elif save_method == "save_duplicate":
                    return HttpResponseRedirect("/core/course/%s/1" % new_course.id)
                elif save_method == "save_add_new":
                    return HttpResponseRedirect("/core/course")
            else:
                for err_field, err_list in course_form.errors.get_json_data().items():
                    for error in err_list:
                        if error.get("message"):
                            messages.error(request, error.get("message"))

    if not course_form:
        course_form = CourseForm(request=request)

    context = {
        "course": course,
        "course_form": course_form,
        "duplicate": True if duplicate else False,
        "teachers": json.dumps(teachers_list),
        "update_rights": update_rights,
    }

    return render(request, 'core/course.html', context)


@groups_required('ENS-CH',)
def mycourses(request):

    component_id = None
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP')

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id

    context = {"components": allowed_comps, "component_id": component_id}

    return render(request, 'core/mycourses.html', context)



@groups_required('ENS-CH',)
def myslots(request):
    return render(request, 'core/myslots.html')
