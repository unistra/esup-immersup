import json
import logging
from datetime import datetime

import requests
from immersionlyceens.decorators import groups_required

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.translation import gettext, ugettext_lazy as _

from .forms import ContactForm, CourseForm, ComponentForm, MyHighSchoolForm, SlotForm
from .models import (Campus, CancelType, Component, Course, HighSchool, ImmersionUser, Slot,
    Training, UniversityYear, Immersion, Holiday)

logger = logging.getLogger(__name__)

# Create your views here.

@groups_required('SCUIO-IP')
def import_holidays(request):
    """
    Import holidays from API if it has been configured
    """
    redirect_url = '/admin/core/holiday'

    if all([settings.WITH_HOLIDAY_API, settings.HOLIDAY_API_URL, settings.HOLIDAY_API_MAP,
        settings.HOLIDAY_API_DATE_FORMAT]):
        url = settings.HOLIDAY_API_URL

        # get holidays data
        data = []
        try:
            year = UniversityYear.objects.get(active=True)
        except Exception as exc:
            logger.error(str(exc))
            return redirect(redirect_url)

        # get API holidays
        try:
            data = requests.get(url.format(year=year.start_date.year)).json()
            if year.start_date.year != year.end_date.year:
                data += requests.get(url.format(year=year.end_date.year)).json()
        except Exception as exc:
            logging.error(str(exc))

        # store
        for holiday in data:
            if isinstance(holiday, dict):
                _label = None
                _date = None

                # get mapped fields and save the object
                try:
                    _date_unformated = holiday[settings.HOLIDAY_API_MAP['date']]
                    _date = datetime.strptime(_date_unformated, settings.HOLIDAY_API_DATE_FORMAT)
                    _label = holiday[settings.HOLIDAY_API_MAP['label']] + ' ' + str(_date.year)
                    Holiday.objects.create(label=_label, date=_date)
                except ValueError as exc:
                    logger.error(str(exc))
                except IntegrityError as exc:
                    logger.warning(str(exc))

    return redirect(redirect_url)


@groups_required('SCUIO-IP', 'REF-CMP')
def slots_list(request):
    """
    Get slots list
    get filters : component and trainings
    """
    template = 'slots/list_slots.html'

    comp_id = request.GET.get('c')
    train_id = request.GET.get('t')

    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all()
    elif request.user.is_component_manager():
        components = request.user.components.all()
    else:
        return render(request, 'base.html')

    contact_form = ContactForm()

    context = {
        'components': components.order_by('label'),
        'contact_form': contact_form,
        'cancel_types': CancelType.objects.filter(active=True),
    }

    if comp_id and int(comp_id) in [c.id for c in components]:
        context['component_id'] = comp_id

        # Make sure the training is active and belongs to the selected component
        try:
            if train_id and Training.objects.filter(id=int(train_id), components=comp_id, active=True).exists():
                context['training_id'] = train_id
        except ValueError:
            pass

    return render(request, template, context=context)


@groups_required('SCUIO-IP', 'REF-CMP')
def add_slot(request, slot_id=None):
    slot = None
    teachers_idx = None

    if slot_id:
        try:
            slot = Slot.objects.get(id=slot_id)
            teachers_idx = [t.id for t in slot.teachers.all()]
            slot.id = None
        except Slot.DoesNotExist: # id not found : make an empty slot
            slot = Slot()
            teachers_idx = []

    # get components
    components = []
    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all().order_by('label')
    elif request.user.is_component_manager:
        components = request.user.components.all().order_by('label')

    if request.method == 'POST' and \
        any([request.POST.get('save'), request.POST.get('duplicate'), request.POST.get('save_add')]):
        slot_form = SlotForm(request.POST, instance=slot)
        teachers = []
        teacher_prefix = 'teacher_'
        for teacher_id in [e.replace(teacher_prefix, '') for e in request.POST if teacher_prefix in e]:
            teachers.append(teacher_id)

        # if published, teachers count must be > 0
        # else no teacher needed
        published = request.POST.get('published') == 'on'
        if slot_form.is_valid() and (not published or len(teachers) > 0):
            slot_form.save()
            for teacher in teachers:
                slot_form.instance.teachers.add(teacher)
            messages.success(request, _("Slot successfully added"))

            if published:
                course = Course.objects.get(id=request.POST.get('course'))
                if course and course.published:
                    messages.success(request, _("Course published"))
        else:
            context = {
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "course": Course.objects.get(id=request.POST.get('course', None)),
                "components": components,
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "teacher_error": len(teachers) < 1,
                "teachers_idx": [int(t) for t in teachers],
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            response = redirect('slots_list')
            response['Location'] += '?c={}&t={}'.format(
                request.POST.get('component', ''), request.POST.get('training', ''),
            )
            return response
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            return redirect('duplicate_slot', slot_id=slot_form.instance.id)
        else:
            return redirect('/')
    elif slot:
        slot_form = SlotForm(instance=slot)
    else:
        slot_form = SlotForm()

    context = {
        "components": components,
        "campus": Campus.objects.filter(active=True).order_by('label'),
        "slot_form": slot_form,
        "ready_load": True,
    }
    if slot:
        context['slot'] = slot
        context['course'] = slot.course
        context['teachers_idx'] = teachers_idx

    return render(request, 'slots/add_slot.html', context=context)


@groups_required('SCUIO-IP', 'REF-CMP')
def modify_slot(request, slot_id):
    """
    Update a slot
    """
    try:
        slot = Slot.objects.get(id=slot_id)
    except Slot.DoesNotExist:
        messages.warning(request, _("This slot id does not exist"))
        return redirect('/core/slots/')

    # Check whether the user has access to this slot
    if request.user.is_component_manager() and slot.course.component not in request.user.components.all():
        messages.error(request, _("This slot belongs to another component"))
        return redirect('/core/slots/')

    slot_form = SlotForm(instance=slot)
    # get components
    components = []
    if request.user.is_superuser or request.user.is_scuio_ip_manager():
        components = Component.activated.all().order_by('label')
    elif request.user.is_component_manager:
        components = request.user.components.all().order_by('label')

    if request.method == 'POST' and any([request.POST.get('save'), request.POST.get('duplicate'),
        request.POST.get('save_add')]):
        slot_form = SlotForm(request.POST, instance=slot)
        teachers = []
        teacher_prefix = 'teacher_'
        for teacher_id in [e.replace(teacher_prefix, '') for e in request.POST if teacher_prefix in e]:
            teachers.append(teacher_id)

        published = request.POST.get('published') == 'on'
        notify_student = request.POST.get('notify_student') == 'on'
        if slot_form.is_valid() and (not published or len(teachers) > 0):
            slot_form.save()
            slot_form.instance.teachers.clear()
            for teacher in teachers:
                slot_form.instance.teachers.add(teacher)
            messages.success(request, _("Slot successfully updated"))
        else:
            context = {
                "slot": slot,
                "components": components,
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "teacher_error": len(teachers) < 1,
                "teachers_idx": [int(t) for t in teachers],
            }
            return render(request, 'slots/add_slot.html', context=context)

        if published:
            course = Course.objects.get(id=request.POST.get('course'))
            if course and course.published:
                messages.success(request, _("Course published"))

        if notify_student:
            sent_msg = 0
            immersions = Immersion.objects.filter(slot=slot, cancellation_type__isnull=True)
            for immersion in immersions:
                if not immersion.student.send_message(request, 'CRENEAU_MODIFY_NOTIF', immersion=immersion, slot=slot):
                    sent_msg += 1

            if sent_msg:
                messages.success(request,  _("Notifications have been sent (%s)") % sent_msg)

        if request.POST.get('save'):
            response = redirect('slots_list')
            response['Location'] += '?c={}&t={}'.format(
                request.POST.get('component', ''), request.POST.get('training', ''),
            )
            return response
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            return redirect('duplicate_slot', slot_id=slot_form.instance.id)
        else:
            context = {
                "slot": slot,
                "course": Course.objects.get(id=request.POST.get('course', None)),
                "components": components,
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "trainings": Training.objects.filter(active=True).order_by('label'),
                "slot_form": slot_form,
                "ready_load": True,
                "teachers_idx": [t.id for t in slot.teachers.all()],
            }
            return render(request, 'slots/add_slot.html', context=context)

    context = {
        "slot": slot,
        "components": components,
        "campus": Campus.objects.filter(active=True).order_by('label'),
        "trainings": Training.objects.filter(active=True),
        "slot_form": slot_form,
        "ready_load": True,
        "teachers_idx": [t.id for t in slot.teachers.all()],
    }
    return render(request, 'slots/add_slot.html', context=context)


@groups_required('SCUIO-IP', 'REF-CMP')
def del_slot(request, slot_id):
    try:
        slot = Slot.objects.get(id=slot_id)
        # Check whether the user has access to this slot
        if request.user.is_component_manager() and slot.course.component not in request.user.components.all():
            return HttpResponse(gettext("This slot belongs to another component"))
        slot.delete()
    except Slot.DoesNotExist:
        pass

    return HttpResponse('ok')


@groups_required('SCUIO-IP', 'REF-CMP')
def courses_list(request):
    can_update_courses = False
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by("code", "label")

    if allowed_comps.count() == 1:
        component_id = allowed_comps.first().id
    else:
        component_id = request.session.get("current_component_id", None)

    # Check if we can add/update courses
    try:
        active_year = UniversityYear.objects.get(active=True)
        can_update_courses = active_year.date_is_between(datetime.today().date())
    except UniversityYear.DoesNotExist:
        pass
    except UniversityYear.MultipleObjectsReturned:
        pass

    if not can_update_courses:
        messages.warning(
            request,
            _(
                """Courses cannot be created, updated or deleted because the """
                """active university year has not begun yet (or is already over."""
            ),
        )

    context = {"components": allowed_comps, "component_id": component_id, "can_update_courses": can_update_courses}

    return render(request, 'core/courses_list.html', context)


@groups_required('SCUIO-IP', 'REF-CMP')
def course(request, course_id=None, duplicate=False):
    teachers_list = []
    save_method = None
    course = None
    course_form = None
    update_rights = True
    can_update_courses = False
    allowed_comps = Component.activated.user_cmps(request.user, 'SCUIO-IP').order_by("code", "label")

    # Check if we can add/update courses
    try:
        active_year = UniversityYear.objects.get(active=True)
        can_update_courses = active_year.date_is_between(datetime.today().date())
    except UniversityYear.DoesNotExist:
        pass
    except UniversityYear.MultipleObjectsReturned:
        pass

    if not can_update_courses:
        messages.warning(
            request,
            _(
                """Courses cannot be created, updated or deleted because the """
                """active university year has not begun yet (or is already over."""
            ),
        )

    if course_id:
        try:
            course = Course.objects.get(pk=course_id)
            request.session["current_component_id"] = course.component_id
            teachers_list = [
                {
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": "%s %s" % (t.last_name, t.first_name),
                    "is_removable": not t.slots.filter(course=course_id).exists(),
                }
                for t in course.teachers.all()
            ]

            if duplicate:
                data = {
                    'component': course.component,
                    'training': course.training,
                    'published': course.published,
                    'label': course.label,
                    'url': course.url,
                }
                course = Course(**data)
                course_form = CourseForm(instance=course, request=request)
            else:
                course_form = CourseForm(instance=course, request=request)
        except Course.DoesNotExist:
            course_form = CourseForm(request=request)

        # check user rights
        if course and not (course.get_components_queryset() & allowed_comps).exists():
            update_rights = False
            messages.error(request, _("You don't have enough privileges to update this course"))

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
            assert len(teachers_list) > 0
        except Exception:
            messages.error(request, _("At least one teacher is required"))
        else:
            if course_form.is_valid():
                new_course = course_form.save()

                request.session["current_component_id"] = new_course.component_id

                current_teachers = [u for u in new_course.teachers.all().values_list('username', flat=True)]
                new_teachers = [teacher.get('username') for teacher in teachers_list]

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

                            messages.success(request, gettext("User '{}' created").format(teacher['username']))
                            return_msg = teacher_user.send_message(request, 'CPT_CREATE_ENS')

                            if not return_msg:
                                messages.success(
                                    request,
                                    gettext("A confirmation email has been sent to {}").format(teacher['email']),
                                )
                            else:
                                messages.warning(request, return_msg)

                        try:
                            Group.objects.get(name='ENS-CH').user_set.add(teacher_user)
                        except Exception:
                            messages.error(
                                request, _("Couldn't add group 'ENS-CH' to user '%s'" % teacher['username']),
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
        "can_update_courses": can_update_courses,
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
    contact_form = ContactForm()

    context = {
        'contact_form': contact_form,
    }

    return render(request, 'core/myslots.html', context)


@groups_required('REF-LYC',)
def my_high_school(request, high_school_id=None):
    if request.user.highschool.id != high_school_id:
        return redirect('home')

    hs = HighSchool.objects.get(id=high_school_id)
    post_values = request.POST.copy()
    post_values['label'] = hs.label

    high_school_form = None
    context = {
        'high_school': hs,
        'modified': False,
        'referents': ImmersionUser.objects.filter(highschool=request.user.highschool),
    }

    if request.method == 'POST':
        high_school_form = MyHighSchoolForm(post_values, instance=hs, request=request)
        if high_school_form.is_valid():
            high_school_form.save()
            context['modified'] = True
    else:
        high_school_form = MyHighSchoolForm(instance=hs, request=request)

    context['high_school_form'] = high_school_form

    return render(request, 'core/my_high_school.html', context)


@groups_required('REF-LYC','SCUIO-IP')
def my_students(request):
    highschool = None

    try:
        highschool = request.user.highschool
    except Exception:
        pass

    context = {
        'highschool': highschool,
        'is_scuio_ip_manager': request.user.is_scuio_ip_manager(),
    }

    return render(request, 'core/highschool_students.html', context)


@groups_required('REF-LYC', 'SCUIO-IP')
def student_validation(request, high_school_id=None):
    from .models import HighSchool

    if not high_school_id and request.user.is_high_school_manager():
        return redirect('student_validation', high_school_id=request.user.highschool.id)

    # student_validation
    context = {}

    if high_school_id:
        context['high_school'] = HighSchool.objects.get(id=high_school_id)
    else:
        context['high_schools'] = HighSchool.objects.all().order_by('city')

    if request.GET.get('hs_id'):
        try:
            context['hs_id'] = int(request.GET.get('hs_id'))
        except ValueError:
            pass


    return render(request, 'core/student_validation.html', context)


@groups_required('REF-LYC', 'SCUIO-IP')
def highschool_student_record_form_manager(request, hs_record_id):
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
    from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm
    from immersionlyceens.apps.core.forms import HighSchoolStudentImmersionUserForm

    hs = HighSchoolStudentRecord.objects.get(id=hs_record_id)
    form = None

    if request.method == 'POST':
        form = HighSchoolStudentRecordManagerForm(request.POST, instance=hs)
        # record validation
        if form.is_valid():
            form.save()
            messages.success(request, _("High school student record modified"))

            user_data = {
                'first_name': request.POST.get('first_name'),
                'last_name': request.POST.get('last_name'),
            }
            user_form = HighSchoolStudentImmersionUserForm(user_data, instance=hs.student)

            # user validation
            if user_form.is_valid():
                user_form.save()
                messages.success(request, _("High school student user modified"))
                response = redirect('student_validation_global')
                response['location'] += f'?hs_id={request.POST.get("high_school_id")}'
                return response
            else:
                messages.error(request, _("High school student user modification failure"))
        else:
            messages.error(request, _("High school student record modification failure"))

    else:
        form = HighSchoolStudentRecordManagerForm(instance=hs)

    context = {
        'form': form,
        'record': hs,
    }
    return render(request, 'core/hs_record_manager.html', context)


@groups_required('REF-CMP')
def component(request, component_code=None):
    """
    Update component url and mailing list
    """
    form = None
    component = None
    components = None

    if request.method == "POST":
        try:
            component = Component.objects.get(code=request.POST.get('code'))
        except Exception:
            messages.error(request, _("Invalid parameter"))
            return redirect('component')

        form = ComponentForm(request.POST, instance=component)

        if form.is_valid():
            form.save()
            messages.success(request, _("Component settings successfully saved"))
            return redirect('component')
    elif component_code:
        try:
            component = Component.objects.get(code=component_code)
            form = ComponentForm(instance=component)
        except Component.DoesNotExist:
            messages.error(request, _("Invalid parameter"))
            return redirect('component')
    else:
        my_components = Component.objects.filter(referents=request.user).order_by('label')

        if my_components.count() == 1:
            component = my_components.first()
            form = ComponentForm(instance=component)
        else:
            components = [c for c in my_components]

    context = {
        'form': form,
        'component': component,
        'components': components,
    }

    return render(request, 'core/component.html', context)


@groups_required('REF-CMP', 'SCUIO-IP', 'REF-LYC',)
def stats(request):
    template = 'core/stats.html'
    components = None

    if request.user.is_scuio_ip_manager():
        components = Component.activated.all()
    elif request.user.is_component_manager():
        components = request.user.components.all()

    context = {
        'components': components,
    }

    if request.user.is_high_school_manager():
        context['high_school_id'] = request.user.highschool.id

    return render(request, template, context)


@login_required
@groups_required('SRV-JUR', 'SCUIO-IP')
def students_presence(request):
    """
    Displays a list of students registered to slots between min_date and max_date
    """
    slots = Slot.objects.filter(published=True).order_by('date', 'start_time')

    first_slot = slots.first()
    min_date = first_slot.date if first_slot else None

    last_slot = slots.last()
    max_date = last_slot.date if last_slot else None

    context = {
        'min_date': min_date.strftime("%Y-%m-%d"),
        'max_date': max_date.strftime("%Y-%m-%d"),
    }

    return render(request, 'core/students_presence.html', context)


@login_required
@groups_required('SCUIO-IP')
def duplicated_accounts(request):
    """
    Manage duplicated accounts
    """

    context = {
    }

    return render(request, 'core/duplicated_accounts.html', context)