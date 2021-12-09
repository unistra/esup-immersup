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
from django.db.models import Q
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
    HighSchoolStudentImmersionUserForm, TrainingFormHighSchool, VisitForm, VisitSlotForm,
    OffOfferEventForm, OffOfferEventSlotForm)

from .admin_forms import ImmersionUserCreationForm, ImmersionUserChangeForm, TrainingForm

from .models import (Campus, CancelType, Structure, Course, HighSchool, Holiday, Immersion, ImmersionUser, Slot,
    Training, UniversityYear, Establishment, Visit, OffOfferEvent)

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
def slots_list(request, establishment_id=None, highschool_id=None, structure_id=None, training_id=None, course_id=None):
    """
    Get slots list
    get filters : structure and trainings
    """
    if request.user.is_high_school_manager() and request.user.highschool \
        and not request.user.highschool.postbac_immersion:
        return HttpResponseRedirect("/")

    template = 'core/slots_list.html'
    course_label_filter = ""

    try:
        int(establishment_id)
    except (ValueError, TypeError):
        establishment_id = None

    try:
        int(highschool_id)
    except (ValueError, TypeError):
        highschool_id = None

    try:
        int(structure_id)
    except (ValueError, TypeError):
        structure_id = None

    try:
        int(training_id)
    except (ValueError, TypeError):
        training_id = None

    try:
        course = Course.objects.get(pk=int(course_id))
        course_label_filter = course.label
    except (ValueError, TypeError, Course.DoesNotExist):
        course_id = None

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
        allowed_establishments = Establishment.objects.filter(pk=request.user.establishment.id)
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_high_school_manager():
        allowed_highschools = HighSchool.objects.filter(pk=request.user.highschool.id)

    if establishment_id and establishment_id not in allowed_establishments.values_list('pk', flat=True):
        establishment_id = None

    if not establishment_id:
        if allowed_establishments.count() == 1:
            establishment_id = allowed_establishments.first().id
        else:
            establishment_id = request.session.get("current_establishment_id", None)

    if highschool_id and highschool_id not in allowed_highschools.values_list('pk', flat=True):
        highschool_id = None

    if not highschool_id:
        if request.user.is_high_school_manager() and allowed_highschools.count() == 1:
            highschool_id = allowed_highschools.first().id
        else:
            highschool_id = request.session.get("current_highschool_id", None)

    if structure_id and structure_id not in allowed_strs.values_list('pk', flat=True):
        structure_id = None

    if not structure_id:
        if allowed_strs.count() == 1:
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
        'training_id': training_id or request.session.get("current_training_id", None),
        'course_id': course_id,
        'course_label_filter': course_label_filter,
        'trainings': [],
        'contact_form': contact_form,
        'cancel_types': CancelType.objects.filter(active=True),
    }

    if structure_id:
        # Make sure the training is active and belongs to the selected structure
        if training_id and Training.objects.filter(id=training_id, structures=structure_id, active=True).exists():
            context['training_id'] = training_id

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
def slot(request, slot_id=None, duplicate=False, establishment_id=None, highschool_id=None, structure_id=None,
         training_id=None, course_id=None):
    slot = None
    speakers_idx = None
    allowed_establishments = None
    allowed_highschools = None

    if slot_id:
        try:
            slot = Slot.objects.get(id=slot_id)
            speakers_idx = [t.id for t in slot.speakers.all()]

            allowed_establishments = [e.id for e in slot.allowed_establishments.all()]
            allowed_highschools = [h.id for h in slot.allowed_highschools.all()]

            if duplicate:
                slot.id = None

            update_conditions = [
                request.user.is_master_establishment_manager(),
                slot.course.structure and slot.course.structure in request.user.get_authorized_structures(),
                slot.course.highschool and slot.course.highschool == request.user.highschool
            ]

            if not any(update_conditions):
                messages.error(request, _("This slot belongs to another structure"))
                return redirect('/core/slots/')

            request.session["current_structure_id"] = \
                slot.course.structure.id if slot.course and slot.course.structure else None
            request.session["current_highschool_id"] = \
                slot.course.highschool.id if slot.course and slot.course.highschool else None
            request.session["current_establishment_id"] = \
                slot.course.structure.establishment.id if slot.course and slot.course.structure else None
            request.session["current_training_id"] = \
                slot.course.training.id if slot.course and slot.course.training else None

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

            # Update session variables
            request.session["current_structure_id"] = \
                new_slot.course.structure.id if new_slot.course and new_slot.course.structure else None
            request.session["current_highschool_id"] = \
                new_slot.course.highschool.id if new_slot.course and new_slot.course.highschool else None
            request.session["current_establishment_id"] = \
                new_slot.course.structure.establishment.id if new_slot.course and new_slot.course.structure else None
            request.session["current_training_id"] = \
                new_slot.course.training.id if new_slot.course and new_slot.course.training else None

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
        initials = {
            'allowed_establishments': allowed_establishments,
            'allowed_highschools': allowed_highschools
        }
        slot_form = SlotForm(instance=slot, initial=initials, request=request)
    else:
        slot_form = SlotForm(request=request)

    context = {
        "establishment_id": establishment_id,
        "highschool_id": highschool_id,
        "structure_id": structure_id,
        "training_id": training_id,
        "course_id": course_id,
        "slot_form": slot_form,
        "ready_load": True,
    }

    if slot:
        context['slot'] = slot
        context['course'] = slot.course
        context['speakers_idx'] = speakers_idx
        context['allowed_establishments'] = allowed_establishments
        context['allowed_highschools'] = allowed_highschools

    return render(request, 'core/slot.html', context=context)


@groups_required('REF-ETAB', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def del_slot(request, slot_id):
    try:
        slot = Slot.objects.get(id=slot_id)
        # Check whether the user has access to this slot
        if request.user.is_structure_manager():
            conditions = [
                slot.course and slot.course.structure not in request.user.structures.all(),
                slot.visit and slot.visit.structure not in request.user.structures.all()
            ]
            if any(conditions):
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
                    'highschool': course.highschool,
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
            request.user.is_high_school_manager() and course and course.highschool
                and course.highschool != request.user.highschool,
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

                request.session["current_structure_id"] = new_course.structure.id if new_course.structure else None
                request.session["current_highschool_id"] = new_course.highschool.id if new_course.highschool else None
                request.session["current_establishment_id"] = \
                    new_course.structure.establishment.id if new_course.structure else None

                current_speakers = [u for u in new_course.speakers.all().values_list('username', flat=True)]
                new_speakers = [speaker.get('username') for speaker in speakers_list]

                # speakers to add
                for speaker in speakers_list:
                    if isinstance(speaker, dict):
                        try:
                            speaker_user = ImmersionUser.objects.get(
                                Q(username=speaker['username']) | Q(email=speaker['email'])
                            )
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

    return render(request, 'core/my_courses.html', context)


@groups_required('INTER',)
def myvisits(request):

    structure_id = None
    allowed_strs = request.user.get_authorized_structures().order_by('code', 'label')

    if allowed_strs.count() == 1:
        structure_id = allowed_strs.first().id

    context = {
        "structures": allowed_strs,
        "structure_id": structure_id
    }

    return render(request, 'core/my_visits.html', context)


@groups_required('INTER',)
def myevents(request):

    structure_id = None
    allowed_strs = request.user.get_authorized_structures().order_by('code', 'label')

    if allowed_strs.count() == 1:
        structure_id = allowed_strs.first().id

    context = {
        "structures": allowed_strs,
        "structure_id": structure_id
    }

    return render(request, 'core/my_events.html', context)


@groups_required('INTER',)
def myslots(request, slots_type=None):
    contact_form = ContactForm()

    context = {
        'contact_form': contact_form,
    }

    if slots_type == "visits":
        return render(request, 'core/my_visits_slots.html', context)
    elif slots_type == "events":
        return render(request, 'core/my_events_slots.html', context)
    elif slots_type == "courses":
        return render(request, 'core/my_courses_slots.html', context)


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




@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class CourseSlotList(generic.TemplateView):
    template_name = "core/courses_slots_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe
        context["slot_mode"] = "course"

        # Defaults
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()
        context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True).order_by('city', 'label')

        context["establishment_id"] = \
            kwargs.get('establishment_id', None) or self.request.session.get('current_establishment_id', None)

        context["structure_id"] = \
            kwargs.get('structure_id', None) or self.request.session.get('current_structure_id', None)

        context["highschool_id"] = \
            kwargs.get('highschool_id', None) or self.request.session.get('current_highschool_id', None)

        context["training_id"] = \
            kwargs.get('training_id', None) or self.request.session.get('current_training_id', None)

        context["course_id"] = kwargs.get('course_id', None)

        if context["course_id"]:
            try:
                course = Course.objects.get(pk=context["course_id"])
                context["course_label_filter"] = course.label
            except Course.DoesNotExist:
                pass

        if context["training_id"]:
            try:
                training = Training.objects.get(pk=context["training_id"])
                context["training_id"] = training.id
            except Training.DoesNotExist:
                pass

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id
                context["structure_id"] = context["structure_id"] or self.request.user.structures.first().id

            if self.request.user.is_high_school_manager():
                context["establishments"] = Establishment.objects.none()
                context["structures"] = Structure.objects.none()
                context["highschools"] = HighSchool.agreed.filter(
                    postbac_immersion=True, pk=self.request.user.highschool.id
                )
                context["highschool_id"] = self.request.user.highschool.id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class CourseSlotAdd(generic.CreateView):
    form_class = SlotForm
    template_name = "core/course_slot.html"
    duplicate = False

    def get_success_url(self):
        self.request.session['current_establishment_id'] = \
            self.object.course.structure.establishment.id if self.object.course.structure else None
        self.request.session['current_structure_id'] = \
            self.object.course.structure.id if self.object.course.structure else None
        self.request.session['current_training_id'] = \
            self.object.course.training.id if self.object.course.training else None
        self.request.session['current_highschool_id'] = \
            self.object.course.highschool.id if self.object.course.highschool else None

        if self.add_new:
            return reverse("add_course_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_course_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("courses_slots")


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        speakers_list = [{"id": id} for id in self.request.POST.getlist("speakers_list", []) or []]
        context["speakers"] = json.dumps(speakers_list)
        course = None
        training = None

        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.kwargs.get('course_id', None):
            context["establishment_id"] = self.kwargs.get('establishment_id', None)
            context["structure_id"] = self.kwargs.get('structure_id', None)
            context["highschool_id"] = self.kwargs.get('highschool_id', None)
            context["course_id"] = self.kwargs.get('course_id')
            context["training_id"] = self.kwargs.get('training_id')

            try:
                course = Course.objects.get(pk=context["course_id"])
            except Course.DoesNotExist:
                pass

            try:
                training = Training.objects.get(pk=context["training_id"])
            except Training.DoesNotExist:
                pass
        else:
            context["establishment_id"] = self.request.session.get('current_establishment_id', None)
            context["structure_id"] = self.request.session.get('current_structure_id', None)
            context["highschool_id"] = self.request.session.get('current_highschool_id', None)
            context["tranining_id"] = self.request.session.get('current_training_id', None)

        if self.duplicate and object_pk:
            context = {'duplicate': True}
            try:
                slot = Slot.objects.get(pk=object_pk)

                establishment_id = slot.course.structure.establishment.id if slot.course.structure else None
                structure_id = slot.course.structure.id if slot.course.structure else None
                highschool_id = slot.course.highschool.id if slot.course.highschool else None

                initials = {
                    'establishment': establishment_id,
                    'structure': structure_id,
                    'highschool': highschool_id,
                    'course': slot.course.id,
                    'course_type': slot.course_type.id,
                    'campus': slot.campus,
                    'building': slot.building,
                    'published': slot.published,
                    'room': slot.room,
                    'url': slot.url,
                    'date': slot.date,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                    'n_places': slot.n_places,
                    'additional_information': slot.additional_information,
                    'face_to_face': slot.face_to_face,
                    'establishments_restrictions': slot.establishments_restrictions,
                    'levels_restrictions': slot.levels_restrictions,
                    'allowed_establishments': [e.id for e in slot.allowed_establishments.all()],
                    'allowed_highschools': [h.id for h in slot.allowed_highschools.all()],
                    'allowed_highschool_levels': slot.allowed_highschool_levels,
                    'allowed_student_levels': slot.allowed_student_levels,
                    'allowed_post_bachelor_levels': slot.allowed_post_bachelor_levels,
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    # careful, some fields are lists
                    if k in ['allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels',
                             'allowed_student_levels', 'allowed_post_bachelor_levels']:
                        initials[k] = data.getlist(k, initials[k])
                    else:
                        initials[k] = data.get(k, initials[k])

                self.form = self.form_class(initial=initials, request=self.request)

                speakers_list = [{ "id": t.id } for t in slot.speakers.all()]
                context["speakers"] = json.dumps(speakers_list)

                context["origin_id"] = slot.id
                context["form"] = self.form
            except Slot.DoesNotExist:
                pass
        elif not self.request.POST and course and training:
            initials = {
                'establishment': context.get("establishment_id", None),
                'structure': context.get("structure_id", None),
                'highschool': context.get("highschool_id", None),
                'training': training,
                'course': course,
            }

            self.form = self.form_class(initial=initials, request=self.request)
            context["form"] = self.form

        context["can_update"] = True  # FixMe
        context["slot_mode"] = "course"
        context["establishment_id"] = self.request.session.get('current_establishment_id')
        context["structure_id"] = self.request.session.get('current_structure_id')
        context["highschool_id"] = self.request.session.get('current_highschool_id')
        context["training_id"] = self.request.session.get('current_training_id')

        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False
        messages.success(self.request, _("Course slot %s created.") % form.instance)
        return super().form_valid(form)

    def form_invalid(self, form):
        for k, error in form.errors.items():
            messages.error(self.request, error)
        messages.error(self.request, _("Course slot not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class CourseSlotUpdate(generic.UpdateView):
    model = Slot
    form_class = SlotForm
    template_name = "core/course_slot.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager():
            return Slot.objects.filter(course__isnull=False)

        if user.is_establishment_manager():
            return Slot.objects.filter(course__establishment=user.establishment)

        if user.is_high_school_manager():
            return Slot.objects.filter(course__highschool=user.highschool)

        if user.is_structure_manager():
            return Slot.objects.filter(course__structure__in=user.get_authorized_structures())


    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = json.dumps(self.request.POST.getlist("speakers_list", []) or [])

        slot_id = self.object.id
        if slot_id:
            try:
                slot = Slot.objects.get(pk=slot_id)
                self.request.session["current_structure_id"] = \
                    slot.course.structure.id if slot.course.structure else None
                self.request.session["current_highschool_id"] = \
                    slot.course.highschool.id if slot.course.highschool else None
                self.request.session["current_establishment_id"] = \
                    slot.course.structure.establishment.id if slot.course.structure else None
                self.request.session["current_training_id"] = \
                    slot.course.training.id if slot.course.training else None

                speakers_list = [{
                    "id": t.id,
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True,
                } for t in slot.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                self.form = self.form_class(instance=slot, request=self.request)
            except Slot.DoesNotExist:
                self.form = self.form_class(request=self.request)

        context["slot_mode"] = "course"
        context["can_update"] = True  # FixMe
        return context


    def get_success_url(self):
        if self.add_new:
            return reverse("add_course_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_course_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("courses_slots")


    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False

        messages.success(self.request, _("Course slot \"%s\" updated.") % form.instance)

        self.request.session["current_structure_id"] = \
            self.object.course.structure.id if self.object.course.structure else None
        self.request.session["current_highschool_id"] = \
            self.object.course.highschool.id if self.object.course.highschool else None
        self.request.session["current_establishment_id"] = \
            self.object.course.structure.establishment.id if self.object.course.structure else None
        self.request.session["current_training_id"] = \
            self.object.course.training.id if self.object.course.training else None

        return super().form_valid(form)


    def form_invalid(self, form):
        messages.error(self.request, _("Course slot \"%s\" not updated.") % form.instance)
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

        context["establishment_id"] = self.request.session.get('current_establishment_id', None)
        context["structure_id"] = self.request.session.get('current_structure_id', None)

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                if self.request.user.structures.count() == 1:
                    context["structure_id"] = context["structure_id"] or self.request.user.structures.first().id

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
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = self.request.POST.get("speakers_list", "[]") or "[]"

        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.duplicate and object_pk:
            context = {'duplicate': True}
            try:
                visit = Visit.objects.get(pk=object_pk)

                initials = {
                    'establishment': visit.establishment.id,
                    'structure': visit.structure.id if visit.structure else None,
                    'highschool': visit.highschool.id,
                    'purpose': visit.purpose,
                    'published': visit.published
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    initials[k] = data.get(k, initials[k])

                self.form = VisitForm(initial=initials, request=self.request)

                speakers_list = [{
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True,
                } for t in visit.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                context["origin_id"] = visit.id
                context["form"] = self.form
            except Visit.DoesNotExist:
                pass

        context["can_update"] = True  # FixMe
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
        messages.success(self.request, _("Visit \"%s\" created.") % form.instance)
        return response


    def form_invalid(self, form):
        messages.error(self.request, _("Visit not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitUpdate(generic.UpdateView):
    model = Visit
    form_class = VisitForm
    template_name = "core/visit.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager():
            return Visit.objects.all()

        if user.is_establishment_manager():
            return Visit.objects.filter(establishment=user.establishment)

        if user.is_high_school_manager():
            return Visit.objects.filter(highschool=user.highschool)

        if user.is_structure_manager():
            return Visit.objects.filter(structure__in=user.get_authorized_structures())


    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = self.request.POST.get("speakers_list", "[]") or "[]"

        visit_id = self.object.id
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
                    "is_removable": not t.slots.filter(visit=visit_id).exists(),
                } for t in visit.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)

                self.form = VisitForm(instance=visit, request=self.request)
            except Visit.DoesNotExist:
                self.form = VisitForm(request=self.request)

        context["can_update"] = True  # FixMe
        return context


    def get_success_url(self):
        if self.add_new:
            return reverse("add_visit")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_visit", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("visits")

    def form_valid(self, form):
        messages.success(self.request, _("Visit \"%s\" updated.") % form.instance)

        self.request.session['current_establishment_id'] = self.object.establishment.id
        self.request.session['current_structure_id'] = self.object.structure.id if self.object.structure else None

        self.duplicate = self.request.POST.get("save_duplicate", False) != False
        self.add_new = self.request.POST.get("save_add_new", False) != False

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Visit \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitSlotList(generic.TemplateView):
    template_name = "core/visits_slots_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe
        context["slot_mode"] = "visit"

        # Defaults
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()
        context["establishment_id"] = \
            kwargs.get('establishment_id', None) or self.request.session.get('current_establishment_id', None)

        context["structure_id"] = \
            kwargs.get('structure_id', None) or self.request.session.get('current_structure_id', None)

        context["highschool_id"] = \
            kwargs.get('highschool_id', None) or self.request.session.get('current_highschool_id', None)

        context["visit_id"] = kwargs.get('visit_id', None)

        if context["visit_id"]:
            try:
                visit = Visit.objects.get(pk=context["visit_id"])
                context["visit_purpose_filter"] = visit.purpose
            except Visit.DoesNotExist:
                pass

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id
                context["structure_id"] = context["structure_id"] or self.request.user.structures.first().id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitSlotAdd(generic.CreateView):
    form_class = VisitSlotForm
    template_name = "core/visit_slot.html"
    duplicate = False

    def get_success_url(self):
        if self.add_new:
            return reverse("add_visit_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_visit_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("visits_slots")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        speakers_list = [{"id": id} for id in self.request.POST.getlist("speakers_list", []) or []]
        context["speakers"] = json.dumps(speakers_list)
        visit = None
        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.kwargs.get('visit_id', None):
            context["establishment_id"] = self.kwargs.get('establishment_id', None)
            context["structure_id"] = self.kwargs.get('structure_id', None)
            context["highschool_id"] = self.kwargs.get('highschool_id', None)
            context["visit_id"] = self.kwargs.get('visit_id')

            try:
                visit = Visit.objects.get(pk=context["visit_id"])
            except Visit.DoesNotExist:
                pass
        else:
            context["establishment_id"] = self.request.session.get('current_establishment_id', None)
            context["structure_id"] = self.request.session.get('current_structure_id', None)
            context["highschool_id"] = self.request.session.get('current_highschool_id', None)

        if self.duplicate and object_pk:
            context['duplicate'] = True
            try:
                slot = Slot.objects.get(pk=object_pk)

                initials = {
                    'establishment': slot.visit.establishment.id,
                    'structure': slot.visit.structure.id if slot.visit.structure else None,
                    'highschool': slot.visit.highschool.id,
                    'purpose': slot.visit.purpose,
                    'published': slot.published,
                    'visit': slot.visit,
                    'room': slot.room,
                    'url': slot.url,
                    'date': slot.date,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                    'n_places': slot.n_places,
                    'additional_information': slot.additional_information,
                    'face_to_face': slot.face_to_face,
                    'establishments_restrictions': False,
                    'levels_restrictions': slot.levels_restrictions,
                    'allowed_highschool_levels': slot.allowed_highschool_levels
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    # careful, some fields are lists
                    if k == 'allowed_highschool_levels':
                        initials[k] = data.getlist(k, initials[k])
                    else:
                        initials[k] = data.get(k, initials[k])

                self.form = VisitSlotForm(initial=initials, request=self.request)

                speakers_list = [{ "id": t.id } for t in slot.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                context["origin_id"] = slot.id
                context["form"] = self.form
            except Slot.DoesNotExist:
                pass
        elif not self.request.POST and visit:
            initials = {
                'establishment': context.get("establishment_id", None),
                'structure': context.get("structure_id", None),
                'highschool': context.get("highschool_id", None),
                'visit': visit,
            }

            self.form = VisitSlotForm(initial=initials, request=self.request)
            context["form"] = self.form

        context["can_update"] = True  # FixMe
        context["slot_mode"] = "visit"

        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False
        messages.success(self.request, _("Visit slot %s created.") % str(form.instance))
        return super().form_valid(form)

    def form_invalid(self, form):
        for k, error in form.errors.items():
            messages.error(self.request, error)
        messages.error(self.request, _("Visit slot not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR'), name="dispatch")
class VisitSlotUpdate(generic.UpdateView):
    model = Slot
    form_class = VisitSlotForm
    template_name = "core/visit_slot.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager():
            return Slot.objects.filter(visit__isnull=False)

        if user.is_establishment_manager():
            return Slot.objects.filter(visit__establishment=user.establishment)

        if user.is_high_school_manager():
            return Slot.objects.filter(visit__highschool=user.highschool)

        if user.is_structure_manager():
            return Slot.objects.filter(visit__structure__in=user.get_authorized_structures())

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = json.dumps(self.request.POST.getlist("speakers_list", []) or [])

        slot_id = self.object.id
        if slot_id:
            try:
                slot = Slot.objects.get(pk=slot_id)
                self.request.session["current_structure_id"] = slot.visit.structure.id if slot.visit.structure else None
                self.request.session["current_highschool_id"] = slot.visit.highschool.id
                self.request.session["current_establishment_id"] = slot.visit.establishment.id

                speakers_list = [{
                    "id": t.id,
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True,
                } for t in slot.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                self.form = VisitSlotForm(instance=slot, request=self.request)
            except Visit.DoesNotExist:
                self.form = VisitSlotForm(request=self.request)

        context["slot_mode"] = "visit"
        context["can_update"] = True  # FixMe
        return context


    def get_success_url(self):
        if self.add_new:
            return reverse("add_visit_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_visit_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("visits_slots")


    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False

        messages.success(self.request, _("Visit slot \"%s\" updated.") % form.instance)

        self.request.session['current_establishment_id'] = self.object.visit.establishment.id
        self.request.session['current_structure_id'] = \
            self.object.visit.structure.id if self.object.visit.structure else None

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Visit slot \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventsList(generic.TemplateView):
    template_name = "core/off_offer_events_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe

        context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True).order_by("city", "label")
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()

        context["establishment_id"] = self.request.session.get('current_establishment_id', None)
        context["structure_id"] = self.request.session.get('current_structure_id', None)
        context["highschool_id"] = self.request.session.get('current_highschool_id', None)

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = self.request.user.structures.all()
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_high_school_manager():
                context["establishments"] = Establishment.objects.none()
                context["structures"] = Structure.objects.none()
                context["highschools"] = HighSchool.agreed.filter(id=self.request.user.highschool.id)
                context["highschool_id"] = self.request.user.highschool.id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventAdd(generic.CreateView):
    form_class = OffOfferEventForm
    template_name = "core/off_offer_event.html"
    duplicate = False

    def get_success_url(self):
        if self.add_new:
            return reverse("add_off_offer_event")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_off_offer_event", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("off_offer_events")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = self.request.POST.get("speakers_list", "[]") or "[]"

        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.duplicate and object_pk:
            context = {'duplicate': True}
            try:
                event = OffOfferEvent.objects.get(pk=object_pk)

                initials = {
                    'establishment': event.establishment.id if event.establishment else None,
                    'structure': event.structure.id if event.structure else None,
                    'highschool': event.highschool.id if event.highschool else None,
                    'event_type': event.event_type.id,
                    'label': event.label,
                    'description': event.description,
                    'published': event.published
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    initials[k] = data.get(k, initials[k])

                self.form = OffOfferEventForm(initial=initials, request=self.request)

                speakers_list = [{
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True,
                } for t in event.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                context["origin_id"] = event.id
                context["form"] = self.form
            except OffOfferEvent.DoesNotExist:
                pass

        context["can_update"] = True  # FixMe
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
        messages.success(self.request, _("Off offer event \"%s\" created.") % form.instance)

        self.request.session['current_establishment_id'] = \
            self.object.establishment.id if self.object.establishment else None
        self.request.session['current_structure_id'] = self.object.structure.id if self.object.structure else None
        self.request.session['current_highschool_id'] = self.object.highschool.id if self.object.highschool else None

        return response


    def form_invalid(self, form):
        messages.error(self.request, _("Off offer event not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventUpdate(generic.UpdateView):
    model = OffOfferEvent
    form_class = OffOfferEventForm
    template_name = "core/off_offer_event.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager():
            return OffOfferEvent.objects.all()

        if user.is_establishment_manager():
            return OffOfferEvent.objects.filter(establishment=user.establishment)

        if user.is_high_school_manager():
            return OffOfferEvent.objects.filter(highschool=user.highschool)

        if user.is_structure_manager():
            return OffOfferEvent.objects.filter(structure__in=user.get_authorized_structures())

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = self.request.POST.get("speakers_list", "[]") or "[]"

        event_id = self.object.id

        if event_id:
            try:
                event = OffOfferEvent.objects.get(pk=event_id)
                self.request.session["current_structure_id"] = event.structure.id if event.structure else None
                self.request.session["current_highschool_id"] = event.highschool.id if event.highschool else None
                self.request.session["current_establishment_id"] = \
                    event.establishment.id if event.establishment else None

                speakers_list = [{
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": not t.slots.filter(event=event_id).exists(),
                } for t in event.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                self.form = OffOfferEventForm(instance=event, request=self.request)
            except OffOfferEvent.DoesNotExist:
                self.form = OffOfferEventForm(request=self.request)

        context["can_update"] = True  # FixMe
        return context


    def get_success_url(self):
        if self.add_new:
            return reverse("add_off_offer_event")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_off_offer_event", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("off_offer_events")

    def form_valid(self, form):
        messages.success(self.request, _("Off offer event \"%s\" updated.") % form.instance)

        self.request.session['current_establishment_id'] = \
            self.object.establishment.id if self.object.establishment else None
        self.request.session['current_structure_id'] = self.object.structure.id if self.object.structure else None
        self.request.session['current_highschool_id'] = self.object.highschool.id if self.object.highschool else None

        self.duplicate = self.request.POST.get("save_duplicate", False) != False
        self.add_new = self.request.POST.get("save_add_new", False) != False

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Off offer event \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventSlotList(generic.TemplateView):
    template_name = "core/off_offer_events_slots_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe
        context["slot_mode"] = "event"

        # Defaults
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()
        context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True).order_by('city', 'label')

        context["establishment_id"] = \
            kwargs.get('establishment_id', None) or self.request.session.get('current_establishment_id', None)

        context["structure_id"] = \
            kwargs.get('structure_id', None) or self.request.session.get('current_structure_id', None)

        context["highschool_id"] = \
            kwargs.get('highschool_id', None) or self.request.session.get('current_highschool_id', None)

        context["event_id"] = kwargs.get('event_id', None)

        if context["event_id"]:
            try:
                event = OffOfferEvent.objects.get(pk=context["event_id"])
                context["event_type_filter"] = event.event_type.label
            except OffOfferEvent.DoesNotExist:
                pass

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id
                context["structure_id"] = context["structure_id"] or self.request.user.structures.first().id

            if self.request.user.is_high_school_manager():
                context["establishments"] = Establishment.objects.none()
                context["structures"] = Structure.objects.none()
                context["highschools"] = HighSchool.agreed.filter(
                    postbac_immersion=True, pk=self.request.user.highschool.id
                )
                context["highschool_id"] = self.request.user.highschool.id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventSlotAdd(generic.CreateView):
    form_class = OffOfferEventSlotForm
    template_name = "core/off_offer_event_slot.html"
    duplicate = False

    def get_success_url(self):
        self.request.session['current_establishment_id'] = \
            self.object.event.establishment.id if self.object.event.establishment else None
        self.request.session['current_structure_id'] = \
            self.object.event.structure.id if self.object.event.structure else None
        self.request.session['current_highschool_id'] = \
            self.object.event.highschool.id if self.object.event.highschool else None

        if self.add_new:
            return reverse("add_off_offer_event_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_off_offer_event_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("off_offer_events_slots")


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        speakers_list = [{"id": id} for id in self.request.POST.getlist("speakers_list", []) or []]
        context["speakers"] = json.dumps(speakers_list)
        event = None

        self.duplicate = self.kwargs.get('duplicate', False)
        object_pk = self.kwargs.get('pk', None)

        if self.kwargs.get('event_id', None):
            context["establishment_id"] = self.kwargs.get('establishment_id', None)
            context["structure_id"] = self.kwargs.get('structure_id', None)
            context["highschool_id"] = self.kwargs.get('highschool_id', None)
            context["event_id"] = self.kwargs.get('event_id')

            try:
                event = OffOfferEvent.objects.get(pk=context["event_id"])
            except OffOfferEvent.DoesNotExist:
                pass
        else:
            context["establishment_id"] = self.request.session.get('current_establishment_id', None)
            context["structure_id"] = self.request.session.get('current_structure_id', None)
            context["highschool_id"] = self.request.session.get('current_highschool_id', None)

        if self.duplicate and object_pk:
            context = {'duplicate': True}
            try:
                slot = Slot.objects.get(pk=object_pk)

                initials = {
                    'establishment': slot.event.establishment.id if slot.event.establishment else None,
                    'structure': slot.event.structure.id if slot.event.structure else None,
                    'highschool': slot.event.highschool.id if slot.event.highschool else None,
                    'event_type': slot.event.event_type.id,
                    'campus': slot.campus,
                    'building': slot.building,
                    'label': slot.event.label,
                    'published': slot.published,
                    'event': slot.event,
                    'room': slot.room,
                    'url': slot.url,
                    'date': slot.date,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                    'n_places': slot.n_places,
                    'additional_information': slot.additional_information,
                    'face_to_face': slot.face_to_face,
                    'establishments_restrictions': slot.establishments_restrictions,
                    'levels_restrictions': slot.levels_restrictions,
                    'allowed_establishments': [e.id for e in slot.allowed_establishments.all()],
                    'allowed_highschools': [h.id for h in slot.allowed_highschools.all()],
                    'allowed_highschool_levels': slot.allowed_highschool_levels,
                    'allowed_student_levels': slot.allowed_student_levels,
                    'allowed_post_bachelor_levels': slot.allowed_post_bachelor_levels,
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    # careful, some fields are lists
                    if k in ['allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels',
                             'allowed_student_levels', 'allowed_post_bachelor_levels']:
                        initials[k] = data.getlist(k, initials[k])
                    else:
                        initials[k] = data.get(k, initials[k])

                self.form = OffOfferEventSlotForm(initial=initials, request=self.request)

                speakers_list = [{ "id": t.id } for t in slot.speakers.all()]
                context["speakers"] = json.dumps(speakers_list)

                context["origin_id"] = slot.id
                context["form"] = self.form
            except Slot.DoesNotExist:
                pass
        elif not self.request.POST and event:
            initials = {
                'establishment': context.get("establishment_id", None),
                'structure': context.get("structure_id", None),
                'highschool': context.get("highschool_id", None),
                'event': event,
            }

            self.form = OffOfferEventSlotForm(initial=initials, request=self.request)
            context["form"] = self.form

        context["can_update"] = True  # FixMe
        context["slot_mode"] = "event"
        context["establishment_id"] = self.request.session.get('current_establishment_id')
        context["structure_id"] = self.request.session.get('current_structure_id')
        context["highschool_id"] = self.request.session.get('current_highschool_id')

        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False
        messages.success(self.request, _("Event slot %s created.") % form.instance)
        return super().form_valid(form)

    def form_invalid(self, form):
        for k, error in form.errors.items():
            messages.error(self.request, error)
        messages.error(self.request, _("Event slot not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC'), name="dispatch")
class OffOfferEventSlotUpdate(generic.UpdateView):
    model = Slot
    form_class = OffOfferEventSlotForm
    template_name = "core/off_offer_event_slot.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager():
            return Slot.objects.filter(event__isnull=False)

        if user.is_establishment_manager():
            return Slot.objects.filter(event__establishment=user.establishment)

        if user.is_high_school_manager():
            return Slot.objects.filter(event__highschool=user.highschool)

        if user.is_structure_manager():
            return Slot.objects.filter(event__structure__in=user.get_authorized_structures())


    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["speakers"] = json.dumps(self.request.POST.getlist("speakers_list", []) or [])

        slot_id = self.object.id
        if slot_id:
            try:
                slot = Slot.objects.get(pk=slot_id)
                self.request.session["current_structure_id"] = \
                    slot.event.structure.id if slot.event.structure else None
                self.request.session["current_highschool_id"] = \
                    slot.event.highschool.id if slot.event.highschool else None
                self.request.session["current_establishment_id"] = \
                    slot.event.establishment.id if slot.event.establishment else None

                speakers_list = [{
                    "id": t.id,
                    "username": t.username,
                    "lastname": t.last_name,
                    "firstname": t.first_name,
                    "email": t.email,
                    "display_name": f"{t.last_name} {t.first_name}",
                    "is_removable": True,
                } for t in slot.speakers.all()]

                context["speakers"] = json.dumps(speakers_list)
                self.form = OffOfferEventSlotForm(instance=slot, request=self.request)
            except Slot.DoesNotExist:
                self.form = OffOfferEventSlotForm(request=self.request)

        context["slot_mode"] = "event"
        context["can_update"] = True  # FixMe
        return context


    def get_success_url(self):
        if self.add_new:
            return reverse("add_off_offer_event_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_off_offer_event_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("off_offer_events_slots")


    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False

        messages.success(self.request, _("Event slot \"%s\" updated.") % form.instance)

        self.request.session["current_structure_id"] = \
            self.object.event.structure.id if self.object.event.structure else None
        self.request.session["current_highschool_id"] = \
            self.object.event.highschool.id if self.object.event.highschool else None
        self.request.session["current_establishment_id"] = \
            self.object.event.establishment.id if self.object.event.establishment else None

        return super().form_valid(form)


    def form_invalid(self, form):
        messages.error(self.request, _("Event slot \"%s\" not updated.") % form.instance)
        return super().form_invalid(form)
