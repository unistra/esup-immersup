import json
import logging
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Any, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import password_validators_help_text_html, validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, resolve
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, FormView

from shibboleth.decorators import login_optional
from shibboleth.middleware import ShibbolethRemoteUserMiddleware

from immersionlyceens.apps.core.models import (
    Calendar, CancelType, CertificateLogo, CertificateSignature, HigherEducationInstitution,
    Immersion, ImmersionUser, MailTemplate, UniversityYear, UserCourseAlert, HighSchoolLevel,
    PostBachelorLevel, StudentLevel
)
from immersionlyceens.apps.immersion.utils import generate_pdf
from immersionlyceens.decorators import groups_required
from immersionlyceens.libs.mails.variables_parser import parser
from immersionlyceens.libs.utils import check_active_year, get_general_setting

from .forms import (
    HighSchoolStudentForm, HighSchoolStudentRecordForm, LoginForm,
    NewPassForm, RegistrationForm, StudentForm, StudentRecordForm, VisitorRecordForm, VisitorForm,
)
from .models import HighSchoolStudentRecord, StudentRecord, VisitorRecord

logger = logging.getLogger(__name__)


def customLogin(request, profile=None):
    """
    Common login function for multiple users profiles
    :param request: request object
    :param profile: name of the profile (None = students)
    """
    # Clear all client sessions
    Session.objects.all().delete()

    is_reg_possible, is_year_valid, year = check_active_year()

    if not profile and (not year or not is_year_valid):
        messages.error(request, _("Sorry, the university year has not begun (or already over), you can't login yet."))

        context = {
            'start_date': year.start_date if year else None,
            'end_date': year.end_date if year else None,
            'reg_date': year.registration_start_date if year else None,
        }
        return render(request, 'immersion/nologin.html',context)

    if request.method == 'POST':
        form = LoginForm(request.POST, profile=profile)

        if form.is_valid():
            username = form.cleaned_data['login']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            print(f"USER: {user}")
            if user is not None:
                # Activated account ?
                if not user.is_valid():
                    messages.error(request, _("Your account hasn't been enabled yet."))
                else:
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    if user.is_high_school_student():
                        # If student has filled his record
                        if user.get_high_school_student_record():
                            return HttpResponseRedirect("/immersion")
                        else:
                            return HttpResponseRedirect("/immersion/hs_record")
                    elif user.is_visitor():
                        if user.get_visitor_record():
                            return HttpResponseRedirect("/immersion")
                        else:
                            return HttpResponseRedirect("/immersion/visitor_record")
                    elif user.is_high_school_manager() and user.highschool:
                        return HttpResponseRedirect(reverse('home'))
            else:
                messages.error(request, _("Authentication error"))
    else:
        form = LoginForm()

    context = {'form': form, 'profile': profile}

    return render(request, 'immersion/login.html', context)


class CustomLoginView(FormView):
    template_name: str = "immersion/login.html"
    invalid_no_login_template: str = "immersion/nologin.html"
    success_url = "/immersion/login2"
    form_class = LoginForm

    def get_form_kwargs(self):
        kwargs: Dict[str, Any] = super().get_form_kwargs()
        kwargs.update({"profile": self.kwargs.get("profile")})
        return kwargs

    def get_context_data(self, **kwargs):
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context.update({
            "profile": self.kwargs.get("profile"),
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        Session.objects.all().delete()

        profile: Optional[str] = self.kwargs.get("profile")
        is_reg_possible, is_year_valid, year = check_active_year()
        if not profile and (not year or not is_year_valid):
            self.invalid_year(year)

        return super().dispatch(request, *args, **kwargs)

    def invalid_year(self, year: UniversityYear):
        messages.error(self.request, _("Sorry, the university year has not begun (or already over), you can't login yet."))
        context = {
            'start_date': year.start_date if year else None,
            'end_date': year.end_date if year else None,
            'reg_date': year.registration_start_date if year else None,
        }
        return render(self.request, self.invalid_no_login_template, context)

    def form_valid(self, form):
        username = form.cleaned_data['login']
        password = form.cleaned_data['password']

        user: Optional[ImmersionUser] = authenticate(
            self.request, username=username, password=password)
        self.user = user
        if user is not None:
            if not user.is_valid():
                messages.error(self.request, _("Your account hasn't been enabled yet."))
                return self.form_invalid(form)
            else:
                login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        else:
            messages.error(self.request, _("Authentication error"))
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        if self.user.is_high_school_student():
            if self.user.get_high_school_student_record():
                return reverse("immersions")
            else:
                return reverse("hs_record")
        elif self.user.is_visitor():
            if self.user.get_visitor_record():
                return reverse("immersions")
            else:
                return reverse("visitor_record")
        elif self.user.is_high_school_manager() and self.user.highschool:
            return reverse('home')
        else:
            return super().get_success_url()


@login_optional
def shibbolethLogin(request, profile=None):
    """
    """
    shib_attrs, error = ShibbolethRemoteUserMiddleware.parse_attributes(request)

    if error:
        messages.error(request, _("Incomplete data for account creation"))
        return HttpResponseRedirect("/")
    elif not all([value[1] in shib_attrs for value in settings.SHIBBOLETH_ATTRIBUTE_MAP.values()]):
        messages.error(request,
            _("Missing attributes, account not created." +
             "<br>Your institution may not be aware of the Immersion service." +
             "<br>Please use the 'contact' link at the bottom of this page, specifying your institution."))
        return HttpResponseRedirect("/")


    if request.POST.get('submit'):
        shib_attrs.pop("uai_code", None)
        new_user = ImmersionUser.objects.create(**shib_attrs)
        new_user.set_validation_string()
        new_user.destruction_date = datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
        new_user.save()

        try:
            Group.objects.get(name='ETU').user_set.add(new_user)
        except Exception:
            logger.exception(f"Cannot add 'ETU' group to user {new_user}")
            messages.error(request, _("Group error"))

        try:
            msg = new_user.send_message(request, 'CPT_MIN_CREATE_ETU')
        except Exception as e:
            logger.exception("Cannot send activation message : %s", e)

        messages.success(request, _("Account created. Please look at your emails for the activation procedure."))
        return HttpResponseRedirect("/")


    if request.user.is_anonymous:
        context = shib_attrs
        return render(request, "immersion/confirm_creation.html", context)
    else:
        # Activated account ?
        if not request.user.is_valid():
            messages.error(request, _("Your account hasn't been enabled yet."))
        else:
            if request.user.is_student():
                # If student has filled his record
                if request.user.get_student_record():
                    return HttpResponseRedirect("/immersion")
                else:
                    return HttpResponseRedirect("/immersion/student_record")

    return HttpResponseRedirect("/")


def register(request):
    # Is current university year valid ?
    is_reg_possible, is_year_valid, year = check_active_year()

    if not year or not is_reg_possible:
        messages.warning(request, _("Sorry, you can't register right now."))
        context = {
            'start_date': year.start_date if year else None,
            'end_date': year.end_date if year else None,
            'reg_date': year.registration_start_date if year else None,
        }
        return render(request, 'immersion/nologin.html', context)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            new_user = form.save(commit=False)
            # adjustments here
            new_user.username = form.cleaned_data.get("username")
            new_user.set_validation_string()
            new_user.destruction_date = datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
            new_user.save()

            try:
                Group.objects.get(name='LYC').user_set.add(new_user)
            except Exception:
                logger.exception(f"Cannot add 'LYC' group to user {new_user}")
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

    context = {'form': form}

    return render(request, 'immersion/registration.html', context)


def recovery(request):
    email = ""

    if request.method == "POST":
        email = request.POST.get('email', '').strip().lower()

        try:
            user = ImmersionUser.objects.get(email__iexact=email)

            if not user.username.startswith(settings.USERNAME_PREFIX) and not user.is_high_school_manager():
                messages.warning(request, _("Please use your establishment credentials."))
            else:
                user.set_recovery_string()
                msg = user.send_message(request, 'CPT_MIN_ID_OUBLIE')
                messages.success(request, _("An email has been sent with the procedure to set a new password."))

        except ImmersionUser.DoesNotExist:
            messages.error(request, _("No account found with this email address"))
        except ImmersionUser.MultipleObjectsReturned:
            messages.error(request, _("Error : please contact the establishment referent"))

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

            # TODO : add validators
            # TODO : use Django password form ?
            form = NewPassForm(request.POST, instance=user)

            if form.is_valid():
                user = form.save()
                user.recovery_string = None
                user.save()
                messages.success(request, _("Password successfully updated."))

                # Different login redirection, depending on user group
                return HttpResponseRedirect(user.get_login_page())

            return render(request, 'immersion/reset_password.html', {'form': form})
    elif hash:
        try:
            user = ImmersionUser.objects.get(recovery_string=hash)
            request.session['user_id'] = user.id
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Password recovery : invalid data"))
            return HttpResponseRedirect("/immersion/login")
        except ImmersionUser.MultipleObjectsReturned:
            messages.error(request, _("Error : please contact the establishment referent"))
            return HttpResponseRedirect("/immersion/login")

        form = NewPassForm(instance=user)
        context = {
            'form': form,
        }

        return render(request, 'immersion/reset_password.html', context)

    else:
        del request.session['user_id']
        return HttpResponseRedirect("/immersion/login")


@login_required
@groups_required("LYC", "REF-LYC")
def change_password(request):
    """
    Change password view for high-school students and high-school managers
    """
    if request.method == "POST":
        password_form = PasswordChangeForm(data=request.POST, user=request.user)

        try:
            validate_password(request.POST.get('new_password1'))
        except ValidationError as e:
            pass

        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, _("Password successfully updated"))
        else:
            for err_field, err_list in password_form.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

    else:
        password_form = PasswordChangeForm(request.user)
        messages.info(request, password_validators_help_text_html())

    context = {
        'form': password_form,
    }

    return render(request, 'immersion/change_password.html', context)


def activate(request, hash=None):
    if hash:
        try:
            user = ImmersionUser.objects.get(validation_string=hash)
            user.validate_account()
            messages.success(request, _("Your account is now enabled. Thanks !"))

            if user.is_student():
                return HttpResponseRedirect("/shib")

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

    context = {'email': email}

    return render(request, 'immersion/resend_activation.html', context)


@login_required
def home(request):
    context = {}
    return render(request, 'immersion/home.html', context)


@login_required
@groups_required('REF-ETAB-MAITRE', 'REF-ETAB', 'LYC', 'REF-TEC')
def high_school_student_record(request, student_id=None, record_id=None):
    """
    High school student record
    """
    template_name: str = 'immersion/hs_record.html'
    record = None
    student = None
    calendar = None

    calendars = Calendar.objects.all()

    if calendars:
        calendar = calendars.first()

    # Unused ?
    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Invalid student id"))
            return HttpResponseRedirect(request.headers.get('Referer', '/'))

    if request.user.is_high_school_student():
        student = request.user
        record = student.get_high_school_student_record()

        if not record:
            record = HighSchoolStudentRecord(
                student=request.user,
                allowed_global_registrations=calendar.year_nb_authorized_immersion,
                allowed_first_semester_registrations=calendar.nb_authorized_immersion_per_semester,
                allowed_second_semester_registrations=calendar.nb_authorized_immersion_per_semester,
            )
    elif record_id:
        try:
            record = HighSchoolStudentRecord.objects.get(pk=record_id)
            student = record.student
        except HighSchoolStudentRecord.DoesNotExist:
            pass

    if request.method == 'POST' and request.POST.get('submit'):
        student_id = request.POST.get('student', None)
        if not student and student_id:
            try:
                student = ImmersionUser.objects.get(id=int(student_id))
                record = student.get_high_school_student_record()
            except ImmersionUser.DoesNotExist:
                messages.error(request, _("Invalid student id"))
                return HttpResponseRedirect(request.headers.get('Referer', '/'))

        current_email = student.email
        try:
            current_highschool = record.highschool.id
        except Exception:
            current_highschool = None

        recordform = HighSchoolStudentRecordForm(request.POST, instance=record, request=request)
        studentform = HighSchoolStudentForm(request.POST, instance=student, request=request)

        if studentform.is_valid():
            student = studentform.save()

            if current_email != student.email:
                student.username = settings.USERNAME_PREFIX + student.email
                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')
                    messages.warning(
                        request,
                        _(
                            """You have updated the email."""
                            """<br>Warning : the new email is also the new login."""
                            """<br>A new activation email has been sent."""
                        ),
                    )
                except Exception as e:
                    logger.exception("Cannot send 'change mail' message : %s", e)
        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            record = recordform.save()

            if current_highschool and current_highschool != record.highschool.id:
                record.validation = 1
                record.save()
                messages.info(request, _("You have changed the high school, your record needs a new validation"))

            # Look for duplicated records
            if record.search_duplicates():
                if request.user.is_high_school_student():
                    messages.warning(
                        request,
                        _("A record already exists with this identity, please contact the establishment referent.")
                    )
                else:
                    messages.warning(
                        request, _("A record already exists with this identity, look at duplicate records.")
                    )

            if record.validation == 1:
                if request.user.is_high_school_student():
                    messages.success(
                        request, _("Thank you. Your record is awaiting validation from your high-school referent.")
                    )

            messages.success(request, _("Record successfully saved."))

        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        request.session['back'] = request.headers.get('Referer')
        recordform = HighSchoolStudentRecordForm(request=request, instance=record)
        studentform = HighSchoolStudentForm(request=request, instance=student)

        messages.info(request, _("Current record status : %s") % record.get_validation_display())

    # Stats for user deletion
    today = datetime.today().date()
    now = datetime.today().time()

    past_immersions = student.immersions.filter(
        Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
    ).count()

    future_immersions = student.immersions.filter(
        Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
    ).count()

    context = {
        'calendar': calendar,
        'student_form': studentform,
        'record_form': recordform,
        'student': student,
        'record': record,
        'back_url': request.session.get('back'),
        'past_immersions': past_immersions,
        'future_immersions': future_immersions,
        'high_school_levels': json.dumps(
            {l.id: {
                'is_post_bachelor': l.is_post_bachelor,
                'requires_bachelor_speciality': l.requires_bachelor_speciality
            } for l in HighSchoolLevel.objects.all()}
        )
    }

    return render(request, template_name, context)


@login_required
@groups_required('REF-ETAB-MAITRE', 'REF-ETAB', 'REF-TEC', 'ETU')
def student_record(request, student_id=None, record_id=None):
    """
    Student record
    """
    template_name: str = 'immersion/student_record.html'
    record = None
    student = None
    calendar = None

    calendars = Calendar.objects.all()
    if calendars:
        calendar = calendars.first()

    # Unused ?
    if student_id:
        try:
            student = ImmersionUser.objects.get(pk=student_id)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("Invalid student id"))
            return HttpResponseRedirect(request.headers.get('Referer', '/'))

    if request.user.is_student():
        student = request.user
        record = student.get_student_record()
        uai_code = None

        try:
            shib_attrs = request.session.get("shib", {})
            uai_code = shib_attrs.get("uai_code")
        except Exception:
            logger.error("Cannot retrieve uai code from shibboleth data")

        if uai_code and uai_code.startswith('{UAI}'):
            uai_code = uai_code.replace('{UAI}', '')

        if not record:
            record = StudentRecord(
                student=request.user,
                uai_code=uai_code,
                allowed_global_registrations=calendar.year_nb_authorized_immersion,
                allowed_first_semester_registrations=calendar.nb_authorized_immersion_per_semester,
                allowed_second_semester_registrations=calendar.nb_authorized_immersion_per_semester,
            )
        elif uai_code and record.uai_code != uai_code:
            record.uai_code = uai_code
            record.save()
    elif record_id:
        try:
            record = StudentRecord.objects.get(pk=record_id)
            student = record.student
        except StudentRecord.DoesNotExist:
            pass

    if request.method == 'POST':
        student_id = request.POST.get('student', None)
        if not student and student_id:
            try:
                student = ImmersionUser.objects.get(id=int(student_id))
                record = student.get_student_record()
            except ImmersionUser.DoesNotExist:
                messages.error(request, _("Invalid student id"))
                return HttpResponseRedirect(request.headers.get('Referer', '/'))

        current_email = student.email
        recordform = StudentRecordForm(request.POST, instance=record, request=request)
        studentform = StudentForm(request.POST, request=request, instance=student)

        if studentform.is_valid():
            student = studentform.save()

            if current_email != student.email:
                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')
                    messages.warning(
                        request, _("""You have updated the email.""" """<br>A new activation email has been sent.""")
                    )
                except Exception as e:
                    logger.exception("Cannot send 'change mail' message : %s", e)

        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            record = recordform.save()

            messages.success(request, _("Record successfully saved."))
        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        request.session['back'] = request.headers.get('Referer')
        recordform = StudentRecordForm(request=request, instance=record)
        studentform = StudentForm(request=request, instance=student)

    # Stats for user deletion
    today = datetime.today().date()
    now = datetime.today().time()

    past_immersions = student.immersions.filter(
        Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
    ).count()

    future_immersions = student.immersions.filter(
        Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
    ).count()

    context = {
        'calender': calendar,
        'student_form': studentform,
        'record_form': recordform,
        'record': record,
        'student': student,
        'back_url': request.session.get('back'),
        'past_immersions': past_immersions,
        'future_immersions': future_immersions,
    }

    return render(request, template_name, context)


@login_required
@groups_required('LYC', 'ETU')
def immersions(request):
    """
    Students : display to come, past and cancelled immersions
    Also display the number of active alerts
    """
    cancellation_reasons = CancelType.objects.filter(active=True).order_by('label')
    alerts = UserCourseAlert.objects.filter(email=request.user.email)
    not_sent_alerts_cnt = alerts.filter(email_sent=False).count()
    sent_alerts_cnt = alerts.filter(email_sent=True).count()

    context = {
        'cancellation_reasons': cancellation_reasons,
        'alerts_cnt': alerts.count(),
        'not_sent_alerts_cnt': not_sent_alerts_cnt,
        'sent_alerts_cnt': sent_alerts_cnt,
    }

    return render(request, 'immersion/my_immersions.html', context)


@login_required
@groups_required('LYC', 'ETU', 'REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC')
def immersion_attestation_download(request, immersion_id):
    """
    Attestation download
    """
    try:
        immersion = Immersion.objects.prefetch_related(
            'slot__course__training', 'slot__course_type', 'slot__campus', 'slot__building', 'slot__speakers',
        ).get(pk=immersion_id, attendance_status=1)

        student = immersion.student

        tpl = MailTemplate.objects.get(code='CERTIFICATE_BODY', active=True)
        certificate_body = parser(
            user=student,
            request=request,
            message_body=tpl.body,
            vars=[v for v in tpl.available_vars.all()],
            immersion=immersion,
            slot=immersion.slot,
        )

        certificate_logo = CertificateLogo.objects.get(pk=1)
        certificate_sig = CertificateSignature.objects.get(pk=1)

        context = {
            'city': get_general_setting('PDF_CERTIFICATE_CITY'),
            'certificate_header': MailTemplate.objects.get(code='CERTIFICATE_HEADER', active=True).body,
            'certificate_body': certificate_body,
            'certificate_footer': MailTemplate.objects.get(code='CERTIFICATE_FOOTER', active=True).body,
            'certificate_logo': certificate_logo,
            'certificate_sig': certificate_sig,
        }

        filename = f'immersion_{date_format(immersion.slot.date,"dmY")}_{student.last_name}_{student.first_name}.pdf'
        response = generate_pdf(request, 'export/pdf/attendance_certificate.html', context, filename=filename)

        return response
    # TODO: Manage Mailtemplate not found (?) anyway returns 404
    except Exception as e:
        logger.error('Certificate download error', e)
        raise Http404()


@method_decorator(groups_required('VIS', 'REF-ETAB', 'REF-ETAB-MAITRE'), name="dispatch")
class VisitorRecordView(FormView):
    template_name = "immersion/visitor_record.html"
    form_class = VisitorRecordForm

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["request"] = self.request
        record_id: Optional[int] = self.kwargs.get("record_id")

        if self.request.user.is_visitor():
            record = self.request.user.get_visitor_record()
            if record:
                form_kwargs["instance"] = record
        elif record_id:
            try:
                record: VisitorRecord = VisitorRecord.objects.get(id=record_id)
                form_kwargs["instance"] = record
            except VisitorRecord.DoesNotExist:
                # todo: handle it
                pass

        return form_kwargs

    def get_context_data(self, **kwargs):
        context: Dict[str, Any] = super().get_context_data()
        record_id: Optional[int] = self.kwargs.get("record_id")
        user_form: Optional[VisitorForm] = None
        visitor: Optional[ImmersionUser] = None
        record: Optional[VisitorRecordForm] = None
        hash_change_permission = any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ])

        calendars: QuerySet = Calendar.objects.all()
        calendar: Optional[Calendar] = None
        if calendars:
            calendar = calendars.first()

        if self.request.user.is_visitor():
            visitor = self.request.user
            record = visitor.get_visitor_record()
            if record:
                messages.info(self.request, _("Current record status : %s") % record.get_validation_display())
            user_form = VisitorForm(request=self.request, instance=visitor)
        elif record_id:
            try:
                record: VisitorRecord = VisitorRecord.objects.get(pk=record_id)
            except VisitorRecord.DoesNotExist:
                messages.error(self.request, _("Invalid visitor record id"))
                raise Http404
            visitor = record.visitor
            form_kwargs = self.get_form_kwargs()
            if "data" in form_kwargs:
                user_form = VisitorForm(form_kwargs, instance=visitor, request=self.request)
            else:
                user_form = VisitorForm(instance=visitor, request=self.request)


        # Stats for user deletion
        today = datetime.today().date()
        now = datetime.today().time()
        past_immersions = visitor.immersions.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
        ).count()
        future_immersions = visitor.immersions.filter(
            Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
        ).count()

        if record:
            context.update({"record": record})  # for modal nuke purpose
        context.update({
            "past_immersions": past_immersions, "future_immersions": future_immersions,
            "visitor": visitor, "student": visitor,  # visitor = student for modal nuke purpose
            "user_form": user_form,
            "back_url": self.request.session.get("back"),
            "calendar": calendar,
            "can_change": hash_change_permission,  # can change number of allowed positions
        })
        return context

    def email_changed(self, user: ImmersionUser):
        user.username = settings.USERNAME_PREFIX + user.email
        user.set_validation_string()

        try:
            msg = user.send_message(self.request, "CPT_MIN_CHANGE_MAIL")
            messages.warning(
                self.request,
                _(
                    """You have updated the email."""
                    """<br>Warning : the new email is also the new login."""
                    """<br>A new activation email has been sent."""
                ),
            )
        except Exception as exc:
            logger.exception("Cannot send 'change mail' message : %s", exc)

    def post(self, request, *args, **kwargs):
        # multi validation for multiple form
        form = self.get_form()
        form_user: VisitorForm
        record_id: Optional[int] = self.kwargs.get("record_id")
        current_email: Optional[str] = None
        user: Optional[ImmersionUser] = None

        if request.user.is_visitor():
            user = request.user
            form_user = VisitorForm(request.POST, request.FILES , instance=request.user, request=request, )
        elif record_id:
            record: Optional[VisitorRecord] = VisitorRecord.objects.get(pk=record_id)
            user = record.visitor
            form_user = VisitorForm(request.POST, request.FILES, instance=record.visitor, request=request)
        else:
            form_user = VisitorForm(request.POST, request.FILES, request=request)

        if user:
            current_email = user.email

        if form.is_valid() and form_user.is_valid():
            form.save()
            saved_user = form_user.save()

            if current_email != saved_user.email:
                self.email_changed(saved_user)

            return self.form_valid(form)
        else:
            for form_ in (form, form_user):
                for err_field, err_list in form_.errors.get_json_data().items():
                    for error in err_list:
                        if error.get("message"):
                            messages.error(self.request, error.get("message"))
                            print(f'err: {error.get("message")} ==> {form_.__class__}')

            return self.form_invalid(form)

    def get_success_url(self) -> str:
        if self.request.user.is_visitor():
            return reverse("immersion:visitor_record")
        else:
            return reverse("immersion:visitor_record_by_id", kwargs=self.kwargs)
