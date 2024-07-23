"""
Check that a high school user has an email (he may not if his account has just been created by EduConnect)
"""

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from immersionlyceens.apps.core.models import (
    GeneralSettings, HighSchool, ImmersionUser,
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
from immersionlyceens.libs.utils import get_general_setting

class EmailCheck:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        user = request.user

        if user.is_anonymous or not user.is_high_school_student():
            return response

        if user.email != f"{user.username}@domain.tld":
            return response

        elif request.path != reverse("immersion:set_email"):
            return HttpResponseRedirect(reverse('immersion:set_email'))

        return response
