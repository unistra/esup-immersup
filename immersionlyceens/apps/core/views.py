# pylint: disable=E1101
"""
Views file

pylint ignore:
- E1101: object has no member "XX". ignore because of models object query
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests
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
from django.utils.translation import gettext, gettext_lazy as _
from django.views import generic
from hijack import signals

from immersionlyceens.decorators import groups_required

from .utils import get_session_value, set_session_values

from .admin_forms import (
    ImmersionUserChangeForm, ImmersionUserCreationForm, TrainingForm,
)
from .forms import (
    ContactForm, CourseForm, HighSchoolStudentImmersionUserForm,
    MyHighSchoolForm, OffOfferEventForm, OffOfferEventSlotForm, SlotForm,
    StructureForm, TrainingFormHighSchool
)
from .models import (
    BachelorType, Campus, CancelType, Course, Establishment, GeneralSettings,
    HighSchool, Holiday, Immersion, ImmersionGroupRecord, ImmersionUser,
    InformationText, OffOfferEvent, Period, RefStructuresNotificationsSettings,
    Slot, Structure, Training, UniversityYear
)

from .serializers import PeriodSerializer

logger = logging.getLogger(__name__)


# Define and register a signal for hijack
def hijack_clean_session_vars(sender, hijacker, hijacked, request, **kwargs):
    """
    When hijacking an account, clean the following session vars
    """
    session_vars = {}

    for page in ["courses", "events"]:
        session_vars[page] = [
            'current_establishment_id',
            'current_structure_id',
            'current_highschool_id',
            'current_training_id',
        ]

    for page, vars in session_vars.items():
        map(lambda x:request.session.pop(x, None), vars)

signals.hijack_started.connect(hijack_clean_session_vars)


@groups_required('REF-ETAB-MAITRE', 'REF-TEC')
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
            messages.warning(request, _("Please add an active University Year first."))
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


@groups_required('REF-ETAB', 'REF-TEC', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
def del_slot(request, slot_id):
    try:
        slot = Slot.objects.get(id=slot_id)
        # Check whether the user has access to this slot
        if request.user.is_structure_manager():
            if slot.course and slot.course.structure not in request.user.structures.all():
                return HttpResponse(gettext("This slot belongs to another structure"))

        slot.delete()
    except Slot.DoesNotExist:
        pass

    return HttpResponse('ok')


@groups_required('REF-ETAB', 'REF-TEC', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-ETAB-MAITRE', 'REF-LYC', 'CONS-STR')
def courses_list(request):
    if request.user.is_high_school_manager() and request.user.highschool \
        and not request.user.highschool.postbac_immersion:
        return HttpResponseRedirect("/")

    can_update_courses = False

    allowed_highschools = HighSchool.objects.none()
    allowed_establishments = Establishment.objects.none()
    allowed_strs = Structure.objects.none()

    if request.user.is_master_establishment_manager() or request.user.is_operator():
        allowed_highschools = HighSchool.agreed.filter(postbac_immersion=True)
        allowed_establishments = Establishment.activated.all()
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_establishment_manager():
        allowed_establishments = Establishment.objects.filter(pk=request.user.establishment.id)
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_structure_manager() or request.user.is_structure_consultant():
        allowed_strs = request.user.get_authorized_structures()
    elif request.user.is_high_school_manager():
        allowed_highschools = HighSchool.objects.filter(pk=request.user.highschool.id)

    if allowed_establishments.count() == 1:
        establishment_id = allowed_establishments.first().id
    else:
        establishment_id = get_session_value(request, "courses", "current_establishment_id")

    if request.user.is_high_school_manager() and allowed_highschools.count() == 1:
        highschool_id = allowed_highschools.first().id
    else:
        highschool_id = get_session_value(request, "courses", "current_highschool_id")

    if allowed_strs.count() == 1:
        structure = allowed_strs.first()
        structure_id = structure.id
        establishment_id = structure.establishment.id
    else:
        structure_id = get_session_value(request, "courses", "current_structure_id")
        if structure_id and not establishment_id:
            try:
                structure = Structure.objects.get(pk=structure_id)
                establishment_id = structure.establishment.id
            except Structure.DoesNotExist:
                pass

    # Check if we can add/update courses
    try:
        active_year = UniversityYear.objects.get(active=True)
        can_update_courses = active_year.date_is_between(datetime.today().date()) \
            and not request.user.is_structure_consultant()
    except UniversityYear.DoesNotExist:
        pass
    except UniversityYear.MultipleObjectsReturned:
        pass

    if not can_update_courses and not request.user.is_structure_consultant():
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


@groups_required('REF-ETAB', 'REF-TEC', 'REF-STR', 'REF-ETAB-MAITRE', 'REF-LYC')
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

        # speakers are mandatory if the course is published
        is_published = request.POST.get('published', False) == "on"

        try:
            speakers_list = json.loads(speakers_list)
            assert not is_published or len(speakers_list) > 0
        except Exception:
            messages.error(request, _("At least one speaker is required"))
        else:
            if course_form.is_valid():
                new_course = course_form.save()

                set_session_values(request, "courses", {
                    "current_structure_id": new_course.structure.id if new_course.structure else "",
                    "current_highschool_id": new_course.highschool.id if new_course.highschool else "",
                    "current_establishment_id": new_course.structure.establishment.id if new_course.structure else ""
                })

                current_speakers = [u for u in new_course.speakers.all().values_list('username', flat=True)]
                new_speakers = [speaker.get('username') for speaker in speakers_list]

                # speakers to add
                for speaker in speakers_list:
                    if isinstance(speaker, dict):
                        send_creation_msg = False

                        try:
                            speaker_user = ImmersionUser.objects.get(
                                Q(username=speaker.get('username')) | Q(email=speaker['email'])
                            )
                        except ImmersionUser.DoesNotExist:
                            establishment = new_course.structure.establishment if new_course.structure else None

                            speaker_user = ImmersionUser.objects.create(
                                username=speaker['email'],
                                last_name=speaker['lastname'],
                                first_name=speaker['firstname'],
                                email=speaker['email'],
                                establishment=establishment
                            )

                            messages.success(request, gettext("User '{}' created").format(speaker_user.username))
                            if not speaker_user.establishment or not speaker_user.establishment.data_source_plugin:
                                speaker_user.set_recovery_string()
                            send_creation_msg = True

                        try:
                            Group.objects.get(name='INTER').user_set.add(speaker_user)
                        except Exception:
                            messages.error(
                                request, _("Couldn't add group 'INTER' to user '%s'" % speaker_user.username),
                            )

                        if send_creation_msg:
                            return_msg = speaker_user.send_message(request, 'CPT_CREATE')

                            if not return_msg:
                                messages.success(
                                    request,
                                    gettext("A confirmation email has been sent to {}").format(speaker['email']),
                                )
                                speaker_user.creation_email_sent = True
                                speaker_user.save()
                            else:
                                messages.warning(request, gettext("Couldn't send email : %s" % return_msg))

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


@groups_required('INTER','REF-LYC', )
def myslots(request, slots_type=None):
    contact_form = ContactForm()

    context = {
        'contact_form': contact_form,
        'user_slots': True
    }

    if slots_type == "events":
        context["slot_mode"] = "events"
        return render(request, 'core/my_events_slots.html', context)
    elif slots_type == "courses":
        context["slot_mode"] = "courses"
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

            if not new_speaker.establishment or not new_speaker.establishment.data_source_plugin:
                new_speaker.set_recovery_string()

            Group.objects.get(name='INTER').user_set.add(new_speaker)

            if speaker:
                messages.success(request, _("Speaker successfully updated."))
                if 'email' in speaker_form.changed_data:
                    messages.warning(request, _("Warning : the username is now the new speaker's email address"))
            else:
                messages.success(request, _("Speaker successfully created."))

                # Send creation message
                return_msg = new_speaker.send_message(request, 'CPT_CREATE')

                if not return_msg:
                    messages.success(
                        request,
                        gettext("A confirmation email has been sent to {}").format(new_speaker.email),
                    )
                    new_speaker.creation_email_sent = True
                    new_speaker.save()
                else:
                    messages.warning(request, gettext("Couldn't send email : %s" % return_msg))

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


@method_decorator(groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
class MyStudents(generic.TemplateView):
    template_name: str = "core/highschool_students.html"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        can_show_users_without_record: bool = any([
            self.request.user.is_operator(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_establishment_manager(),
            self.request.user.is_high_school_manager()
                and self.request.user.highschool
                and self.request.user.highschool.postbac_immersion,
        ])

        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context.update({
            "highschool": self.request.user.highschool,
            'can_show_users_without_record': can_show_users_without_record,
        })

        return context


# todo: remove this function
@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def student_validation(request, high_school_id=None):
    if request.user.is_high_school_manager() and request.user.highschool:
        try:
            high_school_id = request.user.highschool.id
        except AttributeError:
            messages.error(request, _("Your account is not bound to any high school"))
            return redirect('/')

    # student_validation
    context = {
        'highschool_filter': request.session.get('highschool_filter'),
        'convention_filter': request.session.get('convention_filter'),
    }

    if high_school_id:
        try:
            context['high_school'] = HighSchool.objects.get(id=high_school_id)
        except HighSchool.DoesNotExist:
            messages.error(request, _("This high school id does not exist"))
            return redirect('/core/student_validation/')

    context["w_convention"] = GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT")
    context["wo_convention"] = GeneralSettings.get_setting("ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT")

    try:
        context['hs_id'] = int(request.GET.get('hs_id'))
    except (ValueError, TypeError):
        pass

    return render(request, 'core/student_validation.html', context)


@method_decorator(groups_required("REF-ETAB-MAITRE", "REF-TEC"), name="dispatch")
class VisitorValidationView(generic.TemplateView):
    template_name = "core/visitor_validation.html"


@groups_required('REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def highschool_student_record_form_manager(request, hs_record_id):
    from immersionlyceens.apps.immersion.forms import (
        HighSchoolStudentRecordManagerForm,
    )
    from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

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


@method_decorator(groups_required('REF-STR'), name="dispatch")
class MyStructureView(generic.TemplateView):
    template_name = "core/structure.html"

    def get_context_data(self, **kwargs):
        context: Dict[str, Any] = super().get_context_data(**kwargs)

        my_structures = Structure.objects.filter(referents=self.request.user).order_by('label')

        if my_structures.count() == 1:
            context.update({"structure": my_structures.first()})
        else:
            context.update({"structures": list(my_structures)})
        return context

#
# @groups_required('REF-STR')
# def structure(request, structure_code=None):
#     """
#     Update structure url and mailing list
#     """
#     form = None
#     structure = None
#     structures = None
#
#     if request.method == "POST":
#         try:
#             structure = Structure.objects.get(code=request.POST.get('code'))
#         except Exception:
#             messages.error(request, _("Invalid parameter"))
#             return redirect('structure')
#
#         form = StructureForm(request.POST, instance=structure)
#
#         if form.is_valid():
#             form.save()
#             messages.success(request, _("Structure settings successfully saved"))
#             return redirect('structure')
#     elif structure_code:
#         try:
#             structure = Structure.objects.get(code=structure_code)
#             form = StructureForm(instance=structure)
#         except Structure.DoesNotExist:
#             messages.error(request, _("Invalid parameter"))
#             return redirect('structure')
#     else:
#         my_structures = Structure.objects.filter(referents=request.user).order_by('label')
#
#         if my_structures.count() == 1:
#             structure = my_structures.first()
#             form = StructureForm(instance=structure)
#         else:
#             structures = [c for c in my_structures]
#
#     context = {
#         'form': form,
#         'structure': structure,
#         'structures': structures,
#     }
#
#     return render(request, 'core/structure.html', context)


@groups_required(
    'REF-STR', 'REF-ETAB', 'REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC'
)
def stats(request):
    template = 'core/stats.html'
    structures = None

    if request.user.is_master_establishment_manager():
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
@groups_required('SRV-JUR', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-LYC')
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
@groups_required('REF-ETAB-MAITRE', 'REF-TEC')
def duplicated_accounts(request):
    """
    Manage duplicated accounts
    """

    context = {}

    return render(request, 'core/duplicated_accounts.html', context)


@method_decorator(groups_required('REF-LYC', 'REF-ETAB-MAITRE', 'REF-TEC', 'REF-ETAB', 'REF-STR', 'CONS-STR'), name="dispatch")
class TrainingList(generic.TemplateView):
    template_name = "core/training/list.html"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context.update({
            "establishments": Establishment.objects.none(),
            "highschools": HighSchool.objects.none(),
            "structures": Structure.objects.none()
        })

        if self.request.user.is_master_establishment_manager() or self.request.user.is_operator():
            context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True)
            context["establishments"] = Establishment.activated.all()
            context["structures"] = self.request.user.get_authorized_structures()
        elif self.request.user.is_establishment_manager():
            context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
            context["structures"] = self.request.user.get_authorized_structures()
        elif self.request.user.is_structure_manager() or self.request.user.is_structure_consultant():
            context["structures"] = self.request.user.get_authorized_structures()
        elif self.request.user.is_high_school_manager():
            context["highschools"] = HighSchool.objects.filter(pk=self.request.user.highschool.id)

        if context["establishments"].count() == 1:
            context["establishment_id"] = context["establishments"].first().id
        else:
            context["establishment_id"] = get_session_value(self.request, "trainings", "current_establishment_id")

        if len(context['structures']) == 1:
            context['structure_id'] = context['structures'].first().id
            context['establishment_id'] = context['structures'].first().establishment.id
        else:
            context['structure_id'] = ""

        try:
            training_quota = GeneralSettings.get_setting("ACTIVATE_TRAINING_QUOTAS")
            context['activated_training_quotas'] = training_quota['activate']
            context['training_quotas_value'] = training_quota['default_quota']
        except:
            context['activated_training_quotas'] = False

        return context


@method_decorator(groups_required('REF-LYC'), name="dispatch")
class TrainingAdd(generic.CreateView):
    """
    Training creation
    """
    form_class = TrainingFormHighSchool
    template_name: str = "core/training/training.html"

    def get_success_url(self) ->  str:
        return reverse("trainings")

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
        return reverse("trainings")

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


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC', 'CONS-STR'), name="dispatch")
class CourseSlotList(generic.TemplateView):
    template_name = "core/courses_slots_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "can_update": True, # FixMe
            "slot_mode": "courses",
            "contact_form": ContactForm(),
            "cancel_types": CancelType.objects.filter(active=True, students=True),
            "groups_cancel_types": CancelType.objects.filter(active=True, groups=True),
            "establishments": Establishment.activated.all(),
            "structures": Structure.activated.all(),
            "highschools": HighSchool.agreed.filter(postbac_immersion=True).order_by('city', 'label'),
            "group_highschools": HighSchool.agreed.order_by('city', 'label'),
            "establishment_id": kwargs.get(
                'establishment_id',
                get_session_value(self.request, "courses", "current_establishment_id")
            ),
            "structure_id": kwargs.get(
                'structure_id',
                get_session_value(self.request, "courses", "current_structure_id")
            ),
            "highschool_id": kwargs.get(
                'highschool_id',
                get_session_value(self.request, "courses", "current_highschool_id")
            ),
            "training_id": kwargs.get(
                'training_id',
                get_session_value(self.request, "courses", "current_training_id")
            ),
            "course_id": kwargs.get('course_id', None),
            "group_file_help_text": ImmersionGroupRecord.file.field.help_text,
        })

        try:
            course = Course.objects.get(pk=int(context["course_id"]))
            context["course_label_filter"] = course.label
        except (ValueError, TypeError, Course.DoesNotExist):
            context["course_id"] = None

        try:
            Training.objects.get(pk=int(context["training_id"]))
        except (ValueError, TypeError, Training.DoesNotExist):
            context["training_id"] = None

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context.update({
                    "establishments": Establishment.objects.filter(pk=self.request.user.establishment.id),
                    "structures": context["structures"].filter(establishment=self.request.user.establishment),
                    "establishment_id": self.request.user.establishment.id
                })

            if self.request.user.is_structure_manager() or self.request.user.is_structure_consultant():
                context.update({
                    "establishments": Establishment.objects.filter(pk=self.request.user.establishment.id),
                    "structures": self.request.user.structures.filter(active=True),
                    "establishment_id": self.request.user.establishment.id,
                    "structure_id": context["structure_id"] or self.request.user.structures.first().id
                })
            if self.request.user.is_high_school_manager():
                context.update({
                    "establishments": Establishment.objects.none(),
                    "structures": Structure.objects.none(),
                    "highschools": HighSchool.agreed.filter(
                        postbac_immersion=True,
                        pk=self.request.user.highschool.id
                    ),
                    "highschool_id": self.request.user.highschool.id
                })

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class CourseSlot(generic.CreateView):
    """
    Course slot add/duplicate
    """
    form_class = SlotForm
    template_name = "core/course_slot.html"
    duplicate = False

    def get_success_url(self):
        set_session_values(self.request, "courses", {
            'current_establishment_id':
                self.object.course.structure.establishment.id if self.object.course.structure else "",
            'current_structure_id': self.object.course.structure.id if self.object.course.structure else "",
            'current_training_id': self.object.course.training.id if self.object.course.training else "",
            'current_highschool_id': self.object.course.highschool.id if self.object.course.highschool else ""
        })

        if self.add_new:
            return reverse("add_course_slot")
        elif self.duplicate and self.object.pk:
            return reverse("duplicate_course_slot", kwargs={'pk': self.object.pk, 'duplicate': 1})
        else:
            return reverse("courses_slots")


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
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

        if self.duplicate and object_pk:
            context = {'duplicate': True}
            try:
                slot = Slot.objects.get(pk=object_pk)

                establishment_id = slot.course.structure.establishment.id if slot.course.structure else None
                structure_id = slot.course.structure.id if slot.course.structure else None
                highschool_id = slot.course.highschool.id if slot.course.highschool else None
                training_id = slot.course.training.id if slot.course.training else None

                initials = {
                    'establishment': establishment_id,
                    'structure': structure_id,
                    'highschool': highschool_id,
                    'training': training_id,
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
                    'n_group_places': slot.n_group_places,
                    'additional_information': slot.additional_information,
                    'face_to_face': slot.face_to_face,
                    'establishments_restrictions': slot.establishments_restrictions,
                    'levels_restrictions': slot.levels_restrictions,
                    'bachelors_restrictions': slot.bachelors_restrictions,
                    'allowed_establishments': [e.id for e in slot.allowed_establishments.all()],
                    'allowed_highschools': [h.id for h in slot.allowed_highschools.all()],
                    'allowed_highschool_levels': slot.allowed_highschool_levels.all(),
                    'allowed_student_levels': slot.allowed_student_levels.all(),
                    'allowed_post_bachelor_levels': slot.allowed_post_bachelor_levels.all(),
                    'allowed_bachelor_types': slot.allowed_bachelor_types.all(),
                    'allowed_bachelor_mentions': slot.allowed_bachelor_mentions.all(),
                    'allowed_bachelor_teachings': slot.allowed_bachelor_teachings.all(),
                    'speakers': [s.id for s in slot.speakers.all()],
                    'allow_group_registrations': slot.allow_group_registrations,
                    'allow_individual_registrations': slot.allow_individual_registrations,
                    'group_mode': slot.group_mode,
                    'public_group': slot.public_group,
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    # careful, some fields are lists
                    if k in ['allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels',
                             'allowed_student_levels', 'allowed_post_bachelor_levels', 'allowed_bachelor_types',
                             'allowed_bachelor_mentions', 'allowed_bachelor_teachings', 'speakers']:
                        initials[k] = data.getlist(k, initials[k])
                    else:
                        initials[k] = data.get(k, initials[k])

                self.form = self.form_class(initial=initials, request=self.request)

                context["origin_id"] = slot.id
                context["form"] = self.form

                # Set <select> initial values from the slot to duplicate
                context["establishment_id"] = establishment_id
                context["structure_id"] = structure_id
                context["highschool_id"] = highschool_id
                context["training_id"] = training_id

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

        if self.request.POST:
            context["slot_dates"] = ",".join([str(i) for i in self.request.POST.getlist("slot_dates[]")])
        else:
            context["slot_dates"] = None

        context["can_update"] = True  # FixMe
        context["slot_mode"] = "courses"

        if "establishment_id" not in context:
            context["establishment_id"] = get_session_value(self.request, "courses", "current_establishment_id")

        if "structure_id" not in context:
            context["structure_id"] = get_session_value(self.request, "courses", "current_structure_id")

        if "highschool_id" not in context:
            context["highschool_id"] = get_session_value(self.request, "courses", "current_highschool_id")

        if "training_id" not in context:
            context["training_id"] = get_session_value(self.request, "courses", "current_training_id")

        # Bachelor types for restrictions
        context["bachelor_types"] = json.dumps({
            bt.id: {
                'is_general': bt.general,
                'is_technological': bt.technological,
                'is_professional': bt.professional,
            } for bt in BachelorType.objects.filter(active=True)
        })

        context["periods"] = json.dumps({
            period.pk: PeriodSerializer(period).data for period in Period.objects.all()
        })

        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) is not False
        self.add_new = self.request.POST.get("save_add", False) is not False
        messages.success(self.request, _("Course slot \"%s\" created.") % form.instance)

        repeat_until = self.request.POST.get('repeat')
        if repeat_until:
            self.slot_dates = self.request.POST.getlist('slot_dates')

        return super().form_valid(form)

    def form_invalid(self, form):
        for k, error in form.errors.items():
            messages.error(self.request, error)
        messages.error(self.request, _("Course slot not created."))

        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class CourseSlotUpdate(generic.UpdateView):
    model = Slot
    form_class = SlotForm
    template_name = "core/course_slot.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.get_object()
        except Exception as e:
            if Slot.objects.filter(pk=self.kwargs.get('pk')).exists():
                messages.error(request, _("This slot belongs to another structure"))
            else:
                messages.error(request, _("Slot not found"))
            return redirect(reverse('courses_slots'))

        return super().dispatch(request, *args, **kwargs)


    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager() or user.is_operator():
            return Slot.objects.filter(course__isnull=False)

        if user.is_establishment_manager():
            return Slot.objects.filter(course__structure__establishment=user.establishment)

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

                set_session_values(self.request, "courses", {
                    "current_structure_id": slot.course.structure.id if slot.course.structure else "",
                    "current_highschool_id": slot.course.highschool.id if slot.course.highschool else "",
                    "current_establishment_id":
                        slot.course.structure.establishment.id if slot.course.structure else "",
                    "current_training_id": slot.course.training.id if slot.course.training else ""
                })

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

        context["slot_mode"] = "courses"
        context["can_update"] = True  # FixMe

        # Bachelor types for restrictions
        context["bachelor_types"] = json.dumps({
            bt.id: {
                'is_general': bt.general,
                'is_technological': bt.technological,
                'is_professional': bt.professional,
            } for bt in BachelorType.objects.filter(active=True)
        })

        context["periods"] = json.dumps({
            period.pk: PeriodSerializer(period).data for period in Period.objects.all()
        })

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

        set_session_values(self.request, "courses", {
            "current_structure_id": self.object.course.structure.id if self.object.course.structure else "",
            "current_highschool_id": self.object.course.highschool.id if self.object.course.highschool else "",
            "current_establishment_id":
                self.object.course.structure.establishment.id if self.object.course.structure else "",
            "current_training_id": self.object.course.training.id if self.object.course.training else ""
        })

        if self.object.course and not self.object.course.published and self.object.published:
            self.object.course.published = True
            self.object.course.save()
            messages.success(self.request, _("Course published"))

        if self.request.POST.get('notify_student') == 'on':
            sent_msg = 0
            not_sent_msg = 0
            errors_list = []

            immersions = Immersion.objects.filter(slot=self.object, cancellation_type__isnull=True)

            for immersion in immersions:
                ret = immersion.student.send_message(
                    self.request,
                    'CRENEAU_MODIFY_NOTIF',
                    immersion=immersion,
                    slot=self.object
                )

                if not ret:
                    sent_msg += 1
                elif ret not in errors_list:
                    not_sent_msg += 1
                    errors_list.append(ret)

            if sent_msg:
                messages.success(self.request, gettext("Notifications have been sent (%s)") % sent_msg)

            if errors_list:
                messages.warning(
                    self.request,
                    gettext("{} error(s) occurred :".format(not_sent_msg))  + "<br /".join(errors_list)
                )

        return super().form_valid(form)


    def form_invalid(self, form):
        messages.error(self.request, _("Course slot \"%s\" not updated.") % form.instance)
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC', 'CONS-STR'), name="dispatch")
class OffOfferEventsList(generic.TemplateView):
    template_name = "core/off_offer_events_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True # FixMe

        context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True).order_by("city", "label")
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()

        context["establishment_id"] = get_session_value(self.request, "events", 'current_establishment_id')
        context["structure_id"] = get_session_value(self.request, "events", 'current_structure_id')
        context["highschool_id"] = get_session_value(self.request, "events", 'current_highschool_id')

        if not self.request.user.is_superuser:
            if self.request.user.is_establishment_manager():
                context["establishments"] = context["establishments"].filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager() or self.request.user.is_structure_consultant():
                context["establishments"] = context["establishments"].filter(pk=self.request.user.establishment.id)
                context["structures"] = self.request.user.structures.filter(active=True)
                context["establishment_id"] = self.request.user.establishment.id

                if self.request.user.structures.filter(active=True).count() == 1:
                    context["structure_id"] = self.request.user.structures.filter(active=True).first().id

            if self.request.user.is_high_school_manager():
                context["establishments"] = Establishment.objects.none()
                context["structures"] = Structure.objects.none()
                context["highschools"] = HighSchool.agreed.filter(id=self.request.user.highschool.id)
                context["highschool_id"] = self.request.user.highschool.id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class OffOfferEventAdd(generic.CreateView):
    """
    Off offer event add/duplicate
    """
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
        context["establishment_id"] = get_session_value(self.request, "events", 'current_establishment_id')
        context["structure_id"] = get_session_value(self.request, "events", 'current_structure_id')

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

        set_session_values(self.request, "events", {
            'current_establishment_id': self.object.establishment.id if self.object.establishment else "",
            'current_structure_id': self.object.structure.id if self.object.structure else "",
            'current_highschool_id': self.object.highschool.id if self.object.highschool else ""
        })

        return response


    def form_invalid(self, form):
        messages.error(self.request, _("Off offer event not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class OffOfferEventUpdate(generic.UpdateView):
    model = OffOfferEvent
    form_class = OffOfferEventForm
    template_name = "core/off_offer_event.html"

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager() or user.is_operator():
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
                set_session_values(self.request, "events", {
                    "current_structure_id": event.structure.id if event.structure else "",
                    "current_highschool_id": event.highschool.id if event.highschool else "",
                    "current_establishment_id": event.establishment.id if event.establishment else "",
                })

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

        set_session_values(self.request, "events", {
            "current_structure_id": self.object.structure.id if self.object.structure else "",
            "current_highschool_id": self.object.highschool.id if self.object.highschool else "",
            "current_establishment_id": self.object.establishment.id if self.object.establishment else ""
        })

        self.duplicate = self.request.POST.get("save_duplicate", False) != False
        self.add_new = self.request.POST.get("save_add_new", False) != False

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Off offer event \"%s\" not updated.") % str(form.instance))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC', 'CONS-STR'), name="dispatch")
class OffOfferEventSlotList(generic.TemplateView):
    template_name = "core/off_offer_events_slots_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_update"] = True #FixMe
        context["slot_mode"] = "events"
        context["contact_form"] = ContactForm()
        context["cancel_types"] = CancelType.objects.filter(active=True, students=True)
        context["groups_cancel_types"] = CancelType.objects.filter(active=True, groups=True)
        context["group_file_help_text"] = ImmersionGroupRecord.file.field.help_text

        # Defaults
        context["establishments"] = Establishment.activated.all()
        context["structures"] = Structure.activated.all()
        context["highschools"] = HighSchool.agreed.filter(postbac_immersion=True).order_by('city', 'label')

        context["establishment_id"] = \
            kwargs.get('establishment_id', get_session_value(self.request, "events", "current_establishment_id"))

        try:
            establishment = Establishment.objects.get(pk=kwargs.get('establishment_id'))
            context["managed_by_filter"] = establishment.code
        except Establishment.DoesNotExist:
            pass

        context["structure_id"] = kwargs.get('structure_id')

        if context["structure_id"] == "null":
            context["structure_id"] = ""
        elif context["structure_id"] is None:
            context["structure_id"] = get_session_value(self.request, "events", "current_structure_id")
        else:
            try:
                structure = Structure.objects.get(pk=context["structure_id"])
                context["managed_by_filter"] += f" - {structure.code}"
            except Structure.DoesNotExist:
                pass

        if kwargs.get('highschool_id'):
            try:
                highschool = HighSchool.objects.get(pk=kwargs.get('highschool_id'))
                context["highschool_id"] = highschool.id
                context["managed_by_filter"] = f"{highschool.city} - {highschool.label}"
            except HighSchool.DoesNotExist:
                pass
        else:
            context["highschool_id"] = get_session_value(self.request, "events", "current_highschool_id")

        context["event_id"] = kwargs.get('event_id', None)

        if context["event_id"]:
            try:
                event = OffOfferEvent.objects.get(pk=context["event_id"])
                context["event_type_filter"] = event.event_type.label
                context["event_label_filter"] = event.label
            except OffOfferEvent.DoesNotExist:
                pass

        if not self.request.user.is_superuser:
            if self.request.user.is_master_establishment_manager() or self.request.user.is_operator():
                if not context.get("highschool_id"):
                    context["establishment_id"] = context["establishment_id"] or self.request.user.establishment.id

            if self.request.user.is_establishment_manager():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = context["structures"].filter(establishment=self.request.user.establishment)
                context["establishment_id"] = self.request.user.establishment.id

            if self.request.user.is_structure_manager() or self.request.user.is_structure_consultant():
                context["establishments"] = Establishment.objects.filter(pk=self.request.user.establishment.id)
                context["structures"] = self.request.user.structures.filter(active=True)
                context["establishment_id"] = self.request.user.establishment.id
                context["structure_id"] = context.get("structure_id") or self.request.user.structures.first().id

            if self.request.user.is_high_school_manager():
                context["establishments"] = Establishment.objects.none()
                context["structures"] = Structure.objects.none()
                context["highschools"] = HighSchool.agreed.filter(
                    postbac_immersion=True, pk=self.request.user.highschool.id
                )
                context["highschool_id"] = self.request.user.highschool.id

        return context


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class OffOfferEventSlot(generic.CreateView):
    """
    Off offer event add/duplicate
    """
    form_class = OffOfferEventSlotForm
    template_name = "core/off_offer_event_slot.html"
    duplicate = False

    def get_success_url(self):
        set_session_values(self.request, "events", {
            "current_structure_id": self.object.event.structure.id if self.object.event.structure else "",
            "current_highschool_id": self.object.event.highschool.id if self.object.event.highschool else "",
            "current_establishment_id": self.object.event.establishment.id if self.object.event.establishment else ""
        })

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
            context["structure_id"] = ""

            if self.kwargs.get('establishment_id'):
                try:
                    context["structure_id"] = int(self.kwargs.get('structure_id', None))
                except Exception:
                    context["structure_id"] = ""

            context["highschool_id"] = self.kwargs.get('highschool_id', None)
            context["event_id"] = self.kwargs.get('event_id')

            try:
                event = OffOfferEvent.objects.get(pk=context["event_id"])
            except OffOfferEvent.DoesNotExist:
                pass

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
                    'n_group_places': slot.n_group_places,
                    'additional_information': slot.additional_information,
                    'face_to_face': slot.face_to_face,
                    'establishments_restrictions': slot.establishments_restrictions,
                    'levels_restrictions': slot.levels_restrictions,
                    'bachelors_restrictions': slot.bachelors_restrictions,
                    'allowed_establishments': [e.id for e in slot.allowed_establishments.all()],
                    'allowed_highschools': [h.id for h in slot.allowed_highschools.all()],
                    'allowed_highschool_levels': slot.allowed_highschool_levels.all(),
                    'allowed_student_levels': slot.allowed_student_levels.all(),
                    'allowed_post_bachelor_levels': slot.allowed_post_bachelor_levels.all(),
                    'allowed_bachelor_types': slot.allowed_bachelor_types.all(),
                    'allowed_bachelor_mentions': slot.allowed_bachelor_mentions.all(),
                    'allowed_bachelor_teachings': slot.allowed_bachelor_teachings.all(),
                    'speakers': [s.id for s in slot.speakers.all()],
                    'allow_group_registrations': slot.allow_group_registrations,
                    'allow_individual_registrations': slot.allow_individual_registrations,
                    'group_mode': slot.group_mode,
                    'public_group': slot.public_group,
                }

                # In case of form error, update initial values with POST ones (prevents a double call to clean())
                data = self.request.POST
                for k in initials.keys():
                    # careful, some fields are lists
                    if k in ['allowed_establishments', 'allowed_highschools', 'allowed_highschool_levels',
                             'allowed_student_levels', 'allowed_post_bachelor_levels', 'allowed_bachelor_types',
                             'allowed_bachelor_mentions', 'allowed_bachelor_teachings', 'speakers']:
                        initials[k] = data.getlist(k, initials[k])
                    else:
                        initials[k] = data.get(k, initials[k])

                self.form = self.form_class(initial=initials, request=self.request)
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

            self.form = self.form_class(initial=initials, request=self.request)
            context["form"] = self.form

        context["can_update"] = True  # FixMe
        context["slot_mode"] = "events"

        # Bachelor types for restrictions
        context["bachelor_types"] = json.dumps({
            bt.id: {
                'is_general': bt.general,
                'is_technological': bt.technological,
                'is_professional': bt.professional,
            } for bt in BachelorType.objects.filter(active=True)
        })

        # Periods
        context["periods"] = json.dumps({
            period.pk: PeriodSerializer(period).data for period in Period.objects.all()
        })

        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        self.duplicate = self.request.POST.get("duplicate", False) != False
        self.add_new = self.request.POST.get("save_add", False) != False
        messages.success(self.request, _("Event slot \"%s\" created.") % form.instance)

        return super().form_valid(form)

    def form_invalid(self, form):
        for k, error in form.errors.items():
            messages.error(self.request, error)
        messages.error(self.request, _("Event slot not created."))
        return super().form_invalid(form)


@method_decorator(groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'REF-LYC', 'REF-TEC'), name="dispatch")
class OffOfferEventSlotUpdate(generic.UpdateView):
    model = Slot
    form_class = OffOfferEventSlotForm
    template_name = "core/off_offer_event_slot.html"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.get_object()
        except Exception as e:
            if Slot.objects.filter(pk=self.kwargs.get('pk')).exists():
                messages.error(request, _("This slot belongs to another structure"))
            else:
                messages.error(request, _("Slot not found"))
            return redirect(reverse('off_offer_events_slots'))

        return super().dispatch(request, *args, **kwargs)


    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_master_establishment_manager() or user.is_operator():
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

                set_session_values(self.request, "events", {
                    "current_structure_id": slot.event.structure.id if slot.event.structure else "",
                    "current_highschool_id": slot.event.highschool.id if slot.event.highschool else "",
                    "current_establishment_id": slot.event.establishment.id if slot.event.establishment else "",
                })

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

        context["slot_mode"] = "events"
        context["can_update"] = True # FixMe

        # Periods
        context["periods"] = json.dumps({
            period.pk: PeriodSerializer(period).data for period in Period.objects.all()
        })

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

        set_session_values(self.request, "events", {
            "current_structure_id": self.object.event.structure.id if self.object.event.structure else "",
            "current_highschool_id": self.object.event.highschool.id if self.object.event.highschool else "",
            "current_establishment_id": self.object.event.establishment.id if self.object.event.establishment else ""
        })

        if self.object.event and not self.object.event.published and self.object.published:
            self.object.event.published = True
            self.object.event.save()
            messages.success(self.request, _("Event published"))

        if self.request.POST.get('notify_student') == 'on':
            sent_msg = 0
            not_sent_msg = 0
            errors_list = []

            immersions = Immersion.objects.filter(slot=self.object, cancellation_type__isnull=True)

            for immersion in immersions:
                ret = immersion.student.send_message(
                    self.request,
                    'CRENEAU_MODIFY_NOTIF',
                    immersion=immersion,
                    slot=self.object
                )

                if not ret:
                    sent_msg += 1
                elif ret not in errors_list:
                    not_sent_msg += 1
                    errors_list.append(ret)

            if sent_msg:
                messages.success(self.request, gettext("Notifications have been sent (%s)") % sent_msg)

            if errors_list:
                messages.warning(
                    self.request,
                    gettext("{} error(s) occurred :".format(not_sent_msg))  + "<br /".join(errors_list)
                )

        return super().form_valid(form)


    def form_invalid(self, form):
        messages.error(self.request, _("Event slot \"%s\" not updated.") % form.instance)
        return super().form_invalid(form)


def charter(request):
    user = request.user
    establishment_or_highschool = ""
    address = ""

    if request.user.is_anonymous:
        return HttpResponseRedirect("/")

    try:
        charter_txt = InformationText.objects.get(code="CHARTE_ETABLISSEMENT_ACCUEIL", active=True).content
    except InformationText.DoesNotExist:
        charter_txt = ''

    if user.is_establishment_manager() and user.establishment:
        est = user.establishment
        establishment_or_highschool = est.label
        address = f"{est.address}, {est.zip_code} {est.city}"
    elif user.is_high_school_manager() and user.highschool:
        hs = user.highschool
        establishment_or_highschool = hs
        address = f"{hs.address}, {hs.zip_code} {hs.city}"

    context = {
        'establishment_or_highschool': establishment_or_highschool,
        'establishment_or_highschool_address': address,
        'charter_txt': charter_txt
    }

    return render(request, 'core/charter.html', context)


@groups_required('REF-STR')
def structures_notifications(request, structure_code=None):
    """
    Update structures managers notifications choices
    """

    data = []
    settings = None
    try:
        settings = RefStructuresNotificationsSettings.objects.get(user=request.user)
    except RefStructuresNotificationsSettings.DoesNotExist:
        pass

    structures = Structure.objects.filter(referents=request.user).order_by('label')

    for structure in structures:
        data.append({'structure':structure, 'checked':(structure in settings.structures.all()) if settings else False})

    context = {
        'structures': data
    }

    return render(request, 'core/structures_notifications.html', context)