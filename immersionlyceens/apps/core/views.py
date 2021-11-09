# pylint: disable=E1101
"""
Views file

pylint ignore:
- E1101: object has no member "XX". ignore because of models object query
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views import generic

import requests

from immersionlyceens.decorators import groups_required

from .forms import (StructureForm, ContactForm, CourseForm, MyHighSchoolForm, SlotForm,
    HighSchoolStudentImmersionUserForm, TrainingFormHighSchool, VisitForm)

from .admin_forms import ImmersionUserCreationForm, ImmersionUserChangeForm, TrainingForm

from .models import (Campus, CancelType, Structure, Course, HighSchool, Holiday, Immersion, ImmersionUser, Slot,
    Training, UniversityYear, Establishment, Visit)

logger = logging.getLogger(__name__)


@groups_required('REF-ETAB-MAITRE')
def import_holidays(request):
    """
    Import holidays from API if it has been configured
    """

    redirect_url = '/admin/core/holiday/'

    if all([
        settings.WITH_HOLIDAY_API,
        settings.HOLIDAY_API_URL,
        settings.HOLIDAY_API_MAP,
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
                    if year.start_date <= _date.date() <= year.end_date:
                        Holiday.objects.create(label=_label, date=_date)
                except ValueError as exc:
                    logger.error(str(exc))
                except IntegrityError as exc:
                    logger.warning(str(exc))

    return redirect(redirect_url)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def slots_list(request, str_id=None, train_id=None):
    """
    Get slots list
    get filters : structure and trainings
    """
    if request.user.is_high_school_manager() and request.user.highschool \
        and not request.user.highschool.postbac_immersion:
        return HttpResponseRedirect("/")

    template = 'core/slots_list.html'

    try:
        int(str_id)
    except (ValueError, TypeError):
        str_id = None

    try:
        int(train_id)
    except (ValueError, TypeError):
        train_id = None

    allowed_highschools = HighSchool.objects.none()
    allowed_establishments = Establishment.objects.none()
    allowed_strs = Structure.objects.none()

    if request.user.is_superuser or request.user.is_master_establishment_manager():
        allowed_highschools = HighSchool.agreed.filter(postbac_immersion=True)
        allowed_establishments = Establishment.activated.all()
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_establishment_manager():
        allowed_establishments = Establishment.objects.filter(pk=request.user.establishment.id)
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_structure_manager():
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_high_school_manager():
        allowed_highschools = HighSchool.objects.filter(pk=request.user.highschool.id)

    if allowed_establishments.count() == 1:
        establishment_id = allowed_establishments.first().id
    else:
        establishment_id = request.session.get("current_establishment_id", None)

    if request.user.is_high_school_manager() and allowed_highschools.count() == 1:
        highschool_id = allowed_highschools.first().id
    else:
        highschool_id = request.session.get("current_highschool_id", None)

    if str_id:
        structure_id = str_id
    elif allowed_strs.count() == 1:
        structure_id = allowed_strs.first().id
    else:
        structure_id = request.session.get("current_structure_id", None)

    contact_form = ContactForm()

    context = {
        'structures': allowed_strs.order_by('code'),
        "establishments": allowed_establishments,
        "highschools": allowed_highschools,
        'establishment_id': establishment_id,
        'structure_id': structure_id,
        'highschool_id': highschool_id,
        'training_id': None,
        'trainings': [],
        'contact_form': contact_form,
        'cancel_types': CancelType.objects.filter(active=True),
    }

    if structure_id:
        # Make sure the training is active and belongs to the selected structure
        if train_id and Training.objects.filter(id=train_id, structures=structure_id, active=True).exists():
            context['training_id'] = train_id

        trainings = Training.objects.prefetch_related('training_subdomains') \
                .filter(structures=structure_id, active=True) \
                .order_by('label')

        for training in trainings:
            context['trainings'].append({
                'id': training.id,
                'label': training.label,
                'subdomain': [s.label for s in training.training_subdomains.filter(active=True)],
            })

    return render(request, template, context=context)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def slot(request, slot_id=None, duplicate=False):
    slot = None
    speakers_idx = None

    if slot_id:
        try:
            slot = Slot.objects.get(id=slot_id)
            speakers_idx = [t.id for t in slot.speakers.all()]

            if duplicate:
                slot.id = None

            update_conditions = [
                slot.course.structure and slot.course.structure in request.user.get_authorized_structures(),
                slot.course.highschool and slot.course.highschool == request.user.highschool
            ]

            if not any(update_conditions):
                messages.error(request, _("This slot belongs to another structure"))
                return redirect('/core/slots/')

        except Slot.DoesNotExist:  # id not found : make an empty slot
            messages.warning(request, _("This slot id does not exist"))
            return redirect('/core/slots/')

    structures = request.user.get_authorized_structures().order_by('code')

    if request.method == 'POST' and any(
        [request.POST.get('save'), request.POST.get('duplicate'), request.POST.get('save_add')]
    ):
        slot_form = SlotForm(request.POST, instance=slot, request=request)
        speakers = []
        speaker_prefix = 'speaker_'
        for speaker_id in [e.replace(speaker_prefix, '') for e in request.POST if speaker_prefix in e]:
            speakers.append(speaker_id)

        # if published, speakers count must be > 0
        # else no speaker needed
        published = request.POST.get('published') == 'on'

        if slot_form.is_valid() and (not published or len(speakers) > 0):
            new_slot = slot_form.save()
            for speaker in speakers:
                new_slot.speakers.add(speaker)

            if duplicate or not slot:
                messages.success(request, _("Slot successfully added"))
            elif slot and slot.id:
                messages.success(request, _("Slot successfully updated"))

            if published:
                course = Course.objects.get(id=request.POST.get('course'))
                if course and course.published:
                    messages.success(request, _("Course published"))
        else:
            context = {
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "course": Course.objects.get(id=request.POST.get('course', None)),
                "structures": structures,
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "speaker_error": len(speakers) < 1,
                "speakers_idx": [int(t) for t in speakers],
            }
            return render(request, 'core/slot.html', context=context)

        # Student notification on slot update
        if request.POST.get('notify_student') == 'on':
            sent_msg = 0
            immersions = Immersion.objects.filter(slot=slot, cancellation_type__isnull=True)
            for immersion in immersions:
                if not immersion.student.send_message(request, 'CRENEAU_MODIFY_NOTIF', immersion=immersion,
                                                      slot=slot):
                    sent_msg += 1

            if sent_msg:
                messages.success(request, _("Notifications have been sent (%s)") % sent_msg)

        if request.POST.get('save'):
            structure = new_slot.course.structure if new_slot.course.structure else None
            highschool = new_slot.course.highschool if new_slot.course.highschool else None

            request.session["current_structure_id"] = structure.id if structure else None
            request.session["current_establishment_id"] = structure.establishment.id if structure else None
            request.session["current_highschool_id"] = highschool.id if highschool else None

            return HttpResponseRedirect(reverse('slots_list'))
        elif request.POST.get('save_add'):
            return redirect('slot')
        elif request.POST.get('duplicate'):
            return redirect('duplicate_slot', slot_id=slot_form.instance.id, duplicate=1)
        else:
            return redirect('/')
    elif slot:
        slot_form = SlotForm(instance=slot, request=request)
    else:
        slot_form = SlotForm(request=request)

    context = {
        "campus": Campus.objects.filter(active=True).order_by('label'),
        "slot_form": slot_form,
        "ready_load": True,
    }
    if slot:
        context['slot'] = slot
        context['course'] = slot.course
        context['speakers_idx'] = speakers_idx

    return render(request, 'core/slot.html', context=context)

"""
@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def add_slot(request, slot_id=None):
    slot = None
    speakers_idx = None

    if slot_id:
        try:
            slot = Slot.objects.get(id=slot_id)
            speakers_idx = [t.id for t in slot.speakers.all()]
            slot.id = None
        except Slot.DoesNotExist:  # id not found : make an empty slot
            slot = Slot()
            speakers_idx = []

    # get structures
    structures = []
    if request.user.is_superuser or request.user.is_establishment_manager():
        structures = Structure.activated.all().order_by('code')
    elif request.user.is_structure_manager():
        structures = request.user.structures.all().order_by('code')

    if request.method == 'POST' and any(
        [request.POST.get('save'), request.POST.get('duplicate'), request.POST.get('save_add')]
    ):
        slot_form = SlotForm(request.POST, instance=slot)
        speakers = []
        speaker_prefix = 'speaker_'
        for speaker_id in [e.replace(speaker_prefix, '') for e in request.POST if speaker_prefix in e]:
            speakers.append(speaker_id)

        # if published, speakers count must be > 0
        # else no speaker needed
        published = request.POST.get('published') == 'on'
        if slot_form.is_valid() and (not published or len(speakers) > 0):
            slot_form.save()
            for speaker in speakers:
                slot_form.instance.speakers.add(speaker)
            messages.success(request, _("Slot successfully added"))

            if published:
                course = Course.objects.get(id=request.POST.get('course'))
                if course and course.published:
                    messages.success(request, _("Course published"))
        else:
            context = {
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "course": Course.objects.get(id=request.POST.get('course', None)),
                "structures": structures,
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "speaker_error": len(speakers) < 1,
                "speakers_idx": [int(t) for t in speakers],
            }
            return render(request, 'slots/add_slot.html', context=context)

        if request.POST.get('save'):
            return HttpResponseRedirect(
                reverse(
                    'slots_list',
                    kwargs={
                        'str_id': request.POST.get('structure', ''),
                        'train_id': request.POST.get('training', '')
                    }
                )
            )
        elif request.POST.get('save_add'):
            return redirect('slot')
        elif request.POST.get('duplicate'):
            return redirect('duplicate_slot', slot_id=slot_form.instance.id)
        else:
            return redirect('/')
    elif slot:
        slot_form = SlotForm(instance=slot)
    else:
        slot_form = SlotForm()

    context = {
        "structures": structures,
        "campus": Campus.objects.filter(active=True).order_by('label'),
        "slot_form": slot_form,
        "ready_load": True,
    }
    if slot:
        context['slot'] = slot
        context['course'] = slot.course
        context['speakers_idx'] = speakers_idx

    return render(request, 'slots/add_slot.html', context=context)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE')
def modify_slot(request, slot_id):
    # Update a slot

    try:
        slot = Slot.objects.get(id=slot_id)
    except Slot.DoesNotExist:
        messages.warning(request, _("This slot id does not exist"))
        return redirect('/core/slots/')

    # Check whether the user has access to this slot
    if request.user.is_structure_manager() and slot.course.structure not in request.user.structures.all():
        messages.error(request, _("This slot belongs to another structure"))
        return redirect('/core/slots/')

    slot_form = SlotForm(instance=slot, request=request)
    # get structures
    structures = []
    if request.user.is_superuser or request.user.is_establishment_manager():
        structures = Structure.activated.all().order_by('code')
    elif request.user.is_structure_manager():
        structures = request.user.structures.all().order_by('code')

    if request.method == 'POST' and any(
        [request.POST.get('save'), request.POST.get('duplicate'), request.POST.get('save_add')]
    ):
        slot_form = SlotForm(request.POST, instance=slot, request=request)
        speakers = []
        speaker_prefix = 'speaker_'
        for speaker_id in [e.replace(speaker_prefix, '') for e in request.POST if speaker_prefix in e]:
            speakers.append(speaker_id)

        published = request.POST.get('published') == 'on'
        notify_student = request.POST.get('notify_student') == 'on'
        if slot_form.is_valid() and (not published or len(speakers) > 0):
            slot_form.save()
            slot_form.instance.speakers.clear()
            for speaker in speakers:
                slot_form.instance.speakers.add(speaker)
            messages.success(request, _("Slot successfully updated"))
        else:
            context = {
                "slot": slot,
                "structures": structures,
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "trainings": Training.objects.filter(active=True),
                "slot_form": slot_form,
                "ready_load": True,
                "errors": slot_form.errors,
                "speaker_error": len(speakers) < 1,
                "speakers_idx": [int(t) for t in speakers],
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
                messages.success(request, _("Notifications have been sent (%s)") % sent_msg)

        if request.POST.get('save'):
            return HttpResponseRedirect(
                reverse(
                    'slots_list',
                    kwargs={
                        'str_id': request.POST.get('structure', ''),
                        'train_id': request.POST.get('training', '')
                    }
                )
            )
        elif request.POST.get('save_add'):
            return redirect('add_slot')
        elif request.POST.get('duplicate'):
            return redirect('duplicate_slot', slot_id=slot_form.instance.id)
        else:
            context = {
                "slot": slot,
                "course": Course.objects.get(id=request.POST.get('course', None)),
                "structures": structures,
                "campus": Campus.objects.filter(active=True).order_by('label'),
                "trainings": Training.objects.filter(active=True).order_by('label'),
                "slot_form": slot_form,
                "ready_load": True,
                "speakers_idx": [t.id for t in slot.speakers.all()],
            }
            return render(request, 'slots/add_slot.html', context=context)

    context = {
        "slot": slot,
        "structures": structures,
        "campus": Campus.objects.filter(active=True).order_by('label'),
        "trainings": Training.objects.filter(active=True),
        "slot_form": slot_form,
        "ready_load": True,
        "speakers_idx": [t.id for t in slot.speakers.all()],
    }
    return render(request, 'slots/add_slot.html', context=context)
"""

@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def del_slot(request, slot_id):
    try:
        slot = Slot.objects.get(id=slot_id)
        # Check whether the user has access to this slot
        if request.user.is_structure_manager() and slot.course.structure not in request.user.structures.all():
            return HttpResponse(gettext("This slot belongs to another structure"))
        slot.delete()
    except Slot.DoesNotExist:
        pass

    return HttpResponse('ok')


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-ETAB-MAITRE', 'REF-LYC')
def courses_list(request):
    if request.user.is_high_school_manager() and request.user.highschool \
        and not request.user.highschool.postbac_immersion:
        return HttpResponseRedirect("/")

    can_update_courses = False

    allowed_highschools = HighSchool.objects.none()
    allowed_establishments = Establishment.objects.none()
    allowed_strs = Structure.objects.none()

    if request.user.is_master_establishment_manager():
        allowed_highschools = HighSchool.agreed.filter(postbac_immersion=True)
        allowed_establishments = Establishment.activated.all()
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_establishment_manager():
        allowed_establishments = Establishment.objects.filter(pk=request.user.establishment.id)
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_structure_manager():
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_high_school_manager():
        allowed_highschools = HighSchool.objects.filter(pk=request.user.highschool.id)

    if allowed_establishments.count() == 1:
        establishment_id = allowed_establishments.first().id
    else:
        establishment_id = request.session.get("current_establishment_id", None)

    if request.user.is_high_school_manager() and allowed_highschools.count() == 1:
        highschool_id = allowed_highschools.first().id
    else:
        highschool_id = request.session.get("current_highschool_id", None)

    if allowed_strs.count() == 1:
        structure_id = allowed_strs.first().id
    else:
        structure_id = request.session.get("current_structure_id", None)

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
                """active university year has not begun yet (or is already over)."""
            ),
        )

    context = {
        "structures": allowed_strs.order_by('code'),
        "establishments": allowed_establishments,
        "highschools": allowed_highschools,
        "structure_id": structure_id,
        "establishment_id": establishment_id,
        "highschool_id": highschool_id,
        "can_update_courses": can_update_courses
    }

    return render(request, 'core/courses_list.html', context)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def course(request, course_id=None, duplicate=False):
    """
    Course creation / update / deletion
    """
    speakers_list = []
    save_method = None
    course = None
    course_form = None
    update_rights = True
    can_update_courses = False
    allowed_strs = request.user.get_authorized_structures().order_by('code', 'label')

    # Check if we can add/update courses
    try:
        active_year = UniversityYear.objects.get(active=True)
        can_update_courses = active_year.date_is_between(datetime.today().date())
    except UniversityYear.DoesNotExist:
        pass
    except UniversityYear.MultipleObjectsReturned:
        # Todo : do something here.
        pass

    if not can_update_courses:
        messages.warning(
            request,
            _(
                """Courses cannot be created, updated or deleted because the """
                """active university year has not begun yet (or is already over)."""
            ),
        )

    if course_id:
        try:
            course = Course.objects.get(pk=course_id)
            request.session["current_structure_id"] = course.structure.id if course.structure else None
            request.session["current_highschool_id"] = course.highschool.id if course.highschool else None
            request.session["current_establishment_id"] = \
                course.structure.establishment.id if course.structure else None

            speakers_list = [{
                "username": t.username,
                "lastname": t.last_name,
                "firstname": t.first_name,
                "email": t.email,
                "display_name": f"{t.last_name} {t.first_name}",
                "is_removable": not t.slots.filter(course=course_id).exists(),
            } for t in course.speakers.all()]

            if duplicate:
                data = {
                    'structure': course.structure,
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
        cannot_update_conditions = [
            not course,
            course and course.structure and not (course.get_structures_queryset() & allowed_strs).exists(),
            course and course.highschool and course.highschool != request.user.highschool
        ]

        if any(cannot_update_conditions):
            if request.method == 'POST':
                return HttpResponseRedirect("/core/courses_list")
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

        # speakers
        speakers_list = request.POST.get('speakers_list', "[]")

        try:
            speakers_list = json.loads(speakers_list)
            assert len(speakers_list) > 0
        except Exception:
            messages.error(request, _("At least one speaker is required"))
        else:
            if course_form.is_valid():
                new_course = course_form.save()

                request.session["current_structure_id"] = new_course.structure_id

                current_speakers = [u for u in new_course.speakers.all().values_list('username', flat=True)]
                new_speakers = [speaker.get('username') for speaker in speakers_list]

                # speakers to add
                for speaker in speakers_list:
                    if isinstance(speaker, dict):
                        try:
                            speaker_user = ImmersionUser.objects.get(username=speaker['username'])
                        except ImmersionUser.DoesNotExist:
                            establishment = new_course.structure.establishment if new_course.structure else None

                            speaker_user = ImmersionUser.objects.create(
                                username=speaker['username'],
                                last_name=speaker['lastname'],
                                first_name=speaker['firstname'],
                                email=speaker['email'],
                                establishment=establishment
                            )

                            messages.success(request, gettext("User '{}' created").format(speaker['username']))
                            return_msg = speaker_user.send_message(request, 'CPT_CREATE_INTER')

                            if not return_msg:
                                messages.success(
                                    request,
                                    gettext("A confirmation email has been sent to {}").format(speaker['email']),
                                )
                            else:
                                messages.warning(request, return_msg)

                        try:
                            Group.objects.get(name='INTER').user_set.add(speaker_user)
                        except Exception:
                            messages.error(
                                request, _("Couldn't add group 'INTER' to user '%s'" % speaker['username']),
                            )

                        if speaker_user:
                            new_course.speakers.add(speaker_user)

                # speakers to remove
                remove_list = set(current_speakers) - set(new_speakers)
                for username in remove_list:
                    try:
                        user = ImmersionUser.objects.get(username=username)
                        new_course.speakers.remove(user)
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
        "speakers": json.dumps(speakers_list),
        "update_rights": update_rights,
    }

    return render(request, 'core/course.html', context)


@groups_required('INTER',)
def mycourses(request):

    structure_id = None
    allowed_strs = request.user.get_authorized_structures().order_by('code', 'label')

    if allowed_strs.count() == 1:
        structure_id = allowed_strs.first().id

    context = {
        "structures": allowed_strs,
        "structure_id": structure_id
    }

    return render(request, 'core/mycourses.html', context)


@groups_required('INTER',)
def myslots(request):
    contact_form = ContactForm()

    context = {
        'contact_form': contact_form,
    }

    return render(request, 'core/myslots.html', context)


@groups_required('REF-LYC',)
def my_high_school(request, high_school_id=None):
    if request.user.highschool and request.user.highschool.id != high_school_id:
        return redirect('home')

    hs = HighSchool.objects.get(id=high_school_id)
    post_values = request.POST.copy()
    post_values['label'] = hs.label

    context = {
        'high_school': hs,
        'modified': False,
        'referents': ImmersionUser.objects.filter(
            highschool=request.user.highschool,
            groups__name__in=['REF-LYC', ]
        ),
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


@groups_required('REF-LYC',)
def my_high_school_speakers(request, high_school_id=None):
    """
    Display high school speakers (INTER group)
    """
    highschool = request.user.highschool

    if highschool and (highschool.id != high_school_id or not highschool.postbac_immersion):
        return redirect('home')

    context = {
        'high_school': highschool,
        'speakers': ImmersionUser.objects.filter(
            highschool=highschool,
            groups__name__in=['INTER', ]
        ),
    }

    return render(request, 'core/my_high_school_speakers.html', context)


@groups_required('REF-LYC',)
def speaker(request, id=None):
    """
    Speaker form for high school managers
    :param id: speaker to edit
    :return: speaker form
    """
    speaker = None
    initial = {}
    high_school = request.user.highschool
    speaker_id = id or request.POST.get("id")

    if not high_school:
        return redirect('home')

    if speaker_id:
        try:
            speaker = ImmersionUser.objects.get(pk=speaker_id)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Speaker not found"))
            return redirect(reverse('my_high_school_speakers', kwargs={'high_school_id': high_school.id}))
    else:
        initial = {
            'highschool': high_school,
            'is_active': True,
            'establishment': None
        }

    if request.method == 'POST':
        speaker_form = ImmersionUserCreationForm(request.POST, instance=speaker, initial=initial, request=request)
        if speaker_form.is_valid():
            new_speaker = speaker_form.save()
            Group.objects.get(name='INTER').user_set.add(new_speaker)

            if speaker:
                messages.success(request, _("Speaker successfully updated."))
                if 'email' in speaker_form.changed_data:
                    messages.warning(request, _("Warning : the username is now the new speaker's email address"))
            else:
                messages.success(request, _("Speaker successfully created."))
            return redirect(reverse('my_high_school_speakers', kwargs={'high_school_id': high_school.id}))
        else:
            messages.error(request, speaker_form.errors)
    else:
        speaker_form = ImmersionUserCreationForm(instance=speaker, initial=initial, request=request)

    context = {
        'high_school': high_school,
        'speaker_form': speaker_form,
        'speaker': speaker
    }

    return render(request, 'core/speaker.html', context)


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def my_students(request):
    highschool = None

    try:
        highschool = request.user.highschool
    except Exception:
        pass

    context = {
        'highschool': highschool,
        'is_establishment_manager': request.user.is_establishment_manager(),
    }

    return render(request, 'core/highschool_students.html', context)


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def student_validation(request, high_school_id=None):
    if request.user.is_high_school_manager() and request.user.highschool:
        try:
            high_school_id = request.user.highschool.id
        except AttributeError:
            messages.error(request, _("Your account is not bound to any high school"))
            return redirect('/')

    # student_validation
    context = {}

    if high_school_id:
        try:
            context['high_school'] = HighSchool.objects.get(id=high_school_id)
        except HighSchool.DoesNotExist:
            messages.error(request, _("This high school id does not exist"))
            return redirect('/core/student_validation/')
    else:
        context['high_schools'] = HighSchool.objects.all().order_by('city')

    try:
        context['hs_id'] = int(request.GET.get('hs_id'))
    except (ValueError, TypeError):
        pass

    return render(request, 'core/student_validation.html', context)


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE')
def highschool_student_record_form_manager(request, hs_record_id):
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
    from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm

    try:
        hs = HighSchoolStudentRecord.objects.get(id=hs_record_id)
    except HighSchoolStudentRecord.DoesNotExist:
        return redirect('/core/student_validation/')

    if request.user.is_high_school_manager() and request.user.highschool != hs.highschool:
        messages.error(request, _("This student is not in your high school"))
        return redirect('/core/student_validation/')

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


@groups_required('REF-STR')
def structure(request, structure_code=None):
    """
    Update structure url and mailing list
    """
    form = None
    structure = None
    structures = None

    if request.method == "POST":
        try:
            structure = Structure.objects.get(code=request.POST.get('code'))
        except Exception:
            messages.error(request, _("Invalid parameter"))
            return redirect('structure')

        form = StructureForm(request.POST, instance=structure)

        if form.is_valid():
            form.save()
            messages.success(request, _("Structure settings successfully saved"))
            return redirect('structure')
    elif structure_code:
        try:
            structure = Structure.objects.get(code=structure_code)
            form = StructureForm(instance=structure)
        except Structure.DoesNotExist:
            messages.error(request, _("Invalid parameter"))
            return redirect('structure')
    else:
        my_structures = Structure.objects.filter(referents=request.user).order_by('label')

        if my_structures.count() == 1:
            structure = my_structures.first()
            form = StructureForm(instance=structure)
        else:
            structures = [c for c in my_structures]

    context = {
        'form': form,
        'structure': structure,
        'structures': structures,
    }

    return render(request, 'core/structure.html', context)


@groups_required(
    'REF-STR', 'REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE'
)
def stats(request):
    template = 'core/stats.html'
    structures = None

    if request.user.is_establishment_manager():
        structures = Structure.activated.all()
    elif request.user.is_structure_manager():
        structures = request.user.structures.all()

    context = {
        'structures': structures,
    }

    if request.user.is_high_school_manager() and request.user.highschool:
        context['high_school_id'] = request.user.highschool.id

    return render(request, template, context)


@login_required
@groups_required('SRV-JUR', 'REF-ETAB', 'REF-ETAB-MAITRE')
def students_presence(request):
    """
    Displays a list of students registered to slots between min_date and max_date
    """
    slots = Slot.objects.filter(published=True).order_by('date', 'start_time')

    first_slot = slots.first()
    min_date = first_slot.date.strftime("%Y-%m-%d") if first_slot else None

    last_slot = slots.last()
    max_date = last_slot.date.strftime("%Y-%m-%d") if last_slot else None

    context = {
        'min_date': min_date,
        'max_date': max_date,
    }

    return render(request, 'core/students_presence.html', context)


@login_required
@groups_required('REF-ETAB', 'REF-ETAB-MAITRE')
def duplicated_accounts(request):
    """
    Manage duplicated accounts
    """

    context = {}

    return render(request, 'core/duplicated_accounts.html', context)


@method_decorator(groups_required('REF-LYC', 'REF-ETAB-MAITRE'), name="dispatch")
class TrainingList(generic.TemplateView):
    template_name = "core/training/list.html"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context["can_update"] = True
        if self.request.user.is_master_establishment_manager():
            context["highschools"] = HighSchool.objects.filter(postbac_immersion=True).order_by("city", "label")

        return context


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingAdd(generic.CreateView):
    form_class = TrainingFormHighSchool
    template_name: str = "core/training/training.html"

    def get_success_url(self) ->  str:
        return reverse("training_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self) -> Dict[str, Any]:
        kw: Dict[str, Any] = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        messages.success(self.request, _("Training %s created.") % str(form.instance))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Training not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingUpdate(generic.UpdateView):
    form_class = TrainingFormHighSchool
    template_name: str = "core/training/training.html"

    queryset = Training.objects.filter(highschool__isnull=False)

    def get_success_url(self) -> str:
        return reverse("training_list")

    def get_form_kwargs(self) -> Dict[str, Any]:
        kw: Dict[str, Any] = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        messages.success(self.request, _("Training \"%s\" updated.") % str(form.instance))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Training \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitList(generic.TemplateView):
    template_name = "core/visits_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe

        context["highschools"] = HighSchool.agreed.order_by("city", "label")
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)

        context["establishment_id"] = self.request.session.get('current_establishment_id', None)
        context["structure_id"] = self.request.session.get('current_structure_id', None)

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitAdd(generic.CreateView):
    form_class = VisitForm
    template_name = "core/visit.html"
    duplicate = False

    def get_success_url(self):
        if self.add_new:
            return reverse("add_visit")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_visit", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("visits")

    def get_context_data(self, *args, **kwargs):
        speakers_list = []
        context = super().get_context_data(**kwargs)
        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.duplicate and object_pk:
            try:
                visit = Visit.objects.get(pk=object_pk)
                self.form = VisitForm(instance=visit, request=self.request)

                speakers_list = [{
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": not t.slots.filter(visit=object_pk).exists(),
                } for t in visit.speakers.all()]

                visit.pk = None
                context["form"] = self.form
            except Visit.DoesNotExist:
                pass

        context["can_update"] = True  # FixMe
        context["speakers"] = json.dumps(speakers_list)
        context["establishment_id"] = self.request.session.get('current_establishment_id')
        context["structure_id"] = self.request.session.get('current_structure_id')
        return context


    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw


    def form_valid(self, form):
        self.duplicate = self.request.POST.get("save_duplicate", False) != False
        self.add_new = self.request.POST.get("save_add_new", False) != False
        response = super().form_valid(form)
        messages.success(self.request, _(f"Visit {form.instance} created."))
        return response


    def form_invalid(self, form):
        messages.error(self.request, _("Visit not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitUpdate(generic.UpdateView):
    model = Visit
    form_class = VisitForm
    template_name = "core/visit.html"

    queryset = Visit.objects.all()

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def get_context_data(self, **kwargs):
        speakers_list = []
        visit_id = self.object.id
        duplicate = kwargs.get("duplicate", False)
        if visit_id:
            try:
                visit = Visit.objects.get(pk=visit_id)
                self.request.session["current_structure_id"] = visit.structure.id if visit.structure else None
                self.request.session["current_highschool_id"] = visit.highschool.id
                self.request.session["current_establishment_id"] = visit.establishment.id

                speakers_list = [{
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True  # FixMe : not t.slots.filter(visit=visit_id).exists(),
                } for t in visit.speakers.all()]

                if duplicate:
                    data = {
                        'establishment': visit.establishment,
                        'structure': visit.structure,
                        'highschool': visit.highschool,
                        'published': visit.published,
                        'purpose': visit.purpose
                    }
                    visit = Visit(**data)

                self.form = VisitForm(instance=visit, request=self.request)

            except Course.DoesNotExist:
                self.form = VisitForm(request=self.request)

        context = super().get_context_data(**kwargs)
        context["can_update"] = True  # FixMe
        context["speakers"] = json.dumps(speakers_list)
        return context


    def get_success_url(self):
        return reverse("visits")

    def form_valid(self, form):
        messages.success(self.request, _("Visit \"%s\" updated.") % str(form.instance))

        self.request.session['current_establishment_id'] = self.object.establishment.id
        self.request.session['current_structure_id'] = self.object.structure.id if self.object.structure else None

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Visit \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)
