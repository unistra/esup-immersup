"""
Charts API tests
"""
import json
import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, RequestFactory, TestCase
from django.contrib.auth.models import Group

from immersionlyceens.apps.core.models import (
    HighSchoolLevel, PostBachelorLevel, StudentLevel, Establishment, HighSchool
)

from .. import api

class ChartsAPITestCase(TestCase):
    """Tests for API"""

    # This file contains a complete set of users, slots, etc
    fixtures = ['high_school_levels', 'post_bachelor_levels', 'student_levels', 'group', 'generalsettings',
        'immersionlyceens/apps/charts/tests/fixtures/all_test.json',
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """
        cls.factory = RequestFactory()

        cls.master_establishment = Establishment.objects.filter(master=True).first()

        cls.ref_etab_user = get_user_model().objects.get(username='test-ref-etab')
        cls.ref_etab_user.set_password('hiddenpassword')
        cls.ref_etab_user.save()
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)

        cls.ref_master_etab_user = get_user_model().objects.get(username='test-ref-etab-maitre')
        cls.ref_master_etab_user.establishment = cls.master_establishment
        cls.ref_master_etab_user.set_password('hiddenpassword')
        cls.ref_master_etab_user.save()
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user)

        cls.reflyc_user = get_user_model().objects.get(username='jeanjacquesmonnet')
        cls.reflyc_user.set_password('hiddenpassword')
        cls.reflyc_user.save()
        Group.objects.get(name='REF-LYC').user_set.add(cls.reflyc_user)

        cls.ref_str_user = get_user_model().objects.get(username='test-eco')
        cls.ref_str_user.set_password('hiddenpassword')
        cls.ref_str_user.save()

        cls.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        # Extend the first high school convention end date (other can stay in past)
        now = datetime.datetime.today().date()
        HighSchool.objects.filter(pk=2).update(convention_end_date=now + datetime.timedelta(days=30))


    def setUp(self):
        self.client = Client()


    def test_global_domains_charts_by_population(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')
        # Global domain charts
        url = "/charts/get_global_domains_charts_by_population"
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'domain': 'Art, Lettres, Langues', 'count': 24,
               'subData': [{'name': 'Art plastiques', 'count': 12}, {'name': 'Art visuels', 'count': 12}]},
              {'domain': 'Droit, Economie, Gestion', 'count': 6,
               'subData': [{'name': 'Economie, Gestion', 'count': 6}]},
              {'domain': 'Sciences Humaines et sociales', 'count': 3,
               'subData': [{'name': 'Sport', 'count': 3}]},
              {'domain': 'Sciences et Technologies', 'count': 20,
               'subData': [{'name': 'Informatique', 'count': 10},
                           {'name': 'Mathématiques', 'count': 10}]}]
        )

        # Test with filter
        response = self.client.post(url,
            {'highschools_ids[]': [2]}
        )

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'domain': 'Art, Lettres, Langues', 'count': 15,
               'subData': [{'name': 'Art plastiques', 'count': 7}, {'name': 'Art visuels', 'count': 8}]},
              {'domain': 'Droit, Economie, Gestion', 'count': 5,
               'subData': [{'name': 'Economie, Gestion', 'count': 5}]},
              {'domain': 'Sciences Humaines et sociales', 'count': 2,
               'subData': [{'name': 'Sport', 'count': 2}]},
              {'domain': 'Sciences et Technologies', 'count': 11,
               'subData': [{'name': 'Informatique', 'count': 4},
                           {'name': 'Mathématiques', 'count': 7}]}]
        )

        # As a high school manager
        self.client.login(username='test-ref-lyc', password='hiddenpassword')
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'domain': 'Art, Lettres, Langues', 'count': 24,
              'subData': [{'name': 'Art plastiques', 'count': 12}, {'name': 'Art visuels', 'count': 12}]},
             {'domain': 'Droit, Economie, Gestion', 'count': 6,
              'subData': [{'name': 'Economie, Gestion', 'count': 6}]},
             {'domain': 'Sciences Humaines et sociales', 'count': 3,
              'subData': [{'name': 'Sport', 'count': 3}]},
             {'domain': 'Sciences et Technologies', 'count': 20,
              'subData': [{'name': 'Informatique', 'count': 10}, {'name': 'Mathématiques', 'count': 10}]}]
        )

        # With a filter on level
        response = self.client.post(url, {'level': 2})
        content = response.content.decode()
        json_content = json.loads(content)
        self.assertEqual(json_content['datasets'],
            [{'domain': 'Art, Lettres, Langues', 'count': 9,
              'subData': [{'name': 'Art plastiques', 'count': 4}, {'name': 'Art visuels', 'count': 5}]},
             {'domain': 'Droit, Economie, Gestion', 'count': 3,
              'subData': [{'name': 'Economie, Gestion', 'count': 3}]},
             {'domain': 'Sciences Humaines et sociales', 'count': 1,
              'subData': [{'name': 'Sport', 'count': 1}]},
             {'domain': 'Sciences et Technologies', 'count': 9,
              'subData': [{'name': 'Informatique', 'count': 4}, {'name': 'Mathématiques', 'count': 5}]}]
        )


    def test_global_domains_charts_by_trainings(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')
        # Global domain charts
        url = "/charts/get_global_domains_charts_by_trainings"
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
           [{'domain': 'Art, Lettres, Langues', 'count': 24,
             'subData': [{'name': 'Art plastiques', 'count': 12}, {'name': 'Art visuels', 'count': 12}]},
            {'domain': 'Droit, Economie, Gestion', 'count': 6,
             'subData': [{'name': 'Economie, Gestion', 'count': 6}]},
            {'domain': 'Sciences Humaines et sociales', 'count': 3,
             'subData': [{'name': 'Sport', 'count': 3}]},
            {'domain': 'Sciences et Technologies', 'count': 20,
             'subData': [{'name': 'Informatique', 'count': 10}, {'name': 'Mathématiques', 'count': 10}]}]
        )

        # With a level filter
        response = self.client.post(url, {'level': 1})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content["datasets"],
            [{'domain': 'Art, Lettres, Langues', 'count': 12,
              'subData': [{'name': 'Art plastiques', 'count': 6}, {'name': 'Art visuels', 'count': 6}]},
              {'domain': 'Droit, Economie, Gestion', 'count': 2,
               'subData': [{'name': 'Economie, Gestion', 'count': 2}]},
              {'domain': 'Sciences Humaines et sociales', 'count': 1,
               'subData': [{'name': 'Sport', 'count': 1}]},
              {'domain': 'Sciences et Technologies', 'count': 7,
               'subData': [{'name': 'Informatique', 'count': 4}, {'name': 'Mathématiques', 'count': 3}]}]
        )


        # as a master establishment manager with a filter on a highschool
        # FIXME : add test data : highschool courses, slots and immersions
        """
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')
        response = self.client.post(url, {'highschools_ids[]': [5]})
        content = response.content.decode()
        json_content = json.loads(content)

        # As a high school manager
        self.client.login(username='test-ref-lyc', password='hiddenpassword')
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)
        """


    def test_charts_filters_data_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Charts filter data (ajax request : use headers)
        url = "/charts/get_charts_filters_data"
        response = self.client.get(
            url,
            {
                'filter_by_my_trainings': "true",
                'include_structures': "true",
            },
            **self.header
        )

        content = response.content.decode()
        json_content = json.loads(content)

        # As a non-master referent, we should only see his establishment structures

        self.assertEqual(json_content['data'],
             [{'institution': 'Université de Strasbourg',
               'structure': 'Faculté des Arts',
               'structure_id': 1,
               'institution_id': '',
               'type': 'Higher education institution',
               'type_code': 2,
               'city': '67081 - STRASBOURG',
               'department': 'BAS-RHIN',
               'country': ''
              },
              {'institution': 'Université de Strasbourg',
               'structure': 'Faculté des Sciences économiques et de gestion',
               'structure_id': 6,
               'institution_id': '',
               'type': 'Higher education institution',
               'type_code': 2,
               'city': '67081 - STRASBOURG',
               'department': 'BAS-RHIN',
               'country': ''
              },
              {'institution': 'Université de Strasbourg',
               'structure': 'Faculté des sciences du sport',
               'structure_id': 3,
               'institution_id': '',
               'type': 'Higher education institution',
               'type_code': 2,
               'city': '67081 - STRASBOURG', 'department':
               'BAS-RHIN', 'country': ''
              },
              {'institution': 'Université de Strasbourg',
               'structure': 'IUT Louis Pasteur',
               'structure_id': 7,
               'institution_id': '',
               'type': 'Higher education institution',
               'type_code': 2,
               'city': '67081 - STRASBOURG',
               'department': 'BAS-RHIN',
               'country': ''
              },
              {'institution': 'Université de Strasbourg',
               'structure': 'UFR Mathématiques et Informatique',
               'structure_id': 2,
               'institution_id': '',
               'type': 'Higher education institution',
               'type_code': 2,
               'city': '67081 - STRASBOURG',
               'department': 'BAS-RHIN',
               'country': ''
              }]
        )

        # As a master establishment manager : see all establishments and high schools
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')
        response = self.client.get(
            url,
            {
                'filter_by_my_trainings': "true",
                'include_structures': "true",
            },
            **self.header
        )

        content = response.content.decode()
        json_content = json.loads(content)
        self.assertEqual(json_content['data'], [{
                'institution': 'Université de Strasbourg',
                'institution_id': 1,
                'structure_id': '',
                'type': 'Higher education institution',
                'type_code': 1,
                'city': 'STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }, {
                'institution': 'Université de Strasbourg',
                'structure': 'Faculté des Arts',
                'structure_id': 1,
                'institution_id': '',
                'type': 'Higher education institution',
                'type_code': 2,
                'city': '67081 - STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }, {
                'institution': 'Université de Strasbourg',
                'structure': 'Faculté des Sciences économiques et de gestion',
                'structure_id': 6,
                'institution_id': '',
                'type': 'Higher education institution',
                'type_code': 2,
                'city': '67081 - STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }, {
                'institution': 'Université de Strasbourg',
                'structure': 'Faculté des sciences du sport',
                'structure_id': 3,
                'institution_id': '',
                'type': 'Higher education institution',
                'type_code': 2,
                'city': '67081 - STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }, {
                'institution': 'Université de Strasbourg',
                'structure': 'IUT Louis Pasteur',
                'structure_id': 7,
                'institution_id': '',
                'type': 'Higher education institution',
                'type_code': 2,
                'city': '67081 - STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }, {
                'institution': 'Université de Strasbourg',
                'structure': 'UFR Mathématiques et Informatique',
                'structure_id': 2,
                'institution_id': '',
                'type': 'Higher education institution',
                'type_code': 2,
                'city': '67081 - STRASBOURG',
                'department': 'BAS-RHIN',
                'country': ''
            }]
        )

        # With no filter by training (filter by population)
        # We should only see establishments (and high schools) students and pupils can come from (no structures)
        response = self.client.get(url, {'filter_by_my_trainings': "false"}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)
        self.assertEqual(json_content['data'], [{
                 'institution': 'Lycée Coufignal',
                 'institution_id': 3,
                 'structure_id': '',
                 'type': 'Highschool',
                 'type_code': 0,
                 'city': '68000 - COLMAR',
                 'department': '68',
                 'country': ''
             }, {
                 'institution': 'Lycée Jean Monnet',
                 'institution_id': 2,
                 'structure_id': '',
                 'type': 'Highschool',
                 'type_code': 0,
                 'city': '67100 - STRASBOURG',
                 'department': '67',
                 'country': ''
             }, {
                 'institution': 'Lycée Kléber',
                 'institution_id': 6,
                 'structure_id': '',
                 'type': 'Highschool',
                 'type_code': 0,
                 'city': '67000 - STRASBOURG',
                 'department': '67',
                 'country': ''
             }, {
                 'institution': 'Lycée Marie Curie',
                 'institution_id': 5,
                 'structure_id': '',
                 'type': 'Highschool',
                 'type_code': 0,
                 'city': '67100 - STRASBOURG',
                 'department': '67',
                 'country': ''
             }, {
                 'institution': 'Université de Strasbourg',
                 'institution_id': '0673021V',
                 'structure_id': '',
                 'type': 'Higher education institution',
                 'type_code': 1,
                 'city': ['67081 - Strasbourg'],
                 'department': ['Bas-Rhin'],
                 'country': ['France']
             }]
        )

    def test_global_trainings_charts_api(self):
        """
        Global (all establishments) training charts (ajax request : use headers)
        """
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')

        url = "/charts/get_global_trainings_charts"
        response = self.client.get(url, {'empty_trainings': 'true'}, **self.header)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(
            json_content["columns"],
            [{'data': 'establishment',
              'name': 'establishment',
              'title': 'Establishment',
              'filter': 'establishment_filter'
            },{'data': 'structure',
              'name': 'structures',
              'title': 'Structure(s)',
              'filter': 'structure_filter'
             },
             {'data': 'domain_label',
              'name': 'domain_subdomain',
              'title': 'Domain/Subdomain',
              'filter': 'domain_filter'
             },
             {'data': 'training_label',
              'name': 'training',
              'title': 'Training',
              'filter': 'training_filter'
             },
             {'data': 'unique_persons',
              'name': 'persons_cnt',
              'title': 'Persons cnt'
             },
             *[{
                 "data": f"unique_students_lvl{level.id}",
                 "name": f"pupils_cnt_{level.label}",
                 "title": "Pupils cnt<br>%s" % level.label,
                 "visible": False,
             } for level in HighSchoolLevel.objects.filter(active=True, is_post_bachelor=False)
             ],
             {'data': 'unique_students',
              'name': 'students_cnt',
              'title': 'Students cnt',
              'visible': False
             },
             {'data': 'unique_visitors',
              'name': 'visitors_cnt',
              'title': 'Visitors cnt',
              'visible': False
             },
             {'data': 'all_registrations',
              'name': 'registrations',
              'title': 'Registrations'
             },
             *[{
                 'data': f"registrations_lvl{level.id}",
                 "name": f"registrations_{level.label}",
                 "title": "Registrations<br>%s" % level.label,
                 'visible': False,
             } for level in HighSchoolLevel.objects.filter(active=True, is_post_bachelor=False)
             ],
             {'data': 'students_registrations',
              'name': 'students_registrations',
              'title': 'Students<br>registrations',
              'visible': False
             },
             {'data': 'visitors_registrations',
              'name': 'visitors_registrations',
              'title': 'Visitors<br>registrations',
              'visible': False
             }
          ]
        )

        self.assertEqual(
            json_content["yadcf"],
            [{'column_selector': "establishment:name",
              'filter_default_label': "",
              'filter_match_mode': "exact",
              'filter_container_id': "establishment_filter",
              'style_class': "form-control form-control-sm",
              'filter_reset_button_text': False,
             },{'column_selector': 'structures:name',
              'text_data_delimiter': '<br>',
              'filter_default_label': '',
              'filter_match_mode': 'contains',
              'filter_container_id': 'structure_filter',
              'style_class': 'form-control form-control-sm',
              'filter_reset_button_text': False
             },
             {'column_selector': 'domain_subdomain:name',
              'text_data_delimiter': '<br>',
              'filter_default_label': '',
              'filter_match_mode': 'contains',
              'filter_container_id': 'domain_filter',
              'style_class': 'form-control form-control-sm',
              'filter_reset_button_text': False
             },
             {'column_selector': 'training:name',
              'filter_default_label': '',
              'filter_match_mode': 'exact',
              'filter_container_id': 'training_filter',
              'style_class': 'form-control form-control-sm',
              'filter_reset_button_text': False
              }]
        )
        self.assertEqual(json_content["order"], [[0, 'asc'], [1, 'asc'], [2, 'asc']])

        self.assertEqual(json_content["data"], [
            {'establishment': 'Université de Strasbourg',
             'structure': 'IUT Louis Pasteur',
             'training_label': 'DUT Informatique',
             'domain_label': 'Sciences et Technologies<br>- Informatique',
             'unique_persons': 5,
             'unique_visitors': 0,
             'all_registrations': 5,
             'visitors_registrations': 0,
             'unique_students_lvl1': 2,
             'registrations_lvl1': 2,
             'unique_students_lvl2': 2,
             'registrations_lvl2': 2,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 1,
             'unique_students': 0,
             'students_registrations': 0
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'Faculté des Arts',
             'training_label': 'Licence Arts Plastiques & Design',
             'domain_label': 'Art, Lettres, Langues<br>- Art plastiques',
             'unique_persons': 7,
             'unique_visitors': 0,
             'all_registrations': 12,
             'visitors_registrations': 0,
             'unique_students_lvl1': 3,
             'registrations_lvl1': 6,
             'unique_students_lvl2': 3,
             'registrations_lvl2': 4,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 2,
             'unique_students': 0,
             'students_registrations': 0
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'Faculté des Arts',
             'training_label': 'Licence Arts du Spectacle',
             'domain_label': 'Art, Lettres, Langues<br>- Art visuels',
             'unique_persons': 7,
             'unique_visitors': 0,
             'all_registrations': 12,
             'visitors_registrations': 0,
             'unique_students_lvl1': 3,
             'registrations_lvl1': 6,
             'unique_students_lvl2': 3,
             'registrations_lvl2': 5,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 1,
             'unique_students': 0,
             'students_registrations': 0
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'UFR Mathématiques et Informatique',
             'training_label': 'Licence Informatique',
             'domain_label': 'Sciences et Technologies<br>- Informatique',
             'unique_persons': 5,
             'unique_visitors': 0,
             'all_registrations': 5,
             'visitors_registrations': 0,
             'unique_students_lvl1': 2,
             'registrations_lvl1': 2,
             'unique_students_lvl2': 2,
             'registrations_lvl2': 2,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 1,
             'unique_students': 0,
             'students_registrations': 0
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'Faculté des Sciences économiques et de gestion<br>UFR Mathématiques et Informatique',
             'training_label': 'Licence Maths-Eco',
             'domain_label': 'Droit, Economie, Gestion<br>- Economie, Gestion<br>Sciences et Technologies<br>- Mathématiques',
             'unique_persons': 4,
             'unique_visitors': 0,
             'all_registrations': 6,
             'visitors_registrations': 0,
             'unique_students_lvl1': 1,
             'registrations_lvl1': 2,
             'unique_students_lvl2': 2,
             'registrations_lvl2': 3,
             'unique_students_lvl3': 0,
             'registrations_lvl3': 0,
             'unique_students': 1,
             'students_registrations': 1
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'UFR Mathématiques et Informatique',
             'training_label': 'Licence Mathématiques',
             'domain_label': 'Sciences et Technologies<br>- Mathématiques',
             'unique_persons': 3,
             'unique_visitors': 0,
             'all_registrations': 4,
             'visitors_registrations': 0,
             'unique_students_lvl1': 1,
             'registrations_lvl1': 1,
             'unique_students_lvl2': 1,
             'registrations_lvl2': 2,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 1,
             'unique_students': 0,
             'students_registrations': 0
            },
            {'establishment': 'Université de Strasbourg',
             'structure': 'Faculté des sciences du sport',
             'training_label': 'Licence STAPS',
             'domain_label': 'Sciences Humaines et sociales<br>- Sport',
             'unique_persons': 3,
             'unique_visitors': 0,
             'all_registrations': 3,
             'visitors_registrations': 0,
             'unique_students_lvl1': 1,
             'registrations_lvl1': 1,
             'unique_students_lvl2': 1,
             'registrations_lvl2': 1,
             'unique_students_lvl3': 1,
             'registrations_lvl3': 1,
             'unique_students': 0,
             'students_registrations': 0
            }]
        )

    def test_registration_charts_by_population(self):
        # Registration charts
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')
        url = "/charts/get_registration_charts_by_population"

        # All highschools and establishments by default (no highschool_id parameter)
        response = self.client.get(url, {'level': 0})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'name': 'Attended to at least one immersion',
               HighSchoolLevel.objects.get(pk=1).label: 2,
               HighSchoolLevel.objects.get(pk=2).label: 2,
               HighSchoolLevel.objects.get(pk=3).label: 0,
               HighSchoolLevel.objects.get(pk=4).label: 0,
               'Visitors': 0,
               'none': 0
              },
              {'name': 'Registrations to at least one immersion',
               HighSchoolLevel.objects.get(pk=1).label: 3,
               HighSchoolLevel.objects.get(pk=2).label: 4,
               HighSchoolLevel.objects.get(pk=3).label: 1,
               HighSchoolLevel.objects.get(pk=4).label: 1,
               'Visitors': 0,
               'none': 0
              },
              {'name': 'Registrations count',
               HighSchoolLevel.objects.get(pk=1).label: 4,
               HighSchoolLevel.objects.get(pk=2).label: 4,
               HighSchoolLevel.objects.get(pk=3).label: 2,
               HighSchoolLevel.objects.get(pk=4).label: 2,
               'Visitors': 0,
               'none': 0
              },]
        )

        # With another level
        response = self.client.get(url, {'level': 1})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'], [{
            'name': 'Attended to at least one immersion',
            HighSchoolLevel.objects.get(pk=1).label: 2,
            'none': 0
        }, {
            'name': 'Registrations to at least one immersion',
            HighSchoolLevel.objects.get(pk=1).label: 3,
            'none': 0
        }, {
            'name': 'Registrations count',
            HighSchoolLevel.objects.get(pk=1).label: 4,
            'none': 0
        }
        ])

        # As a school manager : median will be displayed
        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')

        # The highschool_id parameter is not needed (default = the manager highschool)
        response = self.client.get(url, {'level': 0})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'name': 'Attended to at least one immersion [bold](m = 2)[/bold]',
              HighSchoolLevel.objects.get(pk=1).label: 1,
              HighSchoolLevel.objects.get(pk=2).label: 1,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0,
              'none': 0},
             {'name': 'Registrations to at least one immersion [bold](m = 5)[/bold]',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0,
              'none': 0},
             {'name': 'Registrations count [bold](m = 5)[/bold]',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1,
              'none': 0
             }]
        )

    def test_registration_charts_by_training(self):
        # Registration charts
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')
        url = "/charts/get_registration_charts_by_trainings"

        response = self.client.get(url, {'level': 0})
        content = response.content.decode()
        json_content = json.loads(content)

        # As a master establishment manager, charts include by default trainings of all establishments/high schools
        self.assertEqual(json_content['datasets'], [{
                'name': 'Attended to at least one immersion',
                'none': 0,
                'Seconde': 2,
                'Première': 2,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {
                'name': 'Registrations to at least one immersion',
                'none': 0,
                'Seconde': 3,
                'Première': 4,
                'Terminale': 1,
                'Post-bac': 1,
                'Visitors': 0
            }, {
                'name': 'Registrations count',
                'none': 0,
                'Seconde': 4,
                'Première': 4,
                'Terminale': 2,
                'Post-bac': 2,
                'Visitors': 0
            }]
        )

        # Filter by structure : see only registrations for trainings of this structure
        # This one includes the calculation of the median accross structures of the same establishment
        self.client.login(username='test-eco', password='hiddenpassword')
        response = self.client.get(url, {'level': 0, 'structure_id': 6})

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content["datasets"], [{
                'name': 'Attended to at least one immersion [bold](m = 1)[/bold]',
                'none': 0,
                'Seconde': 1,
                'Première': 0,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {
                'name': 'Registrations to at least one immersion [bold](m = 7)[/bold]',
                'none': 0,
                'Seconde': 1,
                'Première': 1,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {
                'name': 'Registrations count',
                'none': 0,
                'Seconde': 4,
                'Première': 4,
                'Terminale': 2,
                'Post-bac': 2,
                'Visitors': 0
            }]
        )


    def test_registration_charts_cats_by_population(self):
        """
        Charts by population with filters on establishments and high schools
        """
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')

        # Registration charts cats (ajax query, headers needed)
        url = "/charts/get_registration_charts_cats_by_population"
        response = self.client.post(url,
            {'highschools_ids[]': [2], 'higher_institutions_ids[]': ['0673021V']}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 1,
              HighSchoolLevel.objects.get(pk=2).label: 1,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0,
              'none': 0
             },
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=4).label: 0,
              'none': 0
             }]
        )

        self.assertEqual(json_content['one_immersion']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0,
              'none': 0},
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=4).label: 1,
              'none': 0
             }]
        )

        self.assertEqual(json_content['platform_regs']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1,
              'none': 0},
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=4).label: 1,
              'none': 0
             }]
        )

        response = self.client.post(url, {'highschools_ids[]': [2], 'level': 1}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'], [{
            HighSchoolLevel.objects.get(pk=1).label: 1,
            'name': 'Lycée Jean Monnet',
            'none': 0
        }])

        self.assertEqual(json_content['one_immersion']['datasets'], [{
            HighSchoolLevel.objects.get(pk=1).label: 2,
            'name': 'Lycée Jean Monnet',
            'none': 0
        }])

        self.assertEqual(json_content['platform_regs']['datasets'], [{
            HighSchoolLevel.objects.get(pk=1).label: 2,
            'name': 'Lycée Jean Monnet',
            'none': 0
        }])


    def test_get_registration_charts_cats_by_trainings(self):
        """
        Charts by trainings with filters on establishments, structures and high schools
        """
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')

        # Registration charts cats (ajax query, headers needed)
        url = "/charts/get_registration_charts_cats_by_trainings"
        response = self.client.post(
            url,
            {
                'highschools_ids[]': [2],
                'higher_institutions_ids[]': [self.master_establishment.id],
                'structure_ids[]': [6]
            },
            **self.header
        )

        content = response.content.decode()
        json_content = json.loads(content)

        # TODO : add test data for high schools with postbac immersions
        self.assertEqual(json_content['one_immersion']["datasets"], [{
                'name': 'Lycée Jean Monnet',
                'none': 0,
                'Seconde': 0,
                'Première': 0,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {'name': 'Université de Strasbourg',
                'none': 0,
                'Seconde': 3,
                'Première': 4,
                'Terminale': 1,
                'Post-bac': 1,
                'Visitors': 0
            }, {'name': 'Unistra - Faculté des Sciences économiques et de gestion',
                'none': 0,
                'Seconde': 1,
                'Première': 1,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0}]
        )

        self.assertEqual(json_content['attended_one']["datasets"],  [{
                'name': 'Lycée Jean Monnet',
                'none': 0,
                'Seconde': 0,
                'Première': 0,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {'name': 'Université de Strasbourg',
                'none': 0,
                'Seconde': 2,
                'Première': 2,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0
            }, {'name': 'Unistra - Faculté des Sciences économiques et de gestion',
                'none': 0,
                'Seconde': 1,
                'Première': 0,
                'Terminale': 0,
                'Post-bac': 0,
                'Visitors': 0}]
        )

    def test_get_slots_charts(self):
        """
        Test slots charts
        """
        self.client.login(username='test-ref-etab-maitre', password='hiddenpassword')
        url = "/charts/get_slots_charts"
        response = self.client.post(
            url,
            {
                'empty_structures': 'false',
                'establishment_id': self.master_establishment.id
            },
            **self.header
        )
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'], [
            {
                'name': 'IUT Louis Pasteur (Unistra)',
                'slots_count': 1,
                'percentage': 1.9,
                'none': 0
            }, {
                'name': 'Faculté des sciences du sport (Unistra)',
                'slots_count': 5,
                'percentage': 9.4,
                'none': 0
            }, {
                'name': 'Faculté des Sciences économiques et de gestion (Unistra)',
                'slots_count': 9,
                'percentage': 17.0,
                'none': 0
            }, {
                'name': 'UFR Mathématiques et Informatique (Unistra)',
                'slots_count': 17,
                'percentage': 32.1,
                'none': 0
            }, {
                'name': 'Faculté des Arts (Unistra)',
                'slots_count': 21,
                'percentage': 39.6,
                'none': 0
            }]
        )