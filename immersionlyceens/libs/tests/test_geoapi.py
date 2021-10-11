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
from django.utils.translation import pgettext
from django.utils.translation import ugettext_lazy as _
from immersionlyceens.apps.core.models import (AccompanyingDocument, Building,
                                               Calendar, Campus, CancelType,
                                               Structure, Course, CourseType,
                                               GeneralSettings, HighSchool,
                                               Immersion, ImmersionUser,
                                               MailTemplate, MailTemplateVars,
                                               Slot, Training, TrainingDomain,
                                               TrainingSubdomain,
                                               UserCourseAlert, Vacation)
from immersionlyceens.apps.immersion.models import (HighSchoolStudentRecord,
                                                    StudentRecord)
from immersionlyceens.libs.api.views import ajax_check_course_publication
from immersionlyceens.libs.geoapi.utils import (get_cities, get_departments,
                                                get_json_from_url,
                                                get_zipcodes)

request_factory = RequestFactory()
request = request_factory.get('/admin')


class GEOAPITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group']

    def setUp(self):
        GeneralSettings.objects.create(setting='MAIL_CONTACT_REF_ETAB', value='unittest@unittest.fr')
        self.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab', password='pass', email='immersion@no-reply.com', first_name='ref_etab', last_name='ref_etab',
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
        self.ref_str = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
        )
        self.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
        )
        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='speaker-immersion@no-reply.com',
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
        self.client.login(username='ref_etab', password='pass')

        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)
        Group.objects.get(name='INTER').user_set.add(self.speaker1)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str)
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
