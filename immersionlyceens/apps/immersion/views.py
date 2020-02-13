import uuid
import logging
from datetime import datetime, timedelta

from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import Session
from django.conf import settings

from immersionlyceens.apps.core.models import ImmersionUser, UniversityYear
from immersionlyceens.libs.utils import check_active_year

from .forms import LoginForm, RegistrationForm


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
                    return HttpResponseRedirect("/immersion")
                    # Else
                    # return HttpResponseRedirect("/immersion/record")
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
            new_user.validation_string = uuid.uuid4().hex
            new_user.destruction_date = \
                datetime.today().date() + timedelta(days=settings.DESTRUCTION_DELAY)
            new_user.save()

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
    pass


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

    context = {}

    return HttpResponseRedirect("/immersion/login")

@login_required
def home(request):
    context = {
    }
    return render(request, 'immersion/home.html', context)

