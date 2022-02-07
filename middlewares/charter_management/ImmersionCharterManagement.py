from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

from immersionlyceens.apps.core.models import GeneralSettings, ImmersionUser
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
from immersionlyceens.libs.utils import get_general_setting

class ImmersionCharterManagement:
    def __init__(self, get_response):
        self.get_response = get_response
        self.charter_sign = get_general_setting('CHARTER_SIGN')

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        user = request.user
        highschool = None

        if user.is_anonymous:
            return response

        try:
            highschool = user.high_school_student_record.highschool
        except HighSchoolStudentRecord.DoesNotExist:
            if user.highschool:
                highschool = user.highschool

        if self.charter_sign:
            signed_charter = any([
                user.is_superuser,
                user.is_operator(),
                user.establishment and (user.establishment.master or user.establishment.signed_charter),
                highschool and highschool.postbac_immersion and highschool.signed_charter
            ])

            # TODO : prevent other profiles to connect if the charter has not been signed

            if not signed_charter:
                exceptions = [
                    reverse('sign_charter'),
                    reverse('hijack'),
                    reverse('charter_not_signed'),
                    reverse('accompanying'),
                    reverse('charter'),
                    reverse('immersion:change_password'),
                    reverse('django_cas:logout'),
                    reverse('shibboleth:logout'),
                ]
                if request.path not in exceptions:
                    if user.is_establishment_manager() or user.is_high_school_manager():
                        return HttpResponseRedirect(reverse('charter'))
                    else:
                        return HttpResponseRedirect(reverse('charter_not_signed'))

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response