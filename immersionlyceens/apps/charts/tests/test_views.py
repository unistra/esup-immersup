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

from immersionlyceens.apps.core.models import HighSchoolLevel, PostBachelorLevel, StudentLevel

class ChartsViewsTestCase(TestCase):
    """
    Tests for Charts app views
    """

    # This file contains a complete set of users, slots, etc
    fixtures = [
        'immersionlyceens/apps/charts/tests/fixtures/all_test.json',
        'high_school_levels', 'post_bachelor_levels', 'student_levels'
    ]

    def setUp(self):
        self.factory = RequestFactory()

        self.ref_etab_user = get_user_model().objects.get(username='test-ref-etab')
        self.ref_etab_user.set_password('hiddenpassword')
        self.ref_etab_user.save()
        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)

        self.reflyc_user = get_user_model().objects.get(username='jeanjacquesmonnet')
        self.reflyc_user.set_password('hiddenpassword')
        self.reflyc_user.save()
        Group.objects.get(name='REF-LYC').user_set.add(self.reflyc_user)

        self.client = Client()
        self.client.login(username='test-ref-etab', password='hiddenpassword')

    def test_view_highschool_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user

        response = self.client.get("/charts/highschool_charts", request)
        self.assertEqual(response.context['highschools'],
             [{'id': 3, 'label': 'Lycée Coufignal', 'city': 'COLMAR'},
              {'id': 4, 'label': 'Lycée Jean Monnet', 'city': "L'ABERGEMENT-DE-VAREY"},
              {'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'},
              {'id': 6, 'label': 'Lycée Kléber', 'city': 'STRASBOURG'},
              {'id': 5, 'label': 'Lycée Marie Curie', 'city': 'STRASBOURG'}]
        )
        self.assertEqual(response.context['highschool_id'], '')

        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')
        response = self.client.get("/charts/highschool_charts", request)
        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)


    def test_view_highschool_domains_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user

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
            [(0, 'All')] + [(h.id, h.label) for h in HighSchoolLevel.objects.order_by('order')]
        )

        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')
        response = self.client.get("/charts/highschool_domains_charts", request)

        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)


    def test_view_global_domains_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user

        # Get : no filter
        response = self.client.get("/charts/global_domains_charts", request)

        self.assertEqual(response.context['highschools'], [])
        self.assertEqual(response.context['higher_institutions'], [])

        # This list MUST match the fixtures HighSchoolLevel objects
        self.assertEqual(response.context['levels'], [(0, 'All')]
            + [(h.id, h.label) for h in HighSchoolLevel.objects.order_by('order')])
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
        request.user = self.ref_etab_user
        # As ref-etab user
        response = self.client.get("/charts/trainings_charts", request)
        self.assertEqual(response.context['highschools'],
            [{'id': 3, 'label': 'Lycée Coufignal', 'city': 'COLMAR'},
             {'id': 4, 'label': 'Lycée Jean Monnet', 'city': "L'ABERGEMENT-DE-VAREY"},
             {'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'},
             {'id': 6, 'label': 'Lycée Kléber', 'city': 'STRASBOURG'},
             {'id': 5, 'label': 'Lycée Marie Curie', 'city': 'STRASBOURG'}]
            )
        self.assertEqual(response.context['highschool_id'], '')

        self.assertEqual(
            [level for level in response.context['levels']],
            [level for level in HighSchoolLevel.objects.filter(active=True).order_by('order')]
        )
        self.assertEqual(response.context['high_school_name'], None)

        # As high school referent
        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')
        response = self.client.get("/charts/trainings_charts", request)

        self.assertEqual(response.context['highschools'],
            [{'id': 2, 'label': 'Lycée Jean Monnet', 'city': 'STRASBOURG'}])
        self.assertEqual(response.context['highschool_id'], 2)
        self.assertEqual(
            [level for level in response.context['levels']],
            [level for level in HighSchoolLevel.objects.filter(active=True).order_by('order')]
        )
        self.assertEqual(response.context['high_school_name'], "Lycée Jean Monnet")


    def test_view_global_registrations_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user
        # Get : no filter
        response = self.client.get("/charts/global_registrations_charts", request)

        self.assertEqual(response.context['highschools'], [])
        self.assertEqual(response.context['higher_institutions'], [])
        self.assertEqual(response.context['levels'], [(0, 'All')]
            + [(h.id, h.label) for h in HighSchoolLevel.objects.order_by('order')])
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
        request.user = self.ref_etab_user
        response = self.client.get("/charts/global_slots_charts", request)

        # Not much to test here, as data is gathered with ajax queries
        self.assertEqual(response.status_code, 200)