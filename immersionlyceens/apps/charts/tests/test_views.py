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

from immersionlyceens.apps.core.models import HighSchoolLevel, PostBachelorLevel, StudentLevel, Establishment

class ChartsViewsTestCase(TestCase):
    """
    Tests for Charts app views
    """

    # This file contains a complete set of users, slots, etc
    fixtures = [
        'immersionlyceens/apps/charts/tests/fixtures/all_test.json',
        'high_school_levels', 'post_bachelor_levels', 'student_levels'
    ]


    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """
        cls.factory = RequestFactory()

        cls.master_establishment = Establishment.objects.first()

        cls.ref_etab_user = get_user_model().objects.get(username='test-ref-etab')
        cls.ref_etab_user.set_password('hiddenpassword')
        cls.ref_etab_user.establishment = cls.master_establishment
        cls.ref_etab_user.save()
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)

        cls.reflyc_user = get_user_model().objects.get(username='jeanjacquesmonnet')
        cls.reflyc_user.set_password('hiddenpassword')
        cls.reflyc_user.save()
        Group.objects.get(name='REF-LYC').user_set.add(cls.reflyc_user)


    def setUp(self):
        self.client = Client()
        self.client.login(username='test-ref-etab', password='hiddenpassword')


    def test_view_global_domains_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user

        response = self.client.get("/charts/global_domains_charts", request)

        self.assertEqual(response.context['part2_filters']['highschools'], [])
        self.assertEqual(response.context['part2_filters']['higher_institutions'], [])

        # This list MUST match the fixtures HighSchoolLevel objects
        self.assertEqual(
            [level for level in response.context['levels']],
            [level for level in HighSchoolLevel.objects.filter(active=True).order_by('order')]
        )
        self.assertEqual(response.context['part2_filters']['level'], 0)

        # Post with filters
        response = self.client.post("/charts/global_domains_charts",
            { 'level': ['3'], 'insts': ['[[0,2],[1,"0673021V"]]'] }
        )

        self.assertEqual(
            response.context['part2_filters']['highschools'],
            ['Strasbourg - Lycée Jean Monnet']
        )
        self.assertEqual(
            response.context['part2_filters']['higher_institutions'],
            ['Strasbourg - Université de Strasbourg']
        )
        self.assertEqual(response.context['part2_filters']['level'], 3)


    def test_view_global_registrations_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user
        # Get : no filter
        response = self.client.get("/charts/global_registrations_charts", request)

        self.assertEqual(response.context['part2_filters']['highschools'], [])
        self.assertEqual(response.context['part2_filters']['higher_institutions'], [])

        self.assertEqual(
            [level.id for level in response.context['levels']],
            [level.id for level in HighSchoolLevel.objects.filter(active=True).order_by('order')]
        )

        self.assertEqual(response.context['part1_level_filter'], 0)
        self.assertEqual(response.context['part2_filters']['level'], 0)

        # Post with filters
        response = self.client.post("/charts/global_registrations_charts",
            {'level': ['3'], 'insts': ['[[0,2],[1,"0673021V"]]']}
        )

        self.assertEqual(
            response.context['part2_filters']['highschools'],
            ['Strasbourg - Lycée Jean Monnet']
        )
        self.assertEqual(
            response.context['part2_filters']['higher_institutions'],
            ['Strasbourg - Université de Strasbourg']
        )
        self.assertEqual(response.context['part1_level_filter'], 0)
        self.assertEqual(response.context['part2_filters']['level'], 3)


    def test_view_slots_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user
        response = self.client.get(
            "/charts/slots_charts",
            {'establishment_id': self.master_establishment.id},
            request
        )

        self.assertEqual(response.context['establishment_id'], str(self.master_establishment.id))
        self.assertEqual(
            [e for e in response.context['establishments']],
            [e for e in Establishment.objects.filter(active=True).order_by('label')]
        )

    def test_view_global_trainings_charts(self):
        request = self.factory.get("/")
        request.user = self.ref_etab_user
        response = self.client.get("/charts/global_trainings_charts",  request)

        # As a master establishment manager, do not consider post bachelors levels (will be included in 'students')
        self.assertEqual(
            [h for h in response.context['high_school_levels']],
            [h for h in HighSchoolLevel.objects.filter(is_post_bachelor=False).order_by('order')]
        )