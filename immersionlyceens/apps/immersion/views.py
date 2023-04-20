import json
import logging
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, Optional

from django import forms
from django.conf import settings
from django.contrib import messages
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

from immersionlyceens.apps.core.models import (
    CancelType, CertificateLogo, CertificateSignature, GeneralSettings,
    HigherEducationInstitution, HighSchoolLevel, Immersion, ImmersionUser,
    MailTemplate, PendingUserGroup, Period, PostBachelorLevel, Slot,
    StudentLevel, UniversityYear, UserCourseAlert,
)
from immersionlyceens.apps.immersion.utils import generate_pdf
from immersionlyceens.decorators import groups_required
from immersionlyceens.libs.mails.variables_parser import parser
from immersionlyceens.libs.utils import check_active_year, get_general_setting

from shibboleth.decorators import login_optional
from shibboleth.middleware import ShibbolethRemoteUserMiddleware

from immersionlyceens.apps.core.models import GeneralSettings, AttestationDocument

from .forms import (
    HighSchoolStudentForm, HighSchoolStudentRecordForm, HighSchoolStudentRecordDocumentForm,
    HighSchoolStudentRecordQuotaForm, LoginForm, NewPassForm, RegistrationForm, StudentForm,
    StudentRecordForm, StudentRecordQuotaForm, VisitorForm, VisitorRecordForm,
    VisitorRecordDocumentForm, VisitorRecordQuotaForm
)

from .models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument,
    HighSchoolStudentRecordQuota, StudentRecord, StudentRecordQuota,
    VisitorRecord, VisitorRecordDocument, VisitorRecordQuota
)

logger = logging.getLogger(__name__)


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
            return "/immersion" if self.user.get_high_school_student_record() else "/immersion/hs_record"
        elif self.user.is_visitor():
            return "/immersion" if self.user.get_visitor_record() else "/immersion/visitor_record"
        elif any(go_home):
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

    try:
        affiliations = shib_attrs.pop("affiliation", "").split(";")
    except Exception as e:
        logger.warning(e)
        affiliations = []

    is_student = any(list(filter(lambda a: a.startswith("student@"), affiliations)))
    is_employee = not is_student

    # Account creation confirmed
    if is_student and request.POST.get('submit'):
        if not get_general_setting('ACTIVATE_STUDENTS'):
            messages.error(request, _("Students deactivated"))
            return HttpResponseRedirect("/")

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
            msg = new_user.send_message(request, 'CPT_MIN_CREATE')
        except Exception as e:
            logger.exception("Cannot send activation message : %s", e)

        messages.success(request, _("Account created. Please look at your emails for the activation procedure."))
        return HttpResponseRedirect("/")


    if request.user.is_anonymous:
        err = None

        if is_employee:
            err = _("Your account must be first created by a master establishment manager or an operator.")
        elif not is_student:
            err = _("The attributes sent by Shibboleth show you may not be a student.")

        if err:
            err += _("<br>If you think this is a mistake, please use the 'contact' link at the " +
                     "<br>bottom of this page, specifying your institution.")
            messages.error(request, err)
            return HttpResponseRedirect("/")

        context = shib_attrs
        return render(request, "immersion/confirm_creation.html", context)
    else:
        # Update user attributes
        try:
            user = ImmersionUser.objects.get(username=shib_attrs["username"])
            user.last_name = shib_attrs["last_name"]
            user.first_name = shib_attrs["first_name"]
            user.email = shib_attrs["email"]
            user.username = shib_attrs["username"]
            user.save()
        except (ImmersionUser.DoesNotExist, KeyError):
            err = _("Unable to find a matching user in database")
            return HttpResponseRedirect("/")

        # Activated account ?
        if not request.user.is_valid():
            messages.error(request, _("Your account hasn't been enabled yet."))
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
                    return HttpResponseRedirect("/immersion")
                else:
                    return HttpResponseRedirect("/immersion/student_record")

    return HttpResponseRedirect("/")


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
            except Exception as e:
                logger.exception("Cannot send activation message : %s", e)

            messages.success(request, _("Account created. Please look at your emails for the activation procedure."))
            return HttpResponseRedirect(redirect_url_name)
        # Not used anymore using form.errors displaying instead
        # else:
        #     for err_field, err_list in form.errors.get_json_data().items():
        #         for error in err_list:
        #             if error.get("message"):
        #                 messages.error(request, error.get("message"))
    else:
        form = RegistrationForm()

    context = {'form': form, 'profile': profile}

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
            else:
                user.set_recovery_string()
                msg = user.send_message(request, 'CPT_MIN_ID_OUBLIE')
                messages.success(request, _("An email has been sent with the procedure to set a new password."))

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
    redirect_url: str = "/immersion/login"

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
                if not msg:
                    messages.success(request, _("The activation message has been resent."))
                else:
                    messages.error(request, _("The activation message has not been sent") + " : " + msg)

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

                    if not msg:
                        messages.success(request, _("The link message has been sent to this email address"))
                    else:
                        messages.error(request, _("Message not sent : %s") % msg)
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

    next = False
    quota_form_valid = False
    document_form_valid = False

    quota_forms = []
    document_forms = []

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

    # Custom quotas objects for already started periods (check registration date)
    # The record must exist
    if record and record.pk:
        for period in periods.filter(registration_start_date__lte=timezone.localdate()):
            if not HighSchoolStudentRecordQuota.objects.filter(record=record, period=period).exists():
                HighSchoolStudentRecordQuota.objects.create(
                    record=record, period=period, allowed_immersions=period.allowed_immersions
                )
    else:
        # No record yet
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
                student.username = student.email
                student.set_validation_string()
                try:
                    msg = student.send_message(request, 'CPT_MIN_CHANGE_MAIL')
                    if msg:
                        messages.error(request, _("Cannot send email : %s") % msg)
                    else:
                        messages.warning(
                            request, _(
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
            messages.success(request, _("Record successfully saved."))

            if current_highschool and current_highschool != record.highschool.id:
                # New record validation is needed
                if record.validation > 1:
                    messages.info(
                        request,
                        _("You have changed the high school, your record needs a new validation")
                    )

                # Documents update needed
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

            # Quota for non-student user
            if not request.user.is_high_school_student():
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

            # Documents formset
            if create_documents:
                no_document_form = True
                today = timezone.localdate()
                student_age = today.year - record.birth_date.year\
                              - ((today.month, today.day) < (record.birth_date.month, record.birth_date.day))

                attestation_filters = {
                    'for_minors': student_age < 18,
                    'profiles__code': "LYC_W_CONV" if record.highschool.with_convention else "LYC_WO_CONV"
                }

                current_documents = HighSchoolStudentRecordDocument.objects.filter(record=record)
                attestations = AttestationDocument.activated.filter(**attestation_filters)

                # Clean documents if school has changed
                for hsrd in current_documents:
                    if hsrd.attestation not in attestations:
                        hsrd.delete()

                if attestations.exists():
                    creations = 0
                    for attestation in attestations:
                        obj, created = HighSchoolStudentRecordDocument.objects.update_or_create(
                            record=record, attestation=attestation,
                            defaults={
                                'for_minors': attestation.for_minors,
                                'mandatory': attestation.mandatory,
                                'requires_validity_date': attestation.requires_validity_date,
                            }
                        )

                        creations += 1 if created else 0

                    if creations:
                        next = True
                        # Documents have to be filled -> status = 0
                        record.validation = 0
                    else:
                        record.validation = 1
                else:
                    # No attestation
                    record.validation = 1

                record.save()

            else:
                document_form_valid = True

                for document in HighSchoolStudentRecordDocument.objects.filter(record=record):
                    document_form = HighSchoolStudentRecordDocumentForm(
                        request.POST,
                        request.FILES,
                        instance=document,
                        request=request,
                        prefix=f"document_{document.attestation.id}"
                    )

                    if document_form.is_valid():
                        document_form.save()
                    else:
                        document_form_valid = False

                    document_forms.append(document_form)

                if not document_form_valid:
                    messages.error(request, _("You have errors in Attestations section"))
                else:
                    record.validation = 1
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
                if next:
                    messages.warning(
                        request, _("Record saved. Please fill all the required attestation documents below.")
                    )
                elif record.validation == 1:
                    messages.success(
                        request, _("Thank you. Your record is awaiting validation from your high-school referent.")
                    )

            return HttpResponseRedirect(reverse('immersion:modify_hs_record', kwargs={'record_id': record.id}))
    else:
        # TODO: maybe not useful could be removed
        #request.session['back'] = request.headers.get('Referer')
        recordform = HighSchoolStudentRecordForm(request=request, instance=record)
        studentform = HighSchoolStudentForm(request=request, instance=student)
        for quota in HighSchoolStudentRecordQuota.objects.filter(record=record):
            quota_form = HighSchoolStudentRecordQuotaForm(
                request=request,
                instance=quota,
                prefix=f"quota_{quota.period.id}"
            )
            quota_forms.append(quota_form)

        for document in HighSchoolStudentRecordDocument.objects.filter(record=record):
            document_form = HighSchoolStudentRecordDocumentForm(
                request=request,
                instance=document,
                prefix=f"document_{document.attestation.id}"
            )
            document_forms.append(document_form)

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
                slot__visit__isnull=True,
                cancellation_type__isnull=True
        ).count()

    # Periods to display
    period_filter = { 'registration_start_date__gte': today } if record.id else {'immersion_end_date__gte': today}

    context = {
        'student_form': studentform,
        'record_form': recordform,
        'quota_forms': quota_forms,
        'document_forms': document_forms,
        'student': student,
        'record': record,
        # TODO: maybe not useful could be removed
        #'back_url': request.session.get('back'),
        'past_immersions': past_immersions,
        'future_immersions': future_immersions,
        'high_school_levels': json.dumps(
            {l.id: {
                'is_post_bachelor': l.is_post_bachelor,
                'requires_bachelor_speciality': l.requires_bachelor_speciality
            } for l in HighSchoolLevel.objects.all()}
        ),
        'immersions_count': immersions_count,
        'request_student_consent': GeneralSettings.get_setting('REQUEST_FOR_STUDENT_AGREEMENT'),
        'future_periods': Period.objects.filter(**period_filter).order_by('immersion_start_date')
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
            uai_code = shib_attrs.get("uai_code")
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
                    record=record, period=period, allowed_immersions=period.allowed_immersions
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

            # Quota creation for newly created records
            for period in periods.filter(registration_start_date__lte=timezone.localdate()):
                if not StudentRecordQuota.objects.filter(record=record, period=period).exists():
                    StudentRecordQuota.objects.create(
                        record=record, period=period, allowed_immersions=period.allowed_immersions
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
        request.session['back'] = request.headers.get('Referer')
        recordform = StudentRecordForm(request=request, instance=record)
        studentform = StudentForm(request=request, instance=student)
        for quota in StudentRecordQuota.objects.filter(record=record):
            quota_form = StudentRecordQuotaForm(
                request=request,
                instance=quota,
                prefix=f"quota_{quota.period.id}"
            )
            quota_forms.append(quota_form)


    # Stats for user deletion
    today = datetime.today().date()
    now = datetime.today().time()

    past_immersions = student.immersions.filter(
        Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
    ).count()

    future_immersions = student.immersions.filter(
        Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
    ).count()

    # Count immersion registrations for each period
    immersions_count = {}
    for period in periods:
        immersions_count[period.pk] = student.immersions.filter(
            slot__date__gte=period.immersion_start_date,
            slot__date__lte=period.immersion_end_date,
            slot__event__isnull=True,
            slot__visit__isnull=True,
            cancellation_type__isnull=True
        ).count()

    # Periods to display
    period_filter = {'registration_start_date__gte': today} if record.id \
        else {'immersion_end_date__gte': today}

    context = {
        'no_record': no_record,
        'student_form': studentform,
        'record_form': recordform,
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
    Students : display to come, past and cancelled immersions/events/visits
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
        ).get(Q(attendance_status=1) | Q(slot__face_to_face=False), pk=immersion_id)

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
        logger.error('Certificate download error', e)
        raise Http404()


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
            immersions = Immersion.objects.prefetch_related('student').filter(slot=slot, cancellation_type__isnull=True)
            slot_entity = slot.get_establishment() \
                if slot.get_establishment() else slot.get_highschool()

            logo = slot_entity if slot_entity and slot_entity.logo \
                else CertificateLogo.objects.get(pk=1)

            context = {
                'students' : [ i.student for i in immersions],
                'logo' : logo if logo else '',
                'slot_desc' : slot,
            }

            filename = f'{date_format(slot.date,"dmY")}.pdf'
            response = generate_pdf(request, 'export/pdf/attendance_students_list.html', context, filename=filename)

            return response
    # TODO: Manage Mailtemplate not found (?) anyway returns 404
    except Exception as e:
        logger.error('Certificate download error', e)
        raise Http404()


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
        periods = Period.objects.all()

        past_immersions = visitor.immersions.filter(
            Q(slot__date__lt=today) | Q(slot__date=today, slot__end_time__lt=now), cancellation_type__isnull=True
        ).count()
        future_immersions = visitor.immersions.filter(
            Q(slot__date__gt=today) | Q(slot__date=today, slot__start_time__gt=now), cancellation_type__isnull=True
        ).count()

        # Count immersion registrations for each period
        immersions_count = {}
        for period in periods:
            immersions_count[period.pk] = visitor.immersions.filter(
                slot__date__gte=period.immersion_start_date,
                slot__date__lte=period.immersion_end_date,
                slot__event__isnull=True,
                slot__visit__isnull=True,
                cancellation_type__isnull=True
            ).count()

        if record.pk:
            context.update({"record": record})  # for modal nuke purpose

            # Extra forms for quotas and documents
            for quota in VisitorRecordQuota.objects.filter(record=record):
                quota_form = VisitorRecordQuotaForm(
                    request=self.request,
                    instance=quota,
                    prefix=f"quota_{quota.period.id}"
                )
                quota_forms.append(quota_form)

            for document in VisitorRecordDocument.objects.filter(record=record):
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
        period_filter = {'registration_start_date__gte': today} if record and record.pk \
            else {'immersion_end_date__gte': today}

        context.update({
            "past_immersions": past_immersions,
            "future_immersions": future_immersions,
            "visitor": visitor,
            "student": visitor,  # visitor = student for modal nuke purpose
            "user_form": user_form,
            "quota_forms": quota_forms,
            "document_forms": document_forms,
            "back_url": self.request.session.get("back"),
            "can_change": has_change_permission,  # can change number of allowed positions
            "immersions_count": immersions_count,
            'future_periods': Period.objects.filter(**period_filter).order_by('immersion_start_date')
        })
        return context

    def email_changed(self, user: ImmersionUser):
        user.username = user.email
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
        create_documents = False
        next = False
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

            # Quota for non-student user
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
                    'for_minors': visitor_age < 18,
                    'profiles__code': "VIS"
                }

                attestations = AttestationDocument.activated.filter(**attestation_filters)

                if attestations.exists():
                    next = True
                    for attestation in attestations:
                        VisitorRecordDocument.objects.create(
                            record=record,
                            attestation=attestation,
                            for_minors=attestation.for_minors,
                            mandatory=attestation.mandatory,
                            requires_validity_date=attestation.requires_validity_date,
                        )
                    record.validation = 0
                else:
                    record.validation = 1

                record.save()
            else:
                document_form_valid = True

                for document in VisitorRecordDocument.objects.filter(record=record):
                    document_form = VisitorRecordDocumentForm(
                        request.POST,
                        request.FILES,
                        instance=document,
                        request=request,
                        prefix=f"document_{document.attestation.id}"
                    )

                    if document_form.is_valid():
                        document = document_form.save()
                    else:
                        document_form_valid = False

                    document_forms.append(document_form)

                if not document_form_valid:
                    messages.error(request, _("You have errors in Attestations section"))
                else:
                    record.validation = 1
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
                if request.user.is_visitor() and next:
                    messages.warning(
                        request, _("Record saved. Please fill all the required attestation documents below.")
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
