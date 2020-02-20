import uuid
import logging
from datetime import datetime, timedelta

from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import Session
from django.conf import settings

from immersionlyceens.apps.core.models import ImmersionUser, UniversityYear, Calendar
from immersionlyceens.libs.utils import check_active_year

from .models import HighSchoolStudentRecord, StudentRecord

from .forms import (LoginForm, RegistrationForm, HighSchoolStudentRecordForm,
    HighSchoolStudentForm, HighSchoolStudentPassForm, StudentRecordForm,
    StudentForm)


logger = logging.getLogger(__name__)

def customLogin(request):
    # Clear all client sessions
    Session.objects.all().delete()

    is_reg_possible, is_year_valid, year = check_active_year()

    if not year or not is_year_valid:
        messages.warning(request, _("Sorry, you can't login right now."))
        context = {
            'start_date': year.start_date if year else None,
            'end_date': year.end_date if year else None,
            'reg_date': year.registration_start_date if year else None
        }
        return render(request, 'immersion/nologin.html', context)


    # Is current university year valid ?
    if not check_active_year():
        return render(request, 'immersion/nologin.html',
            { 'msg' : _("Sorry, the university year has not begun (or already over), you can't login yet.") }
        )

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['login']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Activated account ?
                if not user.is_valid():
                    messages.error(request, _("Your account hasn't been enabled yet."))
                else:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    # If student has filled his record
                    if user.get_high_school_student_record():
                        return HttpResponseRedirect("/immersion")
                    else:
                        return HttpResponseRedirect("/immersion/hs_record")
            else:
                messages.error(request, _("Authentication error"))
    else:
        form = LoginForm()

    context = {
        'form': form
    }

    return render(request, 'immersion/login.html', context)

"""
# TODO : try Django's authentication system

class CustomLogin(auth_views.LoginView):
    template_name = "immersion/login.html"
    redirect_field_name = "/immersion"
    authentication_form = LoginForm
"""

def register(request):
    # Is current university year valid ?
    is_reg_possible, is_year_valid, year = check_active_year()

    if not year or not is_reg_possible:
        messages.warning(request, _("Sorry, you can't register right now."))
        context = {
            'start_date': year.start_date if year else None,
            'end_date': year.end_date if year else None,
            'reg_date': year.registration_start_date if year else None
        }
        return render(request, 'immersion/nologin.html', context)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            new_user = form.save(commit=False)
            # adjustments here
            new_user.username = form.cleaned_data.get("username")
            new_user.set_validation_string()
            new_user.destruction_date = \
                datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
            new_user.save()

            try:
                Group.objects.get(name='LYC').user_set.add(new_user)
            except Exception:
                logger.exception("Cannot add 'LYC' group to user {}".format(new_user))
                messages.error(request, _("Group error"))

            try:
                msg = new_user.send_message(request, 'CPT_MIN_CREATE_LYCEEN')
            except Exception as e:
                logger.exception("Cannot send activation message : %s", e)

            messages.success(request, _("Account created. Please look at your emails for the activation procedure."))
            return HttpResponseRedirect("/immersion/login")
        else:
            for err_field, err_list in form.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        form = RegistrationForm()

    context = {
        'form': form
    }

    return render(request, 'immersion/registration.html', context)


def recovery(request):
    email = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()

        try:
            user = ImmersionUser.objects.get(email__iexact=email)

            if not user.username.startswith(settings.USERNAME_PREFIX):
                messages.warning(request, _("Please use your establishment credentials."))
            else:
                user.set_recovery_string()
                msg = user.send_message(request, 'CPT_MIN_ID_OUBLIE')
                messages.success(request, _("An email has been sent with the procedure to set a new password."))

        except ImmersionUser.DoesNotExist:
            messages.error(request, _("No account found with this email address"))
        except ImmersionUser.MultipleObjectsReturned:
            messages.error(request, _("Error : please contact the SCUIO-IP"))

    context = {
        'email': email,
    }

    return render(request, 'immersion/recovery.html', context)


def reset_password(request, hash=None):
    if request.method == "POST":
        user_id = request.session.get("user_id")

        if user_id:
            try:
                user = ImmersionUser.objects.get(pk=user_id)
            except ImmersionUser.DoesNotExist:
                messages.error(request, _("Password recovery : invalid data"))
                return HttpResponseRedirect("/immersion/login")

            form = HighSchoolStudentPassForm(request.POST, instance=user)

            if form.is_valid():
                user = form.save()
                user.recovery_string = None
                user.save()
                messages.success(request, _("Password successfully updated."))
                return HttpResponseRedirect("/immersion/login")

            return render(request, 'immersion/reset_password.html', {'form':form})
    elif hash:
        try:
            user = ImmersionUser.objects.get(recovery_string=hash)
            request.session['user_id'] = user.id
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Password recovery : invalid data"))
            return HttpResponseRedirect("/immersion/login")
        except ImmersionUser.MultipleObjectsReturned:
            messages.error(request, _("Error : please contact the SCUIO-IP"))
            return HttpResponseRedirect("/immersion/login")

        form = HighSchoolStudentPassForm(instance=user)
        context = {
            'form': form,
        }

        return render(request, 'immersion/reset_password.html', context)

    else:
        del(request.session['user_id'])
        return HttpResponseRedirect("/immersion/login")


def activate(request, hash=None):
    if hash:
        try:
            user = ImmersionUser.objects.get(validation_string=hash)
            user.validate_account()
            messages.success(request, _("Your account is now enabled. Thanks !"))
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Invalid activation data"))
        except Exception as e:
            logger.exception("Activation error : %s", e)
            messages.error(request, _("Something went wrong"))

    return HttpResponseRedirect("/immersion/login")


def resend_activation(request):
    email = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()

        try:
            user = ImmersionUser.objects.get(email__iexact=email)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("No account found with this email address"))
        else:
            if user.is_valid():
                messages.error(request, _("This account has already been activated, please login."))
                return HttpResponseRedirect("/immersion/login")
            else:
                msg = user.send_message(request, 'CPT_MIN_CREATE_LYCEEN')
                messages.success(request, _("The activation message have been resent."))

    context = {
        'email': email
    }

    return render(request, 'immersion/resend_activation.html', context)


@login_required
def home(request):
    context = {
    }
    return render(request, 'immersion/home.html', context)


@login_required
def high_school_student_record(request, student_id=None, record_id=None):
    """
    High school student record
    """
    record = None
    student = None
    calendar = None
    
    calendars = Calendar.objects.all()   
    if calendars:
        calendar = calendars.first()
    
    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Invalid student id"))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if request.user.is_high_school_student():
        student = request.user
        record = student.get_high_school_student_record()

        if not record:
            record = HighSchoolStudentRecord(student=request.user)
    elif record_id:
        try:
            record = HighSchoolStudentRecord.objects.get(pk=record_id)
            student = HighSchoolStudentRecord.student
        except HighSchoolStudentRecord.DoesNotExist:
            pass

    if request.method == 'POST':
        current_email = student.email
        recordform = HighSchoolStudentRecordForm(request.POST, instance=record, request=request)
        studentform = HighSchoolStudentForm(request.POST, request=request, instance=student)

        if studentform.is_valid():
            student = studentform.save()

            if current_email != student.email:
                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')
                    messages.warning(request, _(
                        """You have updated your email."""
                        """<br>A new activation email has been sent, please check your messages."""))
                except Exception as e:
                    logger.exception("Cannot send 'change mail' message : %s", e)
        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            record = recordform.save()

            # Look for duplicated records
            if record.search_duplicates():
                messages.warning(request,
                    _("A record already exists with this identity, please contact the SCUIO-IP team."))

            if record.validation == 1:
                messages.success(request,
                    _("Thank you. Your record is awaiting validation from your high-school referent."))

        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        recordform = HighSchoolStudentRecordForm(request=request, instance=record)
        studentform = HighSchoolStudentForm(request=request, instance=student)

    context = {
        'calendar': calendar,
        'student_form': studentform,
        'record_form': recordform,
        'student': student
    }

    return render(request, 'immersion/hs_record.html', context)


@login_required
def student_record(request, student_id=None, record_id=None):
    """
    Student record
    """
    record = None
    student = None
    calendar = None
    
    calendars = Calendar.objects.all()   
    if calendars:
        calendar = calendars.first()

    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Invalid student id"))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if request.user.is_student():
        student = request.user
        record = student.get_student_record()

        if not record:
            record = StudentRecord(student=request.user)
    elif record_id:
        try:
            record = StudentRecord.objects.get(pk=record_id)
            student = StudentRecord.student
        except StudentRecord.DoesNotExist:
            pass

    if request.method == 'POST':
        current_email = student.email
        recordform = StudentRecordForm(request.POST, instance=record, request=request)
        studentform = StudentForm(request.POST, request=request, instance=student)

        if studentform.is_valid():
            student = studentform.save()

            if current_email != student.email:
                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')
                    messages.warning(request, _(
                        """You have updated your email."""
                        """<br>A new activation email has been sent, please check your messages."""))
                except Exception as e:
                    logger.exception("Cannot send 'change mail' message : %s", e)

        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            record = recordform.save()
        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        recordform = StudentRecordForm(request=request, instance=record)
        studentform = StudentForm(request=request, instance=student)

    context = {
        'calender': calendar,
        'student_form': studentform,
        'record_form': recordform,
        'student': student
    }

    return render(request, 'immersion/student_record.html', context)