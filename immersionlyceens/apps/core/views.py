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
from django.utils.translation import gettext, ugettext_lazy as _


from immersionlyceens.decorators import groups_required
from .admin_forms import HighSchoolForm

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
def slots_list(request):
    template = 'slots/list_slots.html'

    comp_id = request.GET.get('c')
    train_id = request.GET.get('t')

    components = []
    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all()
    elif request.user.is_component_manager():
        components = request.user.components.all()
    else:
        return render(request, 'base.html')

    context = {
        'components': components,
    }

    if comp_id:
        context['component_id'] = comp_id
    if train_id:
        context['training_id'] = train_id

    return render(request, template, context=context)


groups_required('SCUIO-IP','REF-CMP')
def add_slot(request, slot_id=None):
    slot_form = None
    context = {}
    slot = None
    teachers_idx = None

    if slot_id:
        slot = Slot.objects.get(id=slot_id)
        teachers_idx = [t.id for t in slot.teachers.all()]
        slot.id = None

    # get components
    components = []
    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all()
    elif request.user.is_component_manager:
        components = request.user.components.all()

    if request.method == 'POST' and (request.POST.get('save') or \
            request.POST.get('duplicate') or \
            request.POST.get('save_add')):

        slot_form = SlotForm(request.POST, instance=slot)
        teachers = []
        teacher_prefix = 'teacher_'
        for teacher_id in [e.replace(teacher_prefix, '') for e in request.POST if
                           teacher_prefix in e]:
            teachers.append(teacher_id)

        # if not pub --> len teachers must be > 0
        # else no teacher is needed
        published = request.POST.get('published') == 'on'
        if slot_form.is_valid() and (not published or len(teachers) > 0):
            slot_form.save()
            for teacher in teachers:
                slot_form.instance.teachers.add(teacher)
        else:
            context = {
                "components": components,
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "teacher_error": len(teachers) < 1,
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            return redirect('slots_list')
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            context = {
                "components": components,
                "slot_form": slot_form,
                "ready_load": False,
            }
            return render(request, 'slots/add_slot.html', context=context)
        else:
            return redirect('/')
    elif slot:
        slot_form = SlotForm(instance=slot)
    else:
        slot_form = SlotForm()

    context = {
        "components": components,
        "slot_form": slot_form,
        "ready_load": True,
    }
    if slot:
        context['slot'] = slot
        if not teachers_idx:
            context['teachers_idx'] = teachers_idx

    return render(request, 'slots/add_slot.html', context=context)


# TODO: AUTH
def modify_slot(request, slot_id):

    slot = Slot.objects.get(id=slot_id)
    slot_form = SlotForm(instance=slot)

    # get components
    components = []
    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all()
    elif request.user.is_component_manager:
        components = request.user.components.all()

    if request.method == 'POST' and (request.POST.get('save') or \
            request.POST.get('duplicate') or \
            request.POST.get('save_add')):

        slot_form = SlotForm(request.POST, instance=slot)

        teachers = []
        teacher_prefix = 'teacher_'
        for teacher_id in [e.replace(teacher_prefix, '') for e in request.POST if
                           teacher_prefix in e]:
            teachers.append(teacher_id)

        published = request.POST.get('published') == 'on'
        if slot_form.is_valid() and (not published or len(teachers) > 0):
            slot_form.save()
            slot_form.instance.teachers.clear()
            for teacher in teachers:
                slot_form.instance.teachers.add(teacher)
        else:
            context = {
                "slot": slot,
                "components": components,
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "teacher_error": len(teachers) < 1,
                "teachers_idx": [t.id for t in slot.teachers.all()],
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            return redirect('modify_slot', slot_id=slot_id)
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            context = {
                "components": components,
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": False,
                "teachers_idx": [t.id for t in slot.teachers.all()],
                "modify": True,
            }
            return render(request, 'slots/add_slot.html', context=context)
        else:
            context = {
                "slot": slot,
                "components": components,
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "teachers_idx": [t.id for t in slot.teachers.all()],
            }
            return render(request, 'slots/add_slot.html', context=context)

    context = {
        "slot": slot,
        "components": components,
        "trainings": Training.objects.filter(active=True),
        "slot_form": slot_form,
        "ready_load": True,
        "teachers_idx": [t.id for t in slot.teachers.all()],
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
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by(
        "code", "label"
    )

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id
    else:
        component_id = request.session.get("current_component_id", None)

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
            request.session["current_component_id"] = course.component_id
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

                request.session["current_component_id"] = new_course.component_id

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

                            messages.success(request, gettext("User '{}' created".format(teacher['username'])))
                            return_msg = teacher_user.send_message(request, 'CPT_CREATE_ENS')

                            if not return_msg:
                                messages.success(request,
                                    gettext("A confirmation email has been sent to {}".format(teacher['email'])))
                            else:
                                messages.warning(request, return_msg)

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


@groups_required('REF-LYC', 'SCUIO-IP')
def my_high_school(request,  high_school_id=None):
    from .models import HighSchool

    if request.user.highschool.id != high_school_id:
        return redirect('home')

    hs = HighSchool.objects.get(id=high_school_id)
    post_values = request.POST.copy()
    post_values['label'] = hs.label

    high_school_form = None
    context = {
        'high_school': hs,
        'modified': False,
    }

    if request.method == 'POST':
        high_school_form = HighSchoolForm(post_values, instance=hs, request=request)
        if high_school_form.is_valid():
            high_school_form.save()
            context['modified'] = True
    else:
        high_school_form = HighSchoolForm(instance=hs, request=request)

    context['high_school_form'] = high_school_form

    return render(request, 'core/my_high_school.html', context)

# @@@
def student_validation(request, high_school_id=None):
    from .models import HighSchool

    # student_validation
    context = {}

    if high_school_id:
        context['high_school'] = HighSchool.objects.get(id=high_school_id)
    else:
        context['high_schools'] = HighSchool.objects.all().order_by('city')

    return render(request, 'core/student_validation.html', context)
