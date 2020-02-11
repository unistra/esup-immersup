import uuid
from datetime import datetime

from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import Session
from django.conf import settings

from immersionlyceens.apps.core.models import ImmersionUser

from .forms import LoginForm, RegistrationForm

def login(request):
    # Clear all client sessions
    Session.objects.all().delete()

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['login']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
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


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            new_user = form.save(commit=False)
            # adjustments here
            new_user.username = form.cleaned_data.get("username")
            new_user.validation_string = uuid.uuid4().hex
            new_user.destruction_date = \
                datetime.today().date() + datetime.timedelta(days=settings.DESTRUCTION_DELAY)
            new_user.save()

            new_user.send_message(request, 'CPT_MIN_CREATE_LYCEEN')

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


def activate(request):
    print(request.GET)

    context = {}

    return render(request, 'immersion/login.html', context)

@login_required
def home(request):
    context = {
    }
    return render(request, 'immersion/home.html', context)

