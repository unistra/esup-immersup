"""
Charts Views tests
"""
import datetime
import pprint
import json

from django.contrib.auth import get_user_model
from django.utils.formats import date_format
from django.test import Client, RequestFactory, TestCase
from django.conf import settings
from django.contrib.auth.models import Group

from .. import views

class ChartsViewsTestCase(TestCase):
    """
    Tests for Charts app views
    """

    # This file contains a complete set of users, slots, etc
    fixtures = ['immersionlyceens/apps/charts/tests/fixtures/all_test.json']

    def setUp(self):
        self.factory = RequestFactory()

        self.scuio_user = get_user_model().objects.get(username='test-scuio-ip')
        self.scuio_user.set_password('hiddenpassword')
        self.scuio_user.save()
        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)

        self.reflyc_user = get_user_model().objects.get(username='jeanmonnet')
        self.reflyc_user.set_password('hiddenpassword')
        self.reflyc_user.save()
        Group.objects.get(name='REF-LYC').user_set.add(self.reflyc_user)

        self.client = Client()
        self.client.login(username='test-scuio-ip', password='hiddenpassword')

    def test_view_highschool_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user

        response = self.client.get("/charts/highschool_charts", request)
        self.assertEqual(response.context['highschools'],
             [{'id': 3, 'label': 'Lycée Coufignal', 'city': 'COLMAR'},
              {'id': 4, 'label': 'Lycée Jean Monnet', 'city': "L'ABERGEMENT-DE-VAREY"},
              {'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'},
              {'id': 6, 'label': 'Lycée Kléber', 'city': 'STRASBOURG'},
              {'id': 5, 'label': 'Lycée Marie Curie', 'city': 'STRASBOURG'}]
        )
        self.assertEqual(response.context['highschool_id'], '')

        self.client.login(username='jeanmonnet', password='hiddenpassword')
        response = self.client.get("/charts/highschool_charts", request)
        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)


    def test_view_highschool_domains_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user

        response = self.client.get("/charts/highschool_domains_charts", request)
        self.assertEqual(response.context['highschools'],
             [{'id': 3, 'label': 'Lycée Coufignal', 'city': 'COLMAR'},
              {'id': 4, 'label': 'Lycée Jean Monnet', 'city': "L'ABERGEMENT-DE-VAREY"},
              {'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'},
              {'id': 6, 'label': 'Lycée Kléber', 'city': 'STRASBOURG'},
              {'id': 5, 'label': 'Lycée Marie Curie', 'city': 'STRASBOURG'}]
        )
        self.assertEqual(response.context['highschool_id'], '')
        self.assertEqual(response.context['levels'],
            [(0, 'All'), (1, 'Pupil in year 12 / 11th grade student'), (2, 'Pupil in year 13 / 12th grade student'),
             (3, 'Above A Level / High-School Degree')]
        )

        self.client.login(username='jeanmonnet', password='hiddenpassword')
        response = self.client.get("/charts/highschool_domains_charts", request)

        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)


    def test_view_global_domains_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user

        # Get : no filter
        response = self.client.get("/charts/global_domains_charts", request)

        self.assertEqual(response.context['highschools'], [])
        self.assertEqual(response.context['higher_institutions'], [])
        self.assertEqual(response.context['levels'], [(0, 'All'), (1, 'Pupil in year 12 / 11th grade student'),
            (2, 'Pupil in year 13 / 12th grade student'), (3, 'Above A Level / High-School Degree')])
        self.assertEqual(response.context['level_filter'], 0)

        # Post with filters
        response = self.client.post("/charts/global_domains_charts",
            { 'level': ['3'], 'insts': ['[[0,2],[1,"0673021V"]]'] }
        )

        self.assertEqual(response.context['highschools'], ['Strasbourg - Lycée Jean Monnet'])
        self.assertEqual(response.context['higher_institutions'], ['Strasbourg - Université de Strasbourg'])
        self.assertEqual(response.context['level_filter'], 3)


    def test_view_trainings_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user
        # As scuio-ip user
        response = self.client.get("/charts/trainings_charts", request)
        self.assertEqual(response.context['highschools'],
            [{'id': 3, 'label': 'Lycée Coufignal', 'city': 'COLMAR'},
             {'id': 4, 'label': 'Lycée Jean Monnet', 'city': "L'ABERGEMENT-DE-VAREY"},
             {'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'},
             {'id': 6, 'label': 'Lycée Kléber', 'city': 'STRASBOURG'},
             {'id': 5, 'label': 'Lycée Marie Curie', 'city': 'STRASBOURG'}]
            )
        self.assertEqual(response.context['highschool_id'], '')
        self.assertEqual(response.context['levels'],
            [(1, 'Pupil in year 12 / 11th grade student'), (2, 'Pupil in year 13 / 12th grade student'),
             (3, 'Above A Level / High-School Degree')]
        )
        self.assertEqual(response.context['high_school_name'], None)

        # As high school referent
        self.client.login(username='jeanmonnet', password='hiddenpassword')
        response = self.client.get("/charts/trainings_charts", request)

        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)
        self.assertEqual(response.context['levels'],
            [(1, 'Pupil in year 12 / 11th grade student'), (2, 'Pupil in year 13 / 12th grade student'),
             (3, 'Above A Level / High-School Degree')]
        )
        self.assertEqual(response.context['high_school_name'], "Lycée Jean Monnet")


    def test_view_global_registrations_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user
        # Get : no filter
        response = self.client.get("/charts/global_registrations_charts", request)

        self.assertEqual(response.context['highschools'], [])
        self.assertEqual(response.context['higher_institutions'], [])
        self.assertEqual(response.context['levels'], [(0, 'All'), (1, 'Pupil in year 12 / 11th grade student'),
            (2, 'Pupil in year 13 / 12th grade student'), (3, 'Above A Level / High-School Degree')])
        self.assertEqual(response.context['part1_level_filter'], 0)
        self.assertEqual(response.context['level_filter'], 0)

        # Post with filters
        response = self.client.post("/charts/global_registrations_charts",
            {'level': ['3'], 'insts': ['[[0,2],[1,"0673021V"]]']}
        )

        self.assertEqual(response.context['highschools'], ['Strasbourg - Lycée Jean Monnet'])
        self.assertEqual(response.context['higher_institutions'], ['Strasbourg - Université de Strasbourg'])
        self.assertEqual(response.context['part1_level_filter'], 0)
        self.assertEqual(response.context['level_filter'], 3)


    def test_view_global_slots_charts(self):
        request = self.factory.get("/")
        request.user = self.scuio_user
        response = self.client.get("/charts/global_slots_charts", request)

        # Not much to test here, as data is gathered with ajax queries
        self.assertEqual(response.status_code, 200)