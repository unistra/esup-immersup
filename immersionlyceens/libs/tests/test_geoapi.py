"""
Django API tests suite
"""
import csv
import json
import unittest
from datetime import datetime, time, timedelta

from django.utils.translation import pgettext, ugettext_lazy as _
from django.template.defaultfilters import date as _date
from compat.templatetags.compat import url
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Building, Campus, Component, Course, CourseType, HighSchool, Slot,
    Training, TrainingDomain,
    TrainingSubdomain,
    Immersion, MailTemplateVars, MailTemplate, Calendar, CancelType, ImmersionUser, Vacation,
    UserCourseAlert, GeneralSettings)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.libs.api.views import ajax_check_course_publication

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase

from immersionlyceens.libs.geoapi.utils import (get_json_from_url, get_departments, get_cities,
                                                get_zipcodes)

request_factory = RequestFactory()
request = request_factory.get('/admin')


class GEOAPITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group']

    def setUp(self):
        GeneralSettings.objects.create(setting='MAIL_CONTACT_SCUIO_IP', value='unittest@unittest.fr')
        self.scuio_user = get_user_model().objects.create_user(
            username='scuio', password='pass', email='immersion@no-reply.com', first_name='scuio', last_name='scuio',
        )
        self.highschool_user = get_user_model().objects.create_user(
            username='hs', password='pass', email='hs@no-reply.com', first_name='high', last_name='SCHOOL',
        )
        self.highschool_user2 = get_user_model().objects.create_user(
            username='hs2', password='pass', email='hs2@no-reply.com', first_name='high2', last_name='SCHOOL2',
        )
        self.highschool_user3 = get_user_model().objects.create_user(
            username='hs3', password='pass', email='hs3@no-reply.com', first_name='high3', last_name='SCHOOL3',
        )
        self.ref_comp = get_user_model().objects.create_user(
            username='refcomp',
            password='pass',
            email='refcomp@no-reply.com',
            first_name='refcomp',
            last_name='refcomp',
        )
        self.teacher1 = get_user_model().objects.create_user(
            username='teacher1',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='teach',
            last_name='HER',
        )
        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
        )
        self.student = get_user_model().objects.create_user(
            username='student',
            password='pass',
            email='student@no-reply.com',
            first_name='student',
            last_name='STUDENT',
        )
        self.student2 = get_user_model().objects.create_user(
            username='student2',
            password='pass',
            email='student2@no-reply.com',
            first_name='student2',
            last_name='STUDENT2',
        )
        self.cancel_type = CancelType.objects.create(label='Hello world')
        self.client = Client()
        self.client.login(username='scuio', password='pass')

        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_comp)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user2)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user3)
        Group.objects.get(name='ETU').user_set.add(self.student)
        Group.objects.get(name='ETU').user_set.add(self.student2)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

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
