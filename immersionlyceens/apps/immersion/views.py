import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, Optional
from functools import reduce
import requests

from django import forms
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import (
    authenticate, login, update_session_auth_hash, views as auth_views,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import (
    password_validators_help_text_html, validate_password,
)
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q, QuerySet
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from shibboleth.decorators import login_optional
from shibboleth.middleware import ShibbolethRemoteUserMiddleware

try:
    from django.utils.six.moves.urllib.parse import quote
except ImportError:
    from urllib.parse import quote

from shibboleth.app_settings import LOGOUT_URL, LOGOUT_REDIRECT_URL


from immersionlyceens.apps.core.models import (
    AttestationDocument, BachelorType, CancelType, CertificateLogo,
    CertificateSignature, GeneralSettings, HigherEducationInstitution,
    HighSchool, HighSchoolLevel, Immersion, ImmersionUser, InformationText,
    MailTemplate, MefStat, PendingUserGroup, Period, Slot, UniversityYear,
    UserCourseAlert,
)
from immersionlyceens.apps.immersion.utils import generate_pdf
from immersionlyceens.decorators import groups_required
from immersionlyceens.libs.mails.variables_parser import parser
from immersionlyceens.libs.utils import check_active_year, get_general_setting

from .forms import (
    EmailForm, HighSchoolStudentForm, HighSchoolStudentRecordDocumentForm,
    HighSchoolStudentRecordForm, HighSchoolStudentRecordQuotaForm, LoginForm,
    NewPassForm, RegistrationForm, StudentForm, StudentRecordForm,
    StudentRecordQuotaForm, VisitorForm, VisitorRecordDocumentForm,
    VisitorRecordForm, VisitorRecordQuotaForm,
)
from .models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument,
    HighSchoolStudentRecordQuota, StudentRecord, StudentRecordQuota,
    VisitorRecord, VisitorRecordDocument, VisitorRecordQuota,
)

logger = logging.getLogger(__name__)

class CustomShibbolethLogoutView(TemplateView):
    """
    Logout app and shibboleth
    Use custom logout url when needed
    Borrowed code from django-shibboleth-remoteuser
    """
    redirect_field_name = "target"

    def get(self, request, *args, **kwargs):
        # Default shibboleth logout URL
        logout_url = LOGOUT_URL
        logout = None
        target = ""

        if self.request.user and not self.request.user.is_anonymous:
            if self.request.user.is_high_school_student() and self.request.user.uses_federation():
                # high school student
                logout = settings.EDUCONNECT_LOGOUT_URL
                # logger.error(f"EDUCONNECT_LOGOUT_URL : logout url : {logout}")
            elif self.request.user.uses_federation():
                # speakers and high school referents
                logout = settings.AGENT_FEDERATION_LOGOUT_URL
                # logger.error(f"AGENT_FEDERATION_URL : logout url : {logout}")
            else:
                # Get target url in order of preference.
                target = LOGOUT_REDIRECT_URL or \
                         quote(self.request.GET.get(self.redirect_field_name, '')) or \
                         quote(request.build_absolute_uri())

                logout = logout_url % target
                # logger.error(f"logout url : {logout}")

        if not logout:
            logout = logout_url % ''

        # Log the user out.
        auth.logout(self.request)
        return redirect(logout)


class CustomLoginView(FormView):
    template_name: str = "immersion/login.html"
    invalid_no_login_template: str = "immersion/nologin.html"
    success_url = "/immersion/login"
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
        username = form.cleaned_data['login'].strip().lower()
        password = form.cleaned_data['password']

        # Must use federation ?
        try:
            user = ImmersionUser.objects.get(username=username)

            if (user.is_high_school_manager() or user.is_speaker()) and user.uses_federation():
                messages.error(self.request, _("Please use the Agent Federation to authenticate"))
                return self.form_invalid(form)

            if user.is_high_school_student() and user.uses_federation():
                messages.error(self.request, _("Please use EduConnect to authenticate"))
                return self.form_invalid(form)

        except ImmersionUser.DoesNotExist:
            # let 'authenticate' below handle the issue
            pass

        user: Optional[ImmersionUser] = authenticate(self.request, username=username, password=password)

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
        go_home = [
            self.user.is_high_school_manager() and self.user.highschool,
            self.user.is_speaker(),
            self.user.is_establishment_manager(),
            self.user.is_structure_manager(),
            self.user.is_high_school_manager(),
            self.user.is_legal_department_staff(),
        ]

        if self.user.is_high_school_student():
            record = self.user.get_high_school_student_record()

            if not record or record.validation in [HighSchoolStudentRecord.INIT, HighSchoolStudentRecord.TO_COMPLETE]:
                return "/immersion/hs_record"
            return reverse('home')
        elif self.user.is_visitor():
            return reverse('home') if self.user.get_visitor_record() else "/immersion/visitor_record"
        elif any(go_home):
            return reverse('home')
        else:
            return super().get_success_url()


def loginChoice(request, profile=None):
    """
    :param request:
    :param profile:
    :return:
    """
    intro_connection_code = None
    intro_connection = ""
    is_reg_possible, is_year_valid, year = check_active_year()

    if not year or not is_reg_possible:
        return redirect(reverse('immersion:register'), profile=profile)

    match profile:
        case 'lyc':
            federation_name = _("EduConnect")
            intro_connection_code = "INTRO_HIGHSCHOOL_CONNECTION"
        case 'ref-lyc':
            federation_name = _("the agent federation")
            intro_connection_code = "INTRO_AGENT_CONNECTION"
        case 'speaker':
            federation_name = _("the agent federation")
            intro_connection_code = "INTRO_AGENT_CONNECTION"
        case _:
            federation_name = ''

    if federation_name and intro_connection_code:
        try:
            intro_connection = InformationText.objects.get(code=intro_connection_code, active=True).content
        except InformationText.DoesNotExist:
            intro_connection = ""

    context = {
        'federation_name': federation_name,
        'profile': profile,
        'intro_connection': intro_connection
    }

    template = "immersion/login_choice.html" if federation_name else "immersion/login.html"

    return render(request, template, context)


@login_optional
def shibbolethLogin(request, profile=None):
    """
    """
    enabled_students = get_general_setting('ACTIVATE_STUDENTS')
    enabled_student_federation = get_general_setting('ACTIVATE_EDUCONNECT')
    enabled_agent_federation = get_general_setting('ACTIVATE_FEDERATION_AGENT')
    group_name = None
    record_highschool = None
    level = None

    shib_attrs, error = ShibbolethRemoteUserMiddleware.parse_attributes(request)

    """
    # --------------- <shib dev> ----------------------
    # Uncomment this to fake Shibboleth data for DEV purpose
    hs = HighSchool.objects.filter(uses_student_federation=True,active=True,uai_codes__isnull=False).first()
    shib_attrs.update({
        "username": "https://pr4.educonnect.phm.education.gouv.fr/idp!https://immersup-test.app.unistra.fr!TGZM3VDBINLJTQMX4DJ23XYLYK43HVNO",
        "first_name": "Jean-Jacques",
        "last_name": "TEST",
        "uai_code": f"{{UAI}}{hs.uai_codes.first().code}",
        "etu_stage": "{SIREN:110043015:MEFSTAT4}2212",
        "birth_date": "2005-05-07",
        "unscoped_affiliation": "student"
    })
    # --------------- </shib dev> ----------------------
    """
    
    if error:
        logger.error(f"Shibboleth error : {error}")
        messages.error(request, _("Incomplete data for account creation"))
        return HttpResponseRedirect("/")

    # Defaults
    mandatory_attributes = [
        "username",
        "first_name",
        "last_name",
        "email",
    ]

    student_attribute = [
        "uai_code"
    ]

    high_school_student_attribute = [
        "birth_date",
        "etu_stage",
        "uai_code"
    ]

    one_of_affiliations = [
        "affiliation",
        "unscoped_affiliation",
        "primary_affiliation",
    ]

    optional_attributes = []


    # Extract all affiliations, clean empty lists and remove scopes (something@domain)
    try:
        affiliations = set(
            map(lambda a:a.partition('@')[0],
                reduce(
                    lambda a,b:a+b,
                    filter(
                        lambda a: a != [''],
                        [shib_attrs.pop(attr, '').split(";") for attr in one_of_affiliations]
                    )
                )
            )
        )
    except Exception as e:
        logger.warning(e)
        affiliations = []

    is_high_school_student = False
    is_student = False

    if "student" in affiliations:
        """
        Can be a student or a high school student
        """
        # Common field for students and high school students
        uai_code = shib_attrs.get("uai_code", "")

        if shib_attrs.get('birth_date'):
            # High school student using EduConnect : email becomes optional
            # TODO : identify EduConnect users with another meta HTTP var
            is_high_school_student = True
            optional_attributes.append('email')
            mandatory_attributes.remove('email')
            mandatory_attributes += high_school_student_attribute
            group_name = 'LYC'

            # Don't keep the email address
            shib_attrs.pop('email', None)

            # Check allowed etu_stages
            try:
                etu_stage = shib_attrs.get('etu_stage').split("}")[1]
            except:
                # Not found or incorrect
                etu_stage = ""

            try:
                mefstat = MefStat.objects.get(code__iexact=etu_stage, level__active=True)
                level = mefstat.level
            except MefStat.DoesNotExist:
                messages.error(
                    request,
                    _("Sorry, your high school level does not allow you to register or connect to this platform.")
                )

                return HttpResponseRedirect("/")

            # Check UAI
            try:
                clean_uai_code = uai_code.replace('{UAI}', '')
                record_highschool = HighSchool.objects.get(
                    Q(uai_codes=uai_code)|Q(uai_codes=clean_uai_code),
                    uses_student_federation=True
                )
            except HighSchool.DoesNotExist as e:
                return render(request, 'immersion/missing_hs.html', {})

        else:
            is_student = True
            mandatory_attributes += student_attribute
            group_name = 'ETU'
    else:
        shib_attrs['username'] = shib_attrs.get('email', None)

    if not is_high_school_student:
        # Attributes cleaning
        try:
            shib_attrs['username'] = shib_attrs['username'].strip().lower()
            shib_attrs['email'] = shib_attrs['email'].strip().lower()
        except:
            # KeyError ? nothing to do
            pass

    # parse affiliations:
    if not all([attr in shib_attrs for attr in mandatory_attributes]) or not affiliations:
        messages.error(request,
            _("Missing attributes, account not created." +
             "<br>Your institution may not be aware of the Immersion service." +
             "<br>Please use the 'contact' link at the bottom of this page, specifying your institution."))
        return HttpResponseRedirect("/")

    is_employee = not is_student and not is_high_school_student

    # Account creation confirmed
    if request.POST.get('submit'):
        if is_student and not enabled_students:
            messages.error(request, _("Students deactivated"))
            return HttpResponseRedirect("/")

        if is_high_school_student:
            # replace email with a unique string
            shib_attrs['email'] = uuid.uuid4().hex

        # Store unneeded attributes from shib_attrs for account creation
        other_fields = {
            k: shib_attrs.pop(k, '') for k in ['uai_code', 'birth_date', 'etu_stage']
        }

        new_user = ImmersionUser.objects.create(**shib_attrs)
        new_user.set_validation_string()
        new_user.destruction_date = datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
        new_user.save()

        # Add group
        try:
            Group.objects.get(name=group_name).user_set.add(new_user)
        except Exception:
            logger.exception(f"Cannot add '{group_name}' group to user {new_user}")
            messages.error(request, _("Group error"))

        if is_high_school_student:
            # validation=HighSchoolStudentRecord.TO_COMPLETE
            HighSchoolStudentRecord.objects.create(
                highschool=record_highschool,
                student=new_user,
                level=level,
                birth_date=other_fields.get('birth_date', None),
                validation=HighSchoolStudentRecord.INIT
            )

        new_user = authenticate(request, remote_user=new_user.username, shib_meta=shib_attrs)
        if new_user:
            request.user = new_user
            login(request, new_user)

        # A high school user may not have an email yet
        if not is_high_school_student and shib_attrs.get("email"):
            try:
                msg = new_user.send_message(request, 'CPT_MIN_CREATE')

                if msg:
                    messages.error(request, _("Cannot send email. The administrators have been notified."))
                    logger.error(f"Error while sending activation email : {msg}")
            except Exception as e:
                messages.error(request, _("Cannot send email. The administrators have been notified."))
                logger.exception("Cannot send activation message : %s", e)

            messages.success(request, _("Account created. Please check your emails for the activation procedure."))
            return HttpResponseRedirect("/")
        else:
            messages.success(
                request,
                _("Your account is almost ready, please enter you email address for the activation procedure")
            )
            return HttpResponseRedirect("/immersion/set_email")


    # The account does not exist yet
    # -> auto-creation for students and high school students after confirmation
    # -> must have been created first for managers (high school, structure, ...)

    # Already authenticated ?
    is_authenticated = request.user.is_authenticated
    user = authenticate(request, remote_user=shib_attrs.get("username"), shib_meta=shib_attrs)

    if user:
        request.user = user
        login(request, user)

    if request.user.is_anonymous:
        err = None

        if is_employee:
            err = _("Your account must be first created by a master establishment manager or an operator.")
        elif not is_student and not is_high_school_student:
            err = _("The attributes sent by Shibboleth show you may not be a student.")

        if err:
            err += _("<br>If you think this is a mistake, please use the 'contact' link at the " +
                     "<br>bottom of this page, specifying your institution.")
            messages.error(request, err)
            return HttpResponseRedirect("/")

        context = shib_attrs
        return render(request, "immersion/confirm_creation.html", context)
    else:
        # Check if user high school uses agent federation
        if request.user.highschool and not request.user.uses_federation():
            err = _("You can't access this application with the agent federation, please use your local credentials.")
            messages.error(request, err)
            profile = "ref_lyc" if request.user.is_high_school_manager() else "inter"
            auth.logout(request)
            return HttpResponseRedirect(f"/immersion/login/{profile}")

        # Update user attributes
        try:
            user = ImmersionUser.objects.get(username=shib_attrs["username"])
            user.last_name = shib_attrs["last_name"]
            user.first_name = shib_attrs["first_name"]

            # Update birthdate for high school students
            if shib_attrs.get("birth_date", None) and user.is_high_school_student():
                record = user.get_high_school_student_record()
                if record:
                    record.birth_date = shib_attrs.get("birth_date")

            if not user.is_high_school_student():
                user.email = shib_attrs["email"]

            user.username = shib_attrs["username"]
            user.save()
        except (ImmersionUser.DoesNotExist, KeyError):
            err = _("Unable to find a matching user in database")
            return HttpResponseRedirect("/")

        # Activated account ?
        if not request.user.is_valid():
            # high school student and invalid email ? redirect to set_email
            if request.user.is_high_school_student():
                try:
                    validate_email(request.user.email)
                except ValidationError as e:
                    messages.success(
                        request,
                        _("Your account is almost ready, please enter you email address for the activation procedure")
                    )
                    return HttpResponseRedirect("/immersion/set_email")

            return render(request, 'immersion/activation_needed.html', {})
        else:
            # Existing account or external student
            staff_accounts = [
                request.user.is_operator(),
                request.user.is_master_establishment_manager(),
                request.user.is_establishment_manager(),
                request.user.is_structure_manager(),
                request.user.is_structure_manager(),
                request.user.is_speaker(),
            ]

            if is_employee and any(staff_accounts):
                return HttpResponseRedirect("/")

            elif is_student and request.user.is_student():
                # If student has filled his record
                if request.user.get_student_record():
                    return HttpResponseRedirect("/")
                else:
                    return HttpResponseRedirect("/immersion/student_record")

            elif is_high_school_student and request.user.is_high_school_student():
                return HttpResponseRedirect("/immersion/hs_record")

    return HttpResponseRedirect("/")


@login_required
@groups_required("LYC")
def setEmail(request):
    """
    This form must be used by high school students after first connection from EduConnect
    to add their email to their account
    """
    redirect_url_name: str = "/"

    if (not request.user or not request.user.get_high_school_student_record()
            or not request.user.high_school_student_record.highschool
            or not request.user.high_school_student_record.highschool.uses_student_federation):
        return HttpResponseRedirect(redirect_url_name)

    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_validation_string()
            user.destruction_date = datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
            user.save()

            user.refresh_from_db()

            try:
                msg = user.send_message(request, 'CPT_MIN_CREATE')

                if msg:
                    messages.error(request, _("Cannot send email. The administrators have been notified."))
                    logger.error(f"Error while sending activation email : {msg}")
                else:
                    return render(request, 'immersion/complete.html', {})
            except Exception as e:
                logger.exception("Cannot send activation message : %s", e)
                messages.error(request, _("Cannot send email. The administrators have been notified."))

            # force logout of the user ?
            # auth.logout(request)

            return HttpResponseRedirect(reverse('home'))
        else:
            for err_field, err_list in form.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        form = EmailForm(request=request, instance=request.user)

    context = {
        'form': form,
    }

    return render(request, 'immersion/email_form.html', context)


def register(request, profile=None):
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
        redirect_url_name: str = "/immersion/login"

        registration_type: Optional[str] = request.POST.get("registration_type")

        if form.is_valid():
            new_user = form.save(commit=False)
            # adjustments here
            new_user.username = form.cleaned_data.get("username").strip().lower()
            new_user.set_validation_string()
            new_user.destruction_date = datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
            new_user.save()

            new_user.refresh_from_db()

            # High school selected : create the Record
            record_highschool = form.cleaned_data.get('record_highschool')

            if record_highschool:
                HighSchoolStudentRecord.objects.create(
                    highschool=record_highschool,
                    student=new_user,
                    validation = HighSchoolStudentRecord.INIT
                )

            group_name: str = "LYC"

            try:
                if get_general_setting('ACTIVATE_VISITORS') and registration_type == "vis":
                    group_name = "VIS"
            except:
                # Should only happen if ACTIVATE_VISITORS setting is not present
                pass

            try:
                Group.objects.get(name=group_name).user_set.add(new_user)
            except Exception:
                logger.exception(f"Cannot add '{group_name}' group to user {new_user}")
                messages.error(request, _("Group error"))

            try:
                msg = new_user.send_message(request, 'CPT_MIN_CREATE')

                if msg:
                    messages.error(request, _("Cannot send email. The administrators have been notified."))
                    logger.error(f"Error while sending activation email : {msg}")
            except Exception as e:
                logger.exception("Cannot send activation message : %s", e)
                messages.error(request, _("Cannot send email. The administrators have been notified."))

            messages.success(request, _("Account created. Please check your emails for the activation procedure."))
            return HttpResponseRedirect(redirect_url_name)
        else:
            for err_field, err_list in form.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        form = RegistrationForm(required_highschool=(profile == 'lyc'))

    highschools = (HighSchool.agreed
        .values('id', 'city', 'label', 'uses_student_federation')
        .order_by('city', 'label')
    ).filter(allow_individual_immersions=True)

    context = {
        'form': form,
        'profile': profile,
        'highschools_values': json.dumps({h['id']: h for h in highschools}),
        'highschools': HighSchool.agreed.all().order_by('city', 'label').filter(allow_individual_immersions=True)
    }

    return render(request, 'immersion/registration.html', context)


class RecoveryView(TemplateView):
    template_name: str = "immersion/recovery.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs).update({
            "email": self.request.POST.get('email', '').strip().lower()
        })

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()

        try:
            user = ImmersionUser.objects.get(email__iexact=email)

            use_external_auth = any([
                user.establishment and user.establishment.data_source_plugin,
                user.is_student()
            ])

            if use_external_auth:
                messages.warning(request, _("Please use your establishment credentials."))
            elif (user.is_high_school_manager() or user.is_speaker()) and user.uses_federation():
                messages.warning(request, _("Please use the Agent Federation to authenticate"))
            elif user.is_high_school_student() and user.uses_federation():
                messages.warning(request, _("Please use EduConnect to authenticate"))
            else:
                user.set_recovery_string()
                msg = user.send_message(request, 'CPT_MIN_ID_OUBLIE')

                if not msg:
                    messages.success(request, _("An email has been sent with the procedure to set a new password."))
                else:
                    messages.error(request, _("Cannot send email. The administrators have been notified."))
                    logger.error(f"Error while sending email : {msg}")

        except ImmersionUser.DoesNotExist:
            # Don't send error message as it can be used to detect valid url for accounts
            # messages.error(request, _("No account found with this email address"))
            messages.success(request, _("An email has been sent with the procedure to set a new password."))
        except ImmersionUser.MultipleObjectsReturned:
            messages.error(request, _("Error : please contact the establishment referent"))

        context: Dict[str, Any] = self.get_context_data(**kwargs)
        return self.render_to_response(context)


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


# todo: refactor this into class :)
@login_required
@groups_required("LYC", "REF-LYC", "VIS", "INTER", "REF-ETAB", "REF-STR", "SRV-JUR")
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


class ActivateView(View):
    redirect_url: str = "/"

    def get(self, request, *args, **kwargs):
        hash = kwargs.get("hash", None)
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

        return HttpResponseRedirect(self.redirect_url)


class ResendActivationView(TemplateView):
    template_name: str = "immersion/resend_activation.html"

    def get_context_data(self, **kwargs):
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context.update({
            "context": self.request.POST.get('email', '').strip().lower()
        })
        return context

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()
        redirect_url: str = "/shib"

        try:
            user = ImmersionUser.objects.get(email__iexact=email)
        except ImmersionUser.DoesNotExist:
            # Don't show error here as it could be used to get valid email address
            # messages.error(request, _("No account found with this email address"))
            messages.success(request, _("The activation message has been resent."))
        else:
            if user.is_valid():
                messages.error(request, _("This account has already been activated, please login."))
                return HttpResponseRedirect(redirect_url)
            else:
                msg = user.send_message(request, 'CPT_MIN_CREATE')

                if msg:
                    messages.error(request, _("Cannot send email. The administrators have been notified."))
                    logger.error(f"Error while sending activation email : {msg}")
                else:
                    messages.success(request, _("The activation message has been resent."))

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


@method_decorator(groups_required('INTER'), name="dispatch")
class LinkAccountsView(TemplateView):
    template_name: str = "immersion/link_accounts.html"

    def get_context_data(self, **kwargs):
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context.update({
            "context": self.request.POST.get('email', '').strip().lower()
        })
        return context


    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()

        try:
            user = ImmersionUser.objects.get(email__iexact=email)
        except ImmersionUser.DoesNotExist:
            messages.error(request, _("No account found with this email address"))
        else:
            if user.is_valid():
                if not user.is_only_speaker():
                    messages.error(request, _("This account is not a speaker-only one, it can't be linked"))
                elif user in request.user.linked_users():
                    messages.success(request, _("These accounts are already linked"))

                else:
                    try:
                        pending = PendingUserGroup.objects.get(
                            Q(immersionuser1=request.user, immersionuser2=user)
                            |Q(immersionuser2=request.user, immersionuser1=user)
                        )
                    except PendingUserGroup.DoesNotExist:
                        pending = PendingUserGroup.objects.create(
                            immersionuser1 = request.user,
                            immersionuser2 = user,
                            validation_string = uuid.uuid4().hex
                        )

                    link_validation_string = pending.validation_string

                    msg = user.send_message(
                        request,
                        'CPT_FUSION',
                        link_validation_string=link_validation_string,
                        link_source_user=request.user
                    )

                    if msg:
                        messages.error(request, _("Cannot send email. The administrators have been notified."))
                        logger.error(f"Error while sending account link email : {msg}")
                    else:
                        messages.success(request, _("The link message has been sent to this email address"))

            else:
                messages.error(request, _("This account has not been validated (yet)"))

        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


@method_decorator(groups_required('INTER'), name="dispatch")
class LinkView(View):
    redirect_url: str = "/immersion/link_accounts"

    def get(self, request, *args, **kwargs):
        hash = kwargs.get("hash", None)
        if hash:
            try:
                pending_link = PendingUserGroup.objects.get(validation_string=hash)
                u1 = pending_link.immersionuser1
                u2 = pending_link.immersionuser2

                if u1.usergroup.exists():
                    usergroup = u1.usergroup.first()
                    if u2 not in u1.linked_users():
                        usergroup.immersionusers.add(u2)
                else:
                    usergroup = u1.usergroup.create()
                    usergroup.immersionusers.add(u2)

                pending_link.delete()

                messages.success(request, _("Your accounts have been linked"))

            except PendingUserGroup.DoesNotExist:
                messages.error(request, _("Invalid link data"))
            except Exception as e:
                logger.exception("Link error : %s", e)
                messages.error(request, _("Something went wrong"))

        return HttpResponseRedirect(self.redirect_url)


@login_required
@groups_required('REF-ETAB-MAITRE', 'REF-ETAB', 'LYC', 'REF-TEC', 'REF-LYC')
def high_school_student_record(request, student_id=None, record_id=None):
    """
    High school student record
    """
    template_name: str = 'immersion/hs_record.html'
    redirect_url: str = reverse('immersion:hs_record')
    record = None
    student = None
    create_documents = False
    no_quota_form = False
    no_document_form = False

    display_documents_message = False
    quota_form_valid = False
    document_form_valid = False

    validation_needed = False
    completion_needed = False

    quota_forms = []
    document_forms = []

    from_page = request.headers.get('Referer', "")
    user = request.user

    # Quota for non-student user
    quota_allowed_groups = any([
        user.is_establishment_manager(),
        user.is_master_establishment_manager(),
        user.is_operator()
    ])

    # 'back' control if not from the same page (eg. POST)
    if reverse('immersion:hs_record') not in from_page:
        request.session['back'] = request.headers.get('Referer')

    periods = Period.objects.filter(
        immersion_end_date__gte=timezone.localdate()
    )

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
            record = HighSchoolStudentRecord(student=request.user)

    elif record_id:
        try:
            record = HighSchoolStudentRecord.objects.get(pk=record_id)
            student = record.student
        except HighSchoolStudentRecord.DoesNotExist:
            # Record not created yet.
            pass

    if record and record.pk and record.validation != HighSchoolStudentRecord.INIT:
        # Check user access for this record
        if user.is_high_school_manager() and user.highschool != record.highschool:
            if from_page:
                return HttpResponseRedirect(from_page)
            else:
                return HttpResponseRedirect(reverse('home'))

        # Custom quotas objects for already started periods (check registration date)
        # The record must exist
        for period in periods.filter(registration_start_date__lte=timezone.localdate()):
            if not HighSchoolStudentRecordQuota.objects.filter(record=record, period=period).exists():
                HighSchoolStudentRecordQuota.objects.create(
                    record=record, period=period, allowed_immersions=period.allowed_immersions
                )
    else:
        # No record yet, we have to initialize attestations on first record save()
        create_documents = True

    if request.method == 'POST' and request.POST.get('submit'):
        student_id = request.POST.get('student', None)
        if not student and student_id:
            try:
                student = ImmersionUser.objects.get(id=int(student_id))
                record = student.get_high_school_student_record()
            except ImmersionUser.DoesNotExist:
                messages.error(request, _("Invalid student id"))
                return HttpResponseRedirect(request.headers.get('Referer', '/'))

        recordform = HighSchoolStudentRecordForm(request.POST, instance=record, request=request)
        studentform = HighSchoolStudentForm(request.POST, instance=student, request=request)

        if studentform.is_valid():
            if studentform.has_changed():
                student = studentform.save()
                if any([
                    "last_name" in studentform.changed_data,
                    "first_name" in studentform.changed_data,
                ]):
                    validation_needed = True

            if "email" in studentform.changed_data:
                # Update username only if High school doesn't use student federation
                if not student.uses_federation():
                    student.username = student.email

                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')

                    if msg:
                        messages.error(request, _("Cannot send email. The administrators have been notified."))
                        logger.error(f"Error while sending email update notification : {msg}")
                    else:
                        if not student.uses_federation():
                            msg = _(
                                """You have updated your email address."""
                                """<br>Warning : the new email is also the new login."""
                                """<br>A new activation email has been sent."""
                            )
                        else:
                            msg = _(
                                """You have updated your email address."""
                                """<br>A new activation email has been sent."""
                            )

                        messages.warning(request, msg)

                except Exception as e:
                    logger.exception("Cannot send 'change mail' message : %s", e)
        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            if recordform.has_changed():
                # for student federation users, validation is not needed unless some attestations have to be uploaded
                record = recordform.save()
                record.save()
                messages.success(request, _("Record successfully saved."))

                if (not user.uses_federation()
                    and record.validation not in [HighSchoolStudentRecord.TO_COMPLETE, HighSchoolStudentRecord.INIT]
                ):
                    validation_needed = True
                    messages.info(
                        request,
                        _("You have updated your record, it needs to be re-examined for validation.")
                    )

                # These particular field changes will trigger attestations updates
                if 'highschool' in recordform.changed_data or 'birth_date' in recordform.changed_data:
                    create_documents = True

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

            for period in periods.filter(registration_start_date__lte=timezone.localdate()):
                # For newly created records
                if not HighSchoolStudentRecordQuota.objects.filter(record=record, period=period).exists():
                    HighSchoolStudentRecordQuota.objects.create(
                        record=record, period=period, allowed_immersions=period.allowed_immersions
                    )

            # Only for allowed groups (establishment managers and operators)
            if quota_allowed_groups:
                quota_form_valid = True

                for quota in HighSchoolStudentRecordQuota.objects.filter(record=record):
                    quota_form = HighSchoolStudentRecordQuotaForm(
                        request.POST,
                        instance=quota,
                        request=request,
                        prefix=f"quota_{quota.period.id}"
                    )

                    if quota_form.is_valid():
                        quota_form.save()
                    else:
                        quota_form_valid = False

                    quota_forms.append(quota_form)

                if not quota_form_valid:
                    messages.error(request, _("You have errors in Immersion periods section"))
            else:
                no_quota_form = True

            # Documents forms
            if create_documents:
                no_document_form = True
                today = timezone.localdate()
                student_age = today.year - record.birth_date.year\
                              - ((today.month, today.day) < (record.birth_date.month, record.birth_date.day))

                attestation_filters = {
                    'profiles__code': "LYC_W_CONV" if record.highschool.with_convention else "LYC_WO_CONV"
                }

                if student_age >= 18:
                    attestation_filters['for_minors'] = False

                current_documents = HighSchoolStudentRecordDocument.objects.filter(record=record)
                attestations = AttestationDocument.activated.filter(**attestation_filters)

                # Clean documents if school has changed, including archives
                for hsrd in current_documents:
                    if hsrd.attestation not in attestations:
                        hsrd.delete()

                # Attestations need to be linked to the record
                if attestations.exists():
                    creations = 0
                    has_mandatory_attestations = False

                    for attestation in attestations:
                        obj, created = HighSchoolStudentRecordDocument.objects.update_or_create(
                            record=record,
                            attestation=attestation,
                            archive=False,
                            defaults={
                                'for_minors': attestation.for_minors,
                                'mandatory': attestation.mandatory,
                                'requires_validity_date': attestation.requires_validity_date,
                                'archive': False
                            }
                        )

                        has_mandatory_attestations = has_mandatory_attestations or attestation.mandatory

                        creations += 1 if created else 0

                    if creations and has_mandatory_attestations:
                        display_documents_message = True
                        completion_needed = True
                    elif creations:
                        validation_needed = True
                        # Only optional documents to send
                        messages.warning(
                            request, _("Please check the optional documents to send below.")
                        )
            else:
                documents = HighSchoolStudentRecordDocument.objects\
                    .filter(record=record, archive=False)\
                    .order_by("attestation__order")

                document_form_valid = True

                if documents:
                    for document in documents:
                        document_form = HighSchoolStudentRecordDocumentForm(
                            request.POST,
                            request.FILES,
                            instance=document,
                            request=request,
                            prefix=f"document_{document.attestation.id}"
                        )

                        if document_form.is_valid():
                            document = document_form.save()

                            if document_form.has_changed() and 'document' in document_form.changed_data:
                                document.deposit_date = timezone.now()
                                document.validity_date = None
                                document.save()
                                validation_needed = True
                        else:
                            document_form_valid = False
                            if document.attestation.mandatory:
                                completion_needed = True

                        document_forms.append(document_form)

                    if not document_form_valid:
                        messages.error(request, _("You have errors in Attestations section"))

            # Evaluate new record status
            if completion_needed:
                record.set_status("TO_COMPLETE")
            elif validation_needed:
                match record.validation:
                    case HighSchoolStudentRecord.VALIDATED:
                        record.set_status("TO_REVALIDATE")
                    case HighSchoolStudentRecord.TO_REVALIDATE:
                        pass
                    case _:
                        record.set_status("TO_VALIDATE")
            elif record.validation in [HighSchoolStudentRecord.TO_COMPLETE, HighSchoolStudentRecord.INIT]:
                if not user.uses_federation():
                    record.set_status("TO_VALIDATE")
                else:
                    record.set_status("VALIDATED")

            record.save()
        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        valid_forms = all([
            recordform.is_valid(),
            studentform.is_valid(),
            no_quota_form or quota_form_valid,
            no_document_form or document_form_valid
        ])

        if valid_forms:
            if request.user.is_high_school_student():
                if display_documents_message:
                    messages.warning(
                        request, _("Please fill all the required attestation documents below.")
                    )
                elif record.validation in [record.STATUSES["TO_VALIDATE"], record.STATUSES["TO_REVALIDATE"]]:
                    if record.highschool.with_convention:
                        messages.success(
                            request, _("Your record is awaiting validation from your high-school referent.")
                        )
                    else:
                        messages.success(
                            request, _("Your record is awaiting validation by the establishment referent.")
                        )

            return HttpResponseRedirect(reverse('immersion:modify_hs_record', kwargs={'record_id': record.id}))

    else:
        # Forms init
        valid_users = any([
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ])

        if valid_users and record.pk:
            for quota in HighSchoolStudentRecordQuota.objects\
                    .filter(record=record)\
                    .order_by("period__immersion_start_date"):
                quota_form = HighSchoolStudentRecordQuotaForm(
                    request=request,
                    instance=quota,
                    prefix=f"quota_{quota.period.id}"
                )
                quota_forms.append(quota_form)

        if record.pk:
            for document in HighSchoolStudentRecordDocument.objects\
                    .filter(record=record, archive=False)\
                    .order_by("attestation__order"):
                document_form = HighSchoolStudentRecordDocumentForm(
                    request=request,
                    instance=document,
                    prefix=f"document_{document.attestation.id}"
                )
                document_forms.append(document_form)
        else:
            record.save()
            record.refresh_from_db()

        recordform = HighSchoolStudentRecordForm(request=request, instance=record)
        studentform = HighSchoolStudentForm(request=request, instance=student)


    if request.user.is_high_school_student():
        messages.info(request, _("Your record status : %s") % record.get_validation_display())
    else:
        messages.info(request, _("Current record status : %s") % record.get_validation_display())

    # Stats for user deletion
    today = datetime.today().date()
    now = datetime.today().time()

    past_immersions = student.immersions.filter(
        Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now),
        cancellation_type__isnull=True
    ).count()

    future_immersions = student.immersions.filter(
        Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now),
        cancellation_type__isnull=True
    ).count()

    # Count immersion registrations for each period
    immersions_count = {}
    for period in periods:
        immersions_count[period.pk] = student.immersions.filter(
                slot__date__gte=period.immersion_start_date,
                slot__date__lte=period.immersion_end_date,
                slot__event__isnull=True,
                cancellation_type__isnull=True
        ).count()

    # Periods to display
    period_filter = { 'registration_start_date__gt': today } if record.id else {'immersion_end_date__gte': today}

    # Document archives
    archives = defaultdict(list)
    if record.pk:
        for archive in HighSchoolStudentRecordDocument.objects \
                    .filter(Q(validity_date__gte=today)|Q(validity_date__isnull=True), record=record, archive=True) \
                    .order_by("-validity_date"):
            archives[archive.attestation.id].append(archive)

    context = {
        'student_form': studentform,
        'record_form': recordform,
        'quota_forms': quota_forms,
        'document_forms': document_forms,
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
        ),
        'bachelor_types': json.dumps(
            {bt.id: {
                'is_general': bt.general,
                'is_technological': bt.technological,
                'is_professional': bt.professional,
            } for bt in BachelorType.objects.all()}
        ),
        'immersions_count': immersions_count,
        'request_student_consent': GeneralSettings.get_setting('REQUEST_FOR_STUDENT_AGREEMENT'),
        'future_periods': Period.objects.filter(**period_filter).order_by('immersion_start_date'),
        'archives': archives
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
    no_record = False
    quota_forms = []
    periods = Period.objects.filter(immersion_end_date__gte=timezone.localdate())

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
        institution = None

        no_record = record is None

        try:
            shib_attrs = request.session.get("shib", {})
            # UAI code sometimes comes with other information, like {SIRET}
            # Make sure we only consider the {UAI} part and split the string
            uai_code = shib_attrs.get("uai_code").split(";")[0]
        except Exception:
            logger.error("Cannot retrieve uai code from shibboleth data")

        if uai_code and uai_code.startswith('{UAI}'):
            uai_code = uai_code.replace('{UAI}', '')
            try:
                institution = HigherEducationInstitution.objects.get(uai_code__iexact=uai_code)
            except HigherEducationInstitution.DoesNotExist:
                # Just warn the admins with a nice Sentry error :)
                logger.error("UAI codes update required : unknown uai_code : %s", uai_code)
        elif student.establishment and student.establishment.uai_reference:
            # Fallback if student establishment is known
            institution = student.establishment.uai_reference
            uai_code = institution.uai_code

        if not record:
            record = StudentRecord(student=request.user, uai_code=uai_code, institution=institution)
        elif uai_code and record.uai_code != uai_code:
            record.uai_code = uai_code
            record.institution = institution
            record.save()
    elif record_id:
        try:
            record = StudentRecord.objects.get(pk=record_id)
            student = record.student
        except StudentRecord.DoesNotExist:
            pass

    # Custom quotas objects for already started periods (check registration date)
    # The record must exist
    if record.pk:
        for period in periods.filter(registration_start_date__lte=timezone.localdate()):
            if not StudentRecordQuota.objects.filter(record=record, period=period).exists():
                StudentRecordQuota.objects.create(
                    record=record,
                    period=period,
                    allowed_immersions=period.allowed_immersions
                )

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

                    if msg:
                        messages.error(request, _("Cannot send email. The administrators have been notified."))
                        logger.error(f"Error while sending email update notification : {msg}")
                    else:
                        messages.warning(
                            request,
                            _("""You have updated your email address.""" """<br>A new activation email has been sent.""")
                        )
                except Exception as e:
                    logger.exception("Error while sending email update notification : %s", e)
                    messages.error(request, _("Cannot send email. The administrators have been notified."))

        else:
            for err_field, err_list in studentform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))

        if recordform.is_valid():
            record = recordform.save()
            messages.success(request, _("Record successfully saved."))

            # Quota creation for newly created records
            for period in periods.filter(registration_start_date__lte=timezone.localdate()):
                if not StudentRecordQuota.objects.filter(record=record, period=period).exists():
                    StudentRecordQuota.objects.create(
                        record=record,
                        period=period,
                        allowed_immersions=period.allowed_immersions
                    )

            # Quota for non-student user
            if not request.user.is_student():
                quota_form_valid = True

                for quota in StudentRecordQuota.objects.filter(record=record):
                    quota_form = StudentRecordQuotaForm(
                        request.POST,
                        instance=quota,
                        request=request,
                        prefix=f"quota_{quota.period.id}"
                    )

                    if quota_form.is_valid():
                        quota_form.save()
                    else:
                        quota_form_valid = False

                    quota_forms.append(quota_form)

                if not quota_form_valid:
                    messages.error(request, _("You have errors in Immersion periods section"))
            else:
                no_quota_form = True
        else:
            for err_field, err_list in recordform.errors.get_json_data().items():
                for error in err_list:
                    if error.get("message"):
                        messages.error(request, error.get("message"))
    else:
        if record.pk:
            recordform = StudentRecordForm(request=request, instance=record)

            for quota in StudentRecordQuota.objects.filter(record=record):
                quota_form = StudentRecordQuotaForm(
                    request=request,
                    instance=quota,
                    prefix=f"quota_{quota.period.id}"
                )
                quota_forms.append(quota_form)
        else:
            record.save()
            record.refresh_from_db()
            recordform = StudentRecordForm(
                request=request,
                instance=record
            )

        studentform = StudentForm(request=request, instance=student)

    if reverse('immersion:student_record') not in request.headers.get('Referer', ""):
        request.session['back'] = request.headers.get('Referer')

    # Stats for user deletion
    today = datetime.today().date()
    now = datetime.today().time()

    past_immersions = student.immersions.filter(
        Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now),
        cancellation_type__isnull=True
    ).count()

    future_immersions = student.immersions.filter(
        Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now),
        cancellation_type__isnull=True
    ).count()

    # Count immersion registrations for each period
    immersions_count = {}
    for period in periods:
        immersions_count[period.pk] = student.immersions.filter(
            slot__date__gte=period.immersion_start_date,
            slot__date__lte=period.immersion_end_date,
            slot__event__isnull=True,
            cancellation_type__isnull=True
        ).count()

    # Periods to display
    period_filter = {'registration_start_date__gt': today} if record.id \
        else {'immersion_end_date__gte': today}

    context = {
        'no_record': no_record,
        'student_form': studentform,
        'record_form': recordform,
        "quota_forms": quota_forms,
        'record': record,
        'student': student,
        'back_url': request.session.get('back'),
        'past_immersions': past_immersions,
        'future_immersions': future_immersions,
        'immersions_count': immersions_count,
        'future_periods': Period.objects.filter(**period_filter).order_by('immersion_start_date')
    }

    return render(request, template_name, context)


@login_required
@groups_required('LYC', 'ETU', 'VIS')
def registrations(request):
    """
    Students : display to come, past and cancelled immersions/events
    Also display the number of active alerts
    """
    cancellation_reasons = CancelType.objects.filter(
        active=True,
        managers=False,
        students=True,
        system=False
    ).order_by('label')
    alerts = UserCourseAlert.objects.filter(email=request.user.email)
    not_sent_alerts_cnt = alerts.filter(email_sent=False).count()
    sent_alerts_cnt = alerts.filter(email_sent=True).count()

    context = {
        'cancellation_reasons': cancellation_reasons,
        'alerts_cnt': alerts.count(),
        'not_sent_alerts_cnt': not_sent_alerts_cnt,
        'sent_alerts_cnt': sent_alerts_cnt,
    }

    return render(request, 'immersion/my_registrations.html', context)


@login_required
@groups_required('LYC', 'ETU', 'REF-LYC', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC', 'VIS')
def immersion_attestation_download(request, immersion_id):
    """
    Attestation download
    """
    try:
        immersion = Immersion.objects.prefetch_related(
            'slot__course__training', 'slot__course_type', 'slot__campus', 'slot__building', 'slot__speakers',
        ).get(Q(attendance_status=1) | Q(slot__place=Slot.REMOTE), pk=immersion_id)

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

        slot_entity = immersion.slot.get_establishment() \
            if immersion.slot.get_establishment() else immersion.slot.get_highschool()

        certificate_logo = slot_entity if slot_entity and slot_entity.logo \
            else CertificateLogo.objects.get(pk=1)
        certificate_sig = slot_entity if slot_entity and slot_entity.signature \
            else CertificateSignature.objects.get(pk=1)

        context = {
            'city': slot_entity.city.capitalize() if slot_entity else '',
            'certificate_header': slot_entity.certificate_header if slot_entity and slot_entity.certificate_header else '',
            'certificate_body': certificate_body,
            'certificate_footer': slot_entity.certificate_footer if slot_entity and slot_entity.certificate_footer else '',
            'certificate_logo': certificate_logo,
            'certificate_sig': certificate_sig,
        }

        filename = f'immersion_{date_format(immersion.slot.date,"dmY")}_{student.last_name}_{student.first_name}.pdf'
        response = generate_pdf(request, 'export/pdf/attendance_certificate.html', context, filename=filename)

        return response
    # TODO: Manage Mailtemplate not found (?) anyway returns 404
    except Exception as e:
        logger.error('Certificate download error', exc_info=e)
        raise Http404() from e


@login_required
@groups_required('REF-ETAB', 'REF-ETAB-MAITRE', 'REF-STR', 'INTER', 'REF-TEC', 'REF-LYC', 'CONS-STR')
def immersion_attendance_students_list_download(request, slot_id):
    """
    Attendance students list pdf download
    """
    try:

        immersions = ""
        slot = Slot.objects.get(pk=slot_id)

        if slot:
            immersions = Immersion.objects\
                .prefetch_related('student')\
                .filter(slot=slot, cancellation_type__isnull=True)\
                .order_by("student__last_name", "student__first_name")

            slot_entity = slot.get_establishment() \
                if slot.get_establishment() else slot.get_highschool()

            logo = slot_entity.logo if slot_entity and slot_entity.logo \
                else CertificateLogo.objects.get(pk=1).logo

            context = {
                'students' : [i.student for i in immersions],
                'logo' : logo if logo else '',
                'slot_desc' : slot,
            }

            filename = f'{date_format(slot.date,"dmY")}.pdf'
            response = generate_pdf(request, 'export/pdf/attendance_students_list.html', context, filename=filename)

            return response
    # TODO: Manage Mailtemplate not found (?) anyway returns 404
    except Exception as e:
        logger.error('Certificate download error', exc_info=e)
        raise Http404() from e


@method_decorator(groups_required('VIS', 'REF-ETAB', 'REF-ETAB-MAITRE', 'REF-TEC'), name="dispatch")
class VisitorRecordView(FormView):
    template_name = "immersion/visitor_record.html"
    form_class = VisitorRecordForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record = None
        self.no_quota_form = False
        self.no_document_form = False

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["request"] = self.request
        record_id: Optional[int] = self.kwargs.get("record_id")

        if self.request.user.is_visitor():
            record = self.request.user.get_visitor_record()
            if record:
                self.record = record
                form_kwargs["instance"] = record
        elif record_id:
            try:
                record: VisitorRecord = VisitorRecord.objects.get(id=record_id)
                self.record = record
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
        has_change_permission = any([
            self.request.user.is_establishment_manager(),
            self.request.user.is_master_establishment_manager(),
            self.request.user.is_operator()
        ])
        quota_forms = []
        document_forms = []
        periods = Period.objects.filter(
            registration_start_date__lte=timezone.localdate(),
            immersion_end_date__gte=timezone.localdate()
        )

        if reverse('immersion:visitor_record') not in self.request.headers.get('Referer', ""):
            self.request.session['back'] = self.request.headers.get('Referer')

        if self.request.user.is_visitor():
            visitor = self.request.user
            record = visitor.get_visitor_record()
            if not record:
                record = VisitorRecord(visitor=visitor)

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

        # Custom quotas objects for already started periods (check registration date)
        # The record must exist
        if record and record.pk:
            for period in periods:
                if not VisitorRecordQuota.objects.filter(record=record, period=period).exists():
                    VisitorRecordQuota.objects.create(
                        record=record, period=period, allowed_immersions=period.allowed_immersions
                    )

        # Stats for user deletion
        today = timezone.localdate()
        now = timezone.now()
        all_periods = Period.objects.all()

        past_immersions = visitor.immersions.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
        ).count()
        future_immersions = visitor.immersions.filter(
            Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
        ).count()

        # Count immersion registrations for each period
        immersions_count = {}
        for period in all_periods:
            immersions_count[period.pk] = visitor.immersions.filter(
                slot__date__gte=period.immersion_start_date,
                slot__date__lte=period.immersion_end_date,
                slot__event__isnull=True,
                cancellation_type__isnull=True
            ).count()

        if record.pk:
            context.update({"record": record})  # for modal nuke purpose

            # Extra forms for quotas and documents
            for quota in VisitorRecordQuota.objects\
                    .filter(record=record)\
                    .order_by("period__immersion_start_date"):
                quota_form = VisitorRecordQuotaForm(
                    request=self.request,
                    instance=quota,
                    prefix=f"quota_{quota.period.id}"
                )
                quota_forms.append(quota_form)

            for document in VisitorRecordDocument.objects\
                    .filter(record=record, archive=False)\
                    .order_by("attestation__order"):
                document_form = VisitorRecordDocumentForm(
                    request=self.request,
                    instance=document,
                    prefix=f"document_{document.attestation.id}"
                )
                document_forms.append(document_form)

        # Record status
        if self.request.user.is_visitor():
            msg = _("Your record status : %s") % record.get_validation_display()
        else:
            msg = _("Current record status : %s") % record.get_validation_display()

        messages.info(self.request, msg)

        # Periods to display
        period_filter = {'registration_start_date__gt': today} if record and record.pk \
            else {'immersion_end_date__gte': today}

        # Document archives
        archives = defaultdict(list)
        if record.pk:
            for archive in VisitorRecordDocument.objects \
                    .filter(Q(validity_date__gte=today) | Q(validity_date__isnull=True), record=record, archive=True) \
                    .order_by("-validity_date"):
                archives[archive.attestation.id].append(archive)

        context.update({
            "past_immersions": past_immersions,
            "future_immersions": future_immersions,
            "visitor": visitor,
            "student": visitor,  # visitor = student for modal nuke purpose
            "user_form": user_form,
            "quota_forms": quota_forms,
            "document_forms": document_forms,
            "back_url": self.request.session.get("back"),
            "can_change": has_change_permission,  # can change number of allowed immersions
            "immersions_count": immersions_count,
            'future_periods': Period.objects.filter(**period_filter).order_by('immersion_start_date'),
            'archives': archives
        })
        return context

    def email_changed(self, user: ImmersionUser):
        user.username = user.email
        user.set_validation_string()

        try:
            msg = user.send_message(self.request, "CPT_MIN_CHANGE_MAIL")

            if msg:
                messages.error(self.request, _("Cannot send email. The administrators have been notified."))
                logger.error(f"Error while sending email update notification : {msg}")
            else:
                messages.warning(
                    self.request,
                    _(
                        """You have updated your email address."""
                        """<br>Warning : the new email is also the new login."""
                        """<br>A new activation email has been sent."""
                    ),
                )
        except Exception as exc:
            messages.error(self.request, _("Cannot send email. The administrators have been notified."))
            logger.exception("Error while sending email update notification : %s", exc)

    def post(self, request, *args, **kwargs):
        # multi validation for multiple form
        form = self.get_form()
        form_user: VisitorForm
        record_id: Optional[int] = self.kwargs.get("record_id")
        current_email: Optional[str] = None
        user: Optional[ImmersionUser] = None
        create_documents = False
        completion_needed = False
        validation_needed = False
        display_documents_message = False
        quota_forms = []
        document_forms = []
        periods = Period.objects.filter(immersion_end_date__gte=timezone.localdate())

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

        if not self.record:
            create_documents = True

        if form.is_valid() and form_user.is_valid():
            record = form.save()
            saved_user = form_user.save()

            # Default quotas for newly created records
            for period in periods.filter(registration_start_date__lte=timezone.localdate()):
                if not VisitorRecordQuota.objects.filter(record=record, period=period).exists():
                    VisitorRecordQuota.objects.create(
                        record=record, period=period, allowed_immersions=period.allowed_immersions
                    )

            # any change : validation need
            if form.has_changed():
                validation_needed = True
                record.save()
                messages.info(
                    request,
                    _("You have updated your record, it needs to be re-examined for validation.")
                )

                # Documents update needed
                create_documents = True

            # Quota for non-visitor user
            if not request.user.is_visitor():
                quota_form_valid = True

                for quota in VisitorRecordQuota.objects.filter(record=record):
                    quota_form = VisitorRecordQuotaForm(
                        request.POST,
                        instance=quota,
                        request=request,
                        prefix=f"quota_{quota.period.id}"
                    )

                    if quota_form.is_valid():
                        quota_form.save()
                    else:
                        quota_form_valid = False

                    quota_forms.append(quota_form)

                if not quota_form_valid:
                    messages.error(request, _("You have errors in Immersion periods section"))
            else:
                self.no_quota_form = True

            # Documents forms
            if create_documents:
                self.no_document_form = True
                today = timezone.localdate()
                visitor_age = today.year - record.birth_date.year \
                              - ((today.month, today.day) < (record.birth_date.month, record.birth_date.day))

                attestation_filters = {
                    'profiles__code': "VIS"
                }

                if visitor_age >= 18:
                    attestation_filters['for_minors'] = False

                current_documents = VisitorRecordDocument.objects.filter(record=record)
                attestations = AttestationDocument.activated.filter(**attestation_filters)

                # Clean documents if school has changed, including archives
                for vrd in current_documents:
                    if vrd.attestation not in attestations:
                        vrd.delete()

                if attestations.exists():
                    creations = 0
                    has_mandatory_attestations = False

                    for attestation in attestations:
                        obj, created = VisitorRecordDocument.objects.update_or_create(
                            record=record,
                            attestation=attestation,
                            archive=False,
                            defaults={
                                'for_minors': attestation.for_minors,
                                'mandatory': attestation.mandatory,
                                'requires_validity_date': attestation.requires_validity_date,
                                'archive': False
                            }
                        )

                        has_mandatory_attestations = has_mandatory_attestations or attestation.mandatory

                        creations += 1 if created else 0

                    if creations and has_mandatory_attestations:
                        display_documents_message = True
                        # Documents have to be filled -> status = 0
                        completion_needed = True
                    elif creations:
                        validation_needed = True
                        # Optional documents to send
                        messages.warning(
                            request, _("Please check the optional documents to send below.")
                        )
            else:
                documents = VisitorRecordDocument.objects \
                    .filter(record=record, archive=False) \
                    .order_by("attestation__order")

                document_form_valid = True

                if documents:
                    for document in documents:
                        document_form = VisitorRecordDocumentForm(
                            request.POST,
                            request.FILES,
                            instance=document,
                            request=request,
                            prefix=f"document_{document.attestation.id}"
                        )

                        if document_form.is_valid():
                            document = document_form.save()
                            if document_form.has_changed() and 'document' in document_form.changed_data:
                                document.deposit_date = timezone.now()
                                document.validity_date = None
                                document.save()
                                validation_needed = True
                        else:
                            document_form_valid = False
                            if document.attestation.mandatory:
                                completion_needed = True

                        document_forms.append(document_form)

                    if not document_form_valid:
                        messages.error(request, _("You have errors in Attestations section"))

            # Evaluate new record status
            if completion_needed:
                record.set_status("TO_COMPLETE")
            elif validation_needed:
                match record.validation:
                    case VisitorRecord.VALIDATED:
                        record.set_status("TO_REVALIDATE")
                    case VisitorRecord.TO_REVALIDATE:
                        pass
                    case _:
                        record.set_status("TO_VALIDATE")
            elif record.validation == VisitorRecord.TO_COMPLETE:
                record.set_status("TO_VALIDATE")

            record.save()

            if current_email != saved_user.email:
                self.email_changed(saved_user)

            valid_forms = all([
                form.is_valid(),
                form_user.is_valid(),
                self.no_quota_form or quota_form_valid,
                self.no_document_form or document_form_valid
            ])

            if valid_forms:
                if request.user.is_visitor() and display_documents_message:
                    messages.warning(
                        request, _("Please fill all the required attestation documents below.")
                    )

                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        else:
            for form_ in (form, form_user):
                for err_field, err_list in form_.errors.get_json_data().items():
                    for error in err_list:
                        if error.get("message"):
                            messages.error(self.request, error.get("message"))

            return self.form_invalid(form)

    def get_success_url(self) -> str:
        if self.request.user.is_visitor():
            return reverse("immersion:visitor_record")
        else:
            return reverse("immersion:visitor_record_by_id", kwargs=self.kwargs)
