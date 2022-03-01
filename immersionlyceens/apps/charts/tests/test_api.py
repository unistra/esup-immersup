"""
Charts API tests
"""
import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, RequestFactory, TestCase
from django.contrib.auth.models import Group

from immersionlyceens.apps.core.models import HighSchoolLevel, PostBachelorLevel, StudentLevel, Establishment

from .. import api

class ChartsAPITestCase(TestCase):
    """Tests for API"""

    # This file contains a complete set of users, slots, etc
    fixtures = ['high_school_levels', 'post_bachelor_levels', 'student_levels',
        'immersionlyceens/apps/charts/tests/fixtures/all_test.json',
    ]

    def setUp(self):
        self.factory = RequestFactory()

        self.master_establishment = Establishment.objects.first()

        self.ref_etab_user = get_user_model().objects.get(username='test-ref-etab')
        self.ref_etab_user.establishment = self.master_establishment
        self.ref_etab_user.set_password('hiddenpassword')
        self.ref_etab_user.save()
        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)

        self.ref_master_etab_user = get_user_model().objects.get(username='test-ref-etab-maitre')
        self.ref_master_etab_user.establishment = self.master_establishment
        self.ref_master_etab_user.set_password('hiddenpassword')
        self.ref_master_etab_user.save()
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(self.ref_master_etab_user)

        self.reflyc_user = get_user_model().objects.get(username='jeanjacquesmonnet')
        self.reflyc_user.set_password('hiddenpassword')
        self.reflyc_user.save()
        Group.objects.get(name='REF-LYC').user_set.add(self.reflyc_user)

        self.client = Client()
        self.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


    def test_highschool_charts_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Highschool charts
        url = "/charts/get_highschool_charts/2"
        response = self.client.get(url)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'], [
          {
            'name': 'Registrations count',
            HighSchoolLevel.objects.get(pk=1).label: 2,
            HighSchoolLevel.objects.get(pk=2).label: 2,
            HighSchoolLevel.objects.get(pk=3).label: 0,
            HighSchoolLevel.objects.get(pk=4).label: 1
          },
          {
             'name': 'Registrations to at least one immersion',
             HighSchoolLevel.objects.get(pk=1).label: 2,
             HighSchoolLevel.objects.get(pk=2).label: 2,
             HighSchoolLevel.objects.get(pk=3).label: 0,
             HighSchoolLevel.objects.get(pk=4).label: 0
          },
          {
              'name': 'Attended to at least one immersion',
              HighSchoolLevel.objects.get(pk=1).label: 1,
              HighSchoolLevel.objects.get(pk=2).label: 1,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0
          }
        ])

    def test_highschool_domains_charts_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Highschool domain charts
        url = "/charts/get_highschool_domains_charts/2/0"
        response = self.client.get(url)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'], [
             {'domain': 'Art, Lettres, Langues',
              'count': 15,
              'subData': [
                  {'name': 'Art plastiques', 'count': 7},
                  {'name': 'Art visuels', 'count': 8}
              ]},
             {'domain': 'Droit, Economie, Gestion',
              'count': 5,
              'subData': [
                  {'name': 'Economie, Gestion', 'count': 5}
              ]},
             {'domain': 'Sciences Humaines et sociales',
              'count': 2,
              'subData': [
                  {'name': 'Sport', 'count': 2}
              ]},
             {'domain': 'Sciences et Technologies',
              'count': 11,
              'subData': [
                  {'name': 'Informatique', 'count': 4},
                  {'name': 'Mathématiques', 'count': 7}
              ]}
        ])

    def test_highschool_global_domains_charts_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')
        # Global domain charts
        url = "/charts/get_global_domains_charts"
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'domain': 'Art, Lettres, Langues', 'count': 24,
               'subData': [{'name': 'Art plastiques', 'count': 12},{'name': 'Art visuels', 'count': 12}]},
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


    def test_charts_filters_data_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Charts filter data (ajax request : use headers)
        url = "/charts/get_charts_filters_data"
        response = self.client.get(url, {}, **self.header)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
             [{'institution': 'Lycée Coufignal', 'institution_id': 3, 'type': 'Highschool', 'type_code': 0,
               'city': '68000 - COLMAR', 'department': '68', 'country': ''},
              {'institution': 'Lycée Jean Monnet', 'institution_id': 2, 'type': 'Highschool', 'type_code': 0,
               'city': '67100 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Lycée Kléber', 'institution_id': 6, 'type': 'Highschool', 'type_code': 0,
               'city': '67000 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Lycée Marie Curie', 'institution_id': 5, 'type': 'Highschool', 'type_code': 0,
               'city': '67100 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Université de Strasbourg', 'institution_id': '0673021V',
               'type': "Higher education institution", 'type_code': 1, 'city': ['67081 - Strasbourg'],
               'department': ['Bas-Rhin'], 'country': ['France']}]
        )


    def test_highschool_trainings_charts_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Training charts (ajax request : use headers)
        url = "/charts/get_highschool_trainings_charts"
        response = self.client.get(url, {'empty_trainings': 'true'}, **self.header)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
            [{'training_label': 'DUT Informatique',
              'domain_label': 'Sciences et Technologies<br>- Informatique',
              'unique_students': 5,
              'all_registrations': 5,
              'unique_students_lvl1': 2,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 2,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1,
              'registrations_lvl4': 0},
             {'training_label': 'Licence Arts Plastiques & Design',
              'domain_label': 'Art, Lettres, Langues<br>- Art plastiques',
              'unique_students': 7,
              'all_registrations': 12,
              'unique_students_lvl1': 3,
              'unique_students_lvl2': 3,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 6,
              'registrations_lvl2': 4,
              'registrations_lvl3': 2,
              'registrations_lvl4': 0},
             {'training_label': 'Licence Arts du Spectacle',
              'domain_label': 'Art, Lettres, Langues<br>- Art visuels',
              'unique_students': 7,
              'all_registrations': 12,
              'unique_students_lvl1': 3,
              'unique_students_lvl2': 3,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 6,
              'registrations_lvl2': 5,
              'registrations_lvl3': 1,
              'registrations_lvl4': 0},
             {'training_label': 'Licence Informatique',
              'domain_label': 'Sciences et Technologies<br>- Informatique',
              'unique_students': 5,
              'all_registrations': 5,
              'unique_students_lvl1': 2,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 2,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1,
              'registrations_lvl4': 0},
             {'training_label': 'Licence Maths-Eco',
              'domain_label': 'Droit, Economie, Gestion<br>- Economie, Gestion<br>Sciences et Technologies<br>- Mathématiques',
              'unique_students': 3,
              'all_registrations': 5,
              'unique_students_lvl1': 1,
              'registrations_lvl1': 2,
              'unique_students_lvl2': 2,
              'registrations_lvl2': 3,
              'unique_students_lvl3': 0,
              'registrations_lvl3': 0,
              'unique_students_lvl4': 0,
              'registrations_lvl4': 0},
             {'training_label': 'Licence Mathématiques',
              'domain_label': 'Sciences et Technologies<br>- Mathématiques',
              'unique_students': 3,
              'all_registrations': 4,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 1,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 1,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1,
              'registrations_lvl4': 0},
             {'training_label': 'Licence STAPS',
              'domain_label': 'Sciences Humaines et sociales<br>- Sport',
              'unique_students': 3,
              'all_registrations': 3,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 1,
              'unique_students_lvl3': 1,
              'unique_students_lvl4': 0,
              'registrations_lvl1': 1,
              'registrations_lvl2': 1,
              'registrations_lvl3': 1,
              'registrations_lvl4': 0}]
        )
        # with an highschool id as a paramater
        response = self.client.get(
            reverse('charts:get_highschool_trainings_charts'),
            {
                'highschool_id': 2,
                'empty_trainings': 'true'
            },
            **self.header
        )
        content = response.content.decode()
        json_content = json.loads(content)

        data = [{'training_label': 'DUT Informatique',
                 'all_registrations': 2,
                 'domain_label': 'Sciences et Technologies<br>- Informatique',
                 'registrations_lvl1': 1,
                 'registrations_lvl2': 1,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 2,
                 'unique_students_lvl1': 1,
                 'unique_students_lvl2': 1,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence Arts Plastiques & Design',
                 'all_registrations': 7,
                 'domain_label': 'Art, Lettres, Langues<br>- Art plastiques',
                 'registrations_lvl1': 4,
                 'registrations_lvl2': 3,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 4,
                 'unique_students_lvl1': 2,
                 'unique_students_lvl2': 2,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence Arts du Spectacle',
                 'all_registrations': 8,
                 'domain_label': 'Art, Lettres, Langues<br>- Art visuels',
                 'registrations_lvl1': 4,
                 'registrations_lvl2': 4,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 4,
                 'unique_students_lvl1': 2,
                 'unique_students_lvl2': 2,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence Informatique',
                 'all_registrations': 2,
                 'domain_label': 'Sciences et Technologies<br>- Informatique',
                 'registrations_lvl1': 1,
                 'registrations_lvl2': 1,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 2,
                 'unique_students_lvl1': 1,
                 'unique_students_lvl2': 1,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence Maths-Eco',
                 'all_registrations': 5,
                 'domain_label': 'Droit, Economie, Gestion<br>- Economie, Gestion<br>Sciences et Technologies<br>- Mathématiques',
                 'registrations_lvl1': 2,
                 'registrations_lvl2': 3,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 3,
                 'unique_students_lvl1': 1,
                 'unique_students_lvl2': 2,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence Mathématiques',
                 'all_registrations': 2,
                 'domain_label': 'Sciences et Technologies<br>- Mathématiques',
                 'registrations_lvl1': 0,
                 'registrations_lvl2': 2,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 1,
                 'unique_students_lvl1': 0,
                 'unique_students_lvl2': 1,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0},
                {'training_label': 'Licence STAPS',
                 'all_registrations': 2,
                 'domain_label': 'Sciences Humaines et sociales<br>- Sport',
                 'registrations_lvl1': 1,
                 'registrations_lvl2': 1,
                 'registrations_lvl3': 0,
                 'registrations_lvl4': 0,
                 'unique_students': 2,
                 'unique_students_lvl1': 1,
                 'unique_students_lvl2': 1,
                 'unique_students_lvl3': 0,
                 'unique_students_lvl4': 0}]

        self.assertEqual(json_content['data'], data)

        # logged as ref-lyc : highschool id not needed
        # Result data should be the same
        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')
        url = "/charts/get_highschool_trainings_charts"
        response = self.client.get(url, {'empty_trainings': 'true'}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)
        self.assertEqual(json_content['data'], data)


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

    def test_registration_charts_charts_api(self):
        # Registration charts
        self.client.login(username='test-ref-etab', password='hiddenpassword')
        url = "/charts/get_registration_charts"

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
              },
              {'name': 'Registrations to at least one immersion',
               HighSchoolLevel.objects.get(pk=1).label: 3,
               HighSchoolLevel.objects.get(pk=2).label: 4,
               HighSchoolLevel.objects.get(pk=3).label: 1,
               HighSchoolLevel.objects.get(pk=4).label: 1,
               'Visitors': 0,
              },
              {'name': 'Registrations count',
               HighSchoolLevel.objects.get(pk=1).label: 4,
               HighSchoolLevel.objects.get(pk=2).label: 4,
               HighSchoolLevel.objects.get(pk=3).label: 2,
               HighSchoolLevel.objects.get(pk=4).label: 2,
               'Visitors': 0,
              },]
        )

        # With another level
        url = "/charts/get_registration_charts"
        response = self.client.get(url, {'level': 1})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'], [{
            'name': 'Attended to at least one immersion',
            HighSchoolLevel.objects.get(pk=1).label: 2
        }, {
            'name': 'Registrations to at least one immersion',
            HighSchoolLevel.objects.get(pk=1).label: 3
        }, {
            'name': 'Registrations count',
            HighSchoolLevel.objects.get(pk=1).label: 4}
        ])

        # As a school manager : median will be displayed
        self.client.login(username='jeanjacquesmonnet', password='hiddenpassword')
        url = "/charts/get_registration_charts"

        # The highschool_id parameter is not needed (default = the manager highschool)
        response = self.client.get(url, {'level': 0})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'name': 'Attended to at least one immersion (m = 1.0)',
              HighSchoolLevel.objects.get(pk=1).label: 1,
              HighSchoolLevel.objects.get(pk=2).label: 1,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0},
             {'name': 'Registrations to at least one immersion (m = 1)',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0},
             {'name': 'Registrations count (m = 1.0)',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1}]
        )


    def test_registration_charts_cats_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Registration charts cats (ajax query, headers needed)
        url = "/charts/get_registration_charts_cats"
        response = self.client.post(url,
            {'highschools_ids[]': [2], 'higher_institutions_ids[]': ['0673021V']}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 1,
              HighSchoolLevel.objects.get(pk=2).label: 1,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0},
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=1).label: 0,
              HighSchoolLevel.objects.get(pk=2).label: 0,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0}]
        )

        self.assertEqual(json_content['one_immersion']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 0},
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=1).label: 0,
              HighSchoolLevel.objects.get(pk=2).label: 0,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1}]
        )

        self.assertEqual(json_content['platform_regs']['datasets'],
            [{'name': 'Lycée Jean Monnet',
              HighSchoolLevel.objects.get(pk=1).label: 2,
              HighSchoolLevel.objects.get(pk=2).label: 2,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1},
             {'name': 'Université de Strasbourg',
              HighSchoolLevel.objects.get(pk=1).label: 0,
              HighSchoolLevel.objects.get(pk=2).label: 0,
              HighSchoolLevel.objects.get(pk=3).label: 0,
              HighSchoolLevel.objects.get(pk=4).label: 1}]
        )

        response = self.client.post(url, {'highschools_ids[]': [2], 'level': 1}, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'],
            [{HighSchoolLevel.objects.get(pk=1).label: 1, 'name': 'Lycée Jean Monnet'}]
        )

        self.assertEqual(json_content['one_immersion']['datasets'],
            [{HighSchoolLevel.objects.get(pk=1).label: 2, 'name': 'Lycée Jean Monnet'}]
        )

        self.assertEqual(json_content['platform_regs']['datasets'],
            [{HighSchoolLevel.objects.get(pk=1).label: 2, 'name': 'Lycée Jean Monnet'}]
        )

    def test_slots_charts_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Slots charts (ajax query, headers needed)
        url = "/charts/get_slots_charts"
        response = self.client.get(url, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content["datasets"],
            [{'structure': 'Faculté des Arts',
              'slots_count': 21,
              'subData': [{'name': 'Licence Arts Plastiques & '
                                   'Design',
                           'slots_count': 13},
                          {'name': 'Licence Arts du Spectacle',
                           'slots_count': 8}]},
             {'structure': 'Faculté des Sciences économiques et de '
                           'gestion',
              'slots_count': 9,
              'subData': [{'name': 'Licence Maths-Eco',
                           'slots_count': 9}]},
             {'structure': 'Faculté des sciences du sport',
              'slots_count': 5,
              'subData': [{'name': 'Licence STAPS',
                           'slots_count': 5}]},
             {'structure': 'IUT Louis Pasteur',
              'slots_count': 1,
              'subData': [{'name': 'DUT Informatique',
                           'slots_count': 1}]},
             {'structure': 'UFR Mathématiques et Informatique',
              'slots_count': 17,
              'subData': [{'name': 'Licence Informatique',
                           'slots_count': 6},
                          {'name': 'Licence Maths-Eco',
                           'slots_count': 4},
                          {'name': 'Licence Mathématiques',
                           'slots_count': 7}]},
             ]
        )

    def test_slots_data_api(self):
        self.client.login(username='test-ref-etab', password='hiddenpassword')

        # Slots data
        url = "/charts/get_slots_data"
        response = self.client.get(url, **self.header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
             [{'available_seats': 15,
               'structure': 'Faculté des Arts',
               'course': 'Arts du spectacle',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 15,
               'structure': 'Faculté des Arts',
               'course': 'Arts plastiques',
               'slots_count': 3,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 29,
               'structure': 'Faculté des Arts',
               'course': 'Arts plastiques 2',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 15,
               'structure': 'Faculté des Arts',
               'course': 'Design théorie',
               'slots_count': 3,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 0,
               'structure': 'Faculté des Arts',
               'course': 'Histoire des arts',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 4,
               'structure': 'Faculté des Arts',
               'course': 'cours test 1',
               'slots_count': 1,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 10,
               'structure': 'Faculté des Arts',
               'course': 'Théatre',
               'slots_count': 3,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 14,
               'structure': 'Faculté des Arts',
               'course': 'Théatre 2',
               'slots_count': 3,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 16,
               'structure': 'Faculté des Arts',
               'course': 'Théatre débutant',
               'slots_count': 2,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 8,
               'structure': 'Faculté des Sciences économiques et de '
                            'gestion',
               'course': 'Economie 2',
               'slots_count': 1,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 43,
               'structure': 'Faculté des Sciences économiques et de '
                            'gestion',
               'course': 'Economie 3',
               'slots_count': 7,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 6,
               'structure': 'Faculté des sciences du sport',
               'course': 'Ergonomie du mouvement',
               'slots_count': 2,
               'training': 'Licence STAPS'},
              {'available_seats': 20,
               'structure': 'Faculté des sciences du sport',
               'course': 'Pratiques sportives',
               'slots_count': 3,
               'training': 'Licence STAPS'},
              {'available_seats': 8,
               'structure': 'IUT Louis Pasteur',
               'course': 'Developpement Web',
               'slots_count': 1,
               'training': 'DUT Informatique'},
              {'available_seats': 15,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique',
               'slots_count': 3,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique 3',
               'slots_count': 0,
               'training': 'Licence Informatique'},
              {'available_seats': 19,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Algèbre 1',
               'slots_count': 3,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Anglais pour informatique',
               'slots_count': 0,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Algo_prog',
               'slots_count': 0,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 19,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Analyse S1',
               'slots_count': 1,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 15,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Organisation',
               'slots_count': 3,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 47,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique',
               'slots_count': 3,
               'training': 'Licence Mathématiques'},
              {'available_seats': 40,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Analyse 2',
               'slots_count': 3,
               'training': 'Licence Mathématiques'},
              {'available_seats': 10,
               'structure': 'UFR Mathématiques et Informatique',
               'course': 'Analyse S1',
               'slots_count': 1,
               'training': 'Licence Mathématiques'}]
        )

        # Slots data, csv format
        url = "/charts/get_slots_data/csv"
        response = self.client.get(url, **self.header)
        content = response.content.decode()
        self.assertIn("UFR Mathématiques et Informatique,Licence Mathématiques,Analyse S1,1,10", content)

