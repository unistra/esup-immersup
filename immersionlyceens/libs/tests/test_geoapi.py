"""
Django API tests suite
"""
import csv
import json
import unittest
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase
from django.utils.translation import pgettext, gettext_lazy as _
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Building, Calendar, Campus, CancelType, Course,
    CourseType, GeneralSettings, HighSchool, Immersion, ImmersionUser,
    MailTemplate, MailTemplateVars, Slot, Structure, Training, TrainingDomain,
    TrainingSubdomain, UserCourseAlert, Vacation,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord,
)

from immersionlyceens.libs.geoapi.utils import (
    get_cities, get_departments, get_json_from_url, get_zipcodes,
)

request_factory = RequestFactory()
request = request_factory.get('/admin')


class GEOAPITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group', 'group_permissions', 'high_school_levels', 'student_levels', 'post_bachelor_levels']

    def test_get_json_from_url(self):
        url = f'{settings.GEOAPI_BASE_URL}/departements?fields=nom,code'
        raises = True
        try:
            get_json_from_url(url)
            raises = False
        except Exception:
            pass
        self.assertFalse(raises)

        with self.assertRaises(Exception):
            get_json_from_url(f'{settings.GEOAPI_BASE_URL}/departement')  # wrong !

    def test_get_departments(self):
        # Failure
        tmp = settings.GEOAPI_BASE_URL
        settings.GEOAPI_BASE_URL = ''
        response = get_departments()
        settings.GEOAPI_BASE_URL = tmp
        self.assertEqual(response, '')

        # OK
        response = get_departments()
        for e in response:
            self.assertEqual(len(e), 2)

    def test_get_cities(self):
        # Failure
        response = get_cities()
        self.assertEqual(response, [])

        # OK
        response = get_cities(dep_code='67')
        for e in response:
            self.assertEqual(len(e), 2)

    def test_get_zipcodes(self):
        # No city
        response = get_zipcodes()
        self.assertEqual(response, [])

        # ok
        response = get_zipcodes(dep_code=67, city='Strasbourg')
        self.assertGreater(len(response), 0)
        for e in response:
            self.assertEqual(len(e), 2)
