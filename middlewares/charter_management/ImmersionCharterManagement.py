from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from immersionlyceens.apps.core.models import (
    GeneralSettings, HighSchool, ImmersionUser,
)
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

        if user.is_anonymous or user.is_visitor() or user.is_student() or user.is_high_school_student():
            return response

        try:
            highschool = user.high_school_student_record.highschool
        except (HighSchoolStudentRecord.DoesNotExist, HighSchool.DoesNotExist):
            if user.highschool:
                highschool = user.highschool

        if self.charter_sign:
            already_signed_charter = any([
                user.is_superuser,
                user.is_operator(),
                #user.is_student(), # FIXME WHEN WE KNOW HOW TO LINK A STUDENT WITH THE ESTABLISHMENT
                #user.is_high_school_student() and not highschool,
                user.establishment and (user.establishment.master or user.establishment.signed_charter),
                highschool and highschool.postbac_immersion and highschool.signed_charter,
                highschool and not highschool.postbac_immersion,
                user.is_visitor(),
            ])

            if not already_signed_charter:
                # Urls that can be accessed when charter is not signed
                reverse_exceptions = [
                    reverse('sign_charter'),
                    reverse('charter_not_signed'),
                    reverse('accompanying'),
                    reverse('charter'),
                    reverse('procedure'),
                    reverse('shibboleth_login'),
                    reverse('immersion:change_password'),
                    reverse('offer'),
                    reverse('offer_off_offer_events'),
                    reverse('immersion:change_password'),
                ]

                # Same thing with namespaces (allow all urls under)
                namespaces_exceptions = [
                    "/hijack",
                    "/accounts",
                    "/shib_secure",
                    "/dl/accdoc/",
                    "/offer/",
                    "/immersion/activate/",
                    "/immersion/login",
                    "/immersion/register",
                    "/api"
                ]

                conditions = [
                    request.path in reverse_exceptions,
                    any(map(lambda n:request.path.startswith(n), namespaces_exceptions))
                ]

                if not any(conditions):
                    if user.is_establishment_manager() or user.is_high_school_manager():
                        return HttpResponseRedirect(reverse('charter'))
                    else:
                        return HttpResponseRedirect(reverse('charter_not_signed'))

        # Code to be executed for each request/response after
        # the view is called.

        return response
