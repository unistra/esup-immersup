"""
Charts API tests
"""
import datetime
import pprint
import json

from django.contrib.auth import get_user_model
from django.utils.formats import date_format
from django.test import Client, RequestFactory, TestCase
from django.conf import settings
from django.contrib.auth.models import Group

from .. import api

class ChartsTestCase(TestCase):
    """Tests for API"""

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


    def test_charts_api(self):
        self.client.login(username='test-scuio-ip', password='hiddenpassword')
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        # Highschool charts
        url = "/charts/get_highschool_charts/2"
        response = self.client.get(url)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'name': 'Inscrits sur la plateforme', 'Première': 3, 'Terminale': 2, 'Post-bac': 0},
             {'name': 'Inscrits à au moins une immersion', 'Première': 2, 'Terminale': 2, 'Post-bac': 0},
             {'name': 'Participation à au moins une immersion', 'Première': 1, 'Terminale': 1, 'Post-bac': 0}]
        )

        # Highschool domain charts
        url = "/charts/get_highschool_domains_charts/2/0"
        response = self.client.get(url)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'domain': 'Art, Lettres, Langues', 'count': 15,
              'subData': [{'name': 'Art visuels', 'count': 8}, {'name': 'Art plastiques', 'count': 7}]},
             {'domain': 'Droit, Economie, Gestion', 'count': 5, 'subData': [{'name': 'Economie, Gestion', 'count': 5}]},
             {'domain': 'Santé', 'count': 0, 'subData': []},
             {'domain': 'Sciences Humaines et sociales', 'count': 2,
              'subData': [{'name': 'Histoire et Géo', 'count': 0}, {'name': 'Sport', 'count': 2}]},
             {'domain': 'Sciences et Technologies', 'count': 11,
              'subData': [{'name': 'Mathématiques', 'count': 7}, {'name': 'Psychologie', 'count': 0},
                          {'name': 'Informatique', 'count': 4}]},
             {'domain': 'Test', 'count': 0, 'subData': [{'name': 'Test sous domaine', 'count': 0}]}]
        )

        # Global domain charts
        url = "/charts/get_global_domains_charts"
        response = self.client.post(url, {})
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'domain': 'Art, Lettres, Langues', 'count': 24,
               'subData': [{'name': 'Art visuels', 'count': 12}, {'name': 'Art plastiques', 'count': 12}]},
              {'domain': 'Droit, Economie, Gestion', 'count': 6,
               'subData': [{'name': 'Economie, Gestion', 'count': 6}]},
              {'domain': 'Santé', 'count': 0, 'subData': []},
              {'domain': 'Sciences Humaines et sociales', 'count': 3,
               'subData': [{'name': 'Histoire et Géo', 'count': 0}, {'name': 'Sport', 'count': 3}]},
              {'domain': 'Sciences et Technologies', 'count': 20,
               'subData': [{'name': 'Mathématiques', 'count': 10}, {'name': 'Psychologie', 'count': 0},
                           {'name': 'Informatique', 'count': 10}]},
              {'domain': 'Test', 'count': 0, 'subData': [{'name': 'Test sous domaine', 'count': 0}]}]
        )

        # Test with filter
        response = self.client.post(url,
            {'highschools_ids[]': [2]}
        )

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'domain': 'Art, Lettres, Langues', 'count': 15,
               'subData': [{'name': 'Art visuels', 'count': 8}, {'name': 'Art plastiques', 'count': 7}]},
              {'domain': 'Droit, Economie, Gestion', 'count': 5,
               'subData': [{'name': 'Economie, Gestion', 'count': 5}]},
              {'domain': 'Santé', 'count': 0, 'subData': []},
              {'domain': 'Sciences Humaines et sociales', 'count': 2,
               'subData': [{'name': 'Histoire et Géo', 'count': 0}, {'name': 'Sport', 'count': 2}]},
              {'domain': 'Sciences et Technologies', 'count': 11,
               'subData': [{'name': 'Mathématiques', 'count': 7}, {'name': 'Psychologie', 'count': 0},
                           {'name': 'Informatique', 'count': 4}]},
              {'domain': 'Test', 'count': 0, 'subData': [{'name': 'Test sous domaine', 'count': 0}]}]
        )

        # Charts filter data (ajax request : use headers)
        url = "/charts/get_charts_filters_data"
        response = self.client.get(url, {}, **header)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
             [{'institution': 'Lycée Coufignal', 'institution_id': 3, 'type': 'Lycée', 'type_code': 0,
               'city': '68000 - COLMAR', 'department': '68', 'country': ''},
              {'institution': 'Lycée Jean Monnet', 'institution_id': 2, 'type': 'Lycée', 'type_code': 0,
               'city': '67100 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Lycée Kléber', 'institution_id': 6, 'type': 'Lycée', 'type_code': 0,
               'city': '67000 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Lycée Marie Curie', 'institution_id': 5, 'type': 'Lycée', 'type_code': 0,
               'city': '67100 - STRASBOURG', 'department': '67', 'country': ''},
              {'institution': 'Université de Strasbourg', 'institution_id': '0673021V',
               'type': "Etablissement d'Etudes Supérieures", 'type_code': 1, 'city': ['67081 - Strasbourg'],
               'department': ['Bas-Rhin'], 'country': ['France']}]
        )

        # Training charts (ajax request : use headers)
        # logged as scuio-ip
        url = "/charts/get_trainings_charts"
        response = self.client.get(url, {}, **header)

        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
            [{'training_label': 'Licence Mathématiques',
              'subdomain_label': 'Mathématiques',
              'domain_label': 'Sciences et Technologies',
              'unique_students': 3,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 1,
              'unique_students_lvl3': 1,
              'all_registrations': 4,
              'registrations_lvl1': 1,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1},
             {'training_label': 'Licence Informatique',
              'subdomain_label': 'Informatique',
              'domain_label': 'Sciences et Technologies',
              'unique_students': 5, 'unique_students_lvl1': 2,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'all_registrations': 5,
              'registrations_lvl1': 2,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1},
             {'training_label': 'DUT Informatique',
              'subdomain_label': 'Informatique',
              'domain_label': 'Sciences et Technologies',
              'unique_students': 5, 'unique_students_lvl1': 2,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'all_registrations': 5,
              'registrations_lvl1': 2,
              'registrations_lvl2': 2,
              'registrations_lvl3': 1},
             {'training_label': 'Licence Maths-Eco',
              'subdomain_label': 'Mathématiques',
              'domain_label': 'Sciences et Technologies',
              'unique_students': 4,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'all_registrations': 6,
              'registrations_lvl1': 2,
              'registrations_lvl2': 3,
              'registrations_lvl3': 1},
             {'training_label': 'Licence Maths-Eco',
              'subdomain_label': 'Economie, Gestion',
              'domain_label': 'Droit, Economie, Gestion',
              'unique_students': 4,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 2,
              'unique_students_lvl3': 1,
              'all_registrations': 6,
              'registrations_lvl1': 2,
              'registrations_lvl2': 3,
              'registrations_lvl3': 1},
             {'training_label': 'Licence Arts Plastiques & Design',
              'subdomain_label': 'Art plastiques',
              'domain_label': 'Art, Lettres, Langues',
              'unique_students': 7,
              'unique_students_lvl1': 3,
              'unique_students_lvl2': 3,
              'unique_students_lvl3': 1,
              'all_registrations': 12,
              'registrations_lvl1': 6,
              'registrations_lvl2': 4,
              'registrations_lvl3': 2},
             {'training_label': 'Licence Arts du Spectacle',
              'subdomain_label': 'Art visuels',
              'domain_label': 'Art, Lettres, Langues',
              'unique_students': 7,
              'unique_students_lvl1': 3,
              'unique_students_lvl2': 3,
              'unique_students_lvl3': 1,
              'all_registrations': 12,
              'registrations_lvl1': 6,
              'registrations_lvl2': 5,
              'registrations_lvl3': 1},
             {'training_label': 'Licence STAPS',
              'subdomain_label': 'Sport',
              'domain_label': 'Sciences Humaines et sociales',
              'unique_students': 3,
              'unique_students_lvl1': 1,
              'unique_students_lvl2': 1,
              'unique_students_lvl3': 1,
              'all_registrations': 3,
              'registrations_lvl1': 1,
              'registrations_lvl2': 1,
              'registrations_lvl3': 1}]
        )
        # with an highschool id as a paramater
        url = "/charts/get_trainings_charts/2"
        response = self.client.get(url, {}, **header)

        content = response.content.decode()
        json_content = json.loads(content)

        data = [{'all_registrations': 2,
                  'domain_label': 'Sciences et Technologies',
                  'registrations_lvl1': 0,
                  'registrations_lvl2': 2,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Mathématiques',
                  'training_label': 'Licence Mathématiques',
                  'unique_students': 1,
                  'unique_students_lvl1': 0,
                  'unique_students_lvl2': 1,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 2,
                  'domain_label': 'Sciences et Technologies',
                  'registrations_lvl1': 1,
                  'registrations_lvl2': 1,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Informatique',
                  'training_label': 'Licence Informatique',
                  'unique_students': 2,
                  'unique_students_lvl1': 1,
                  'unique_students_lvl2': 1,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 2,
                  'domain_label': 'Sciences et Technologies',
                  'registrations_lvl1': 1,
                  'registrations_lvl2': 1,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Informatique',
                  'training_label': 'DUT Informatique',
                  'unique_students': 2,
                  'unique_students_lvl1': 1,
                  'unique_students_lvl2': 1,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 5,
                  'domain_label': 'Sciences et Technologies',
                  'registrations_lvl1': 2,
                  'registrations_lvl2': 3,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Mathématiques',
                  'training_label': 'Licence Maths-Eco',
                  'unique_students': 3,
                  'unique_students_lvl1': 1,
                  'unique_students_lvl2': 2,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 5,
                  'domain_label': 'Droit, Economie, Gestion',
                  'registrations_lvl1': 2,
                  'registrations_lvl2': 3,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Economie, Gestion',
                  'training_label': 'Licence Maths-Eco',
                  'unique_students': 3,
                  'unique_students_lvl1': 1,
                  'unique_students_lvl2': 2,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 7,
                  'domain_label': 'Art, Lettres, Langues',
                  'registrations_lvl1': 4,
                  'registrations_lvl2': 3,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Art plastiques',
                  'training_label': 'Licence Arts Plastiques & Design',
                  'unique_students': 4,
                  'unique_students_lvl1': 2,
                  'unique_students_lvl2': 2,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 8,
                  'domain_label': 'Art, Lettres, Langues',
                  'registrations_lvl1': 4,
                  'registrations_lvl2': 4,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Art visuels',
                  'training_label': 'Licence Arts du Spectacle',
                  'unique_students': 4,
                  'unique_students_lvl1': 2,
                  'unique_students_lvl2': 2,
                  'unique_students_lvl3': 0},
                 {'all_registrations': 2,
                  'domain_label': 'Sciences Humaines et sociales',
                  'registrations_lvl1': 1,
                  'registrations_lvl2': 1,
                  'registrations_lvl3': 0,
                  'subdomain_label': 'Sport',
                  'training_label': 'Licence STAPS',
                  'unique_students': 2,
                  'unique_students_lvl1': 1,
                  'unique_students_lvl2': 1,
                  'unique_students_lvl3': 0}]

        self.assertEqual(json_content['data'], data)

        # logged as ref-lyc : highschool id not needed
        # Result data should be the same
        self.client.login(username='jeanmonnet', password='hiddenpassword')
        url = "/charts/get_trainings_charts"
        response = self.client.get(url, {}, **header)
        content = response.content.decode()
        json_content = json.loads(content)
        self.assertEqual(json_content['data'], data)

        # Registration charts
        self.client.login(username='test-scuio-ip', password='hiddenpassword')
        url = "/charts/get_registration_charts/0"

        response = self.client.get(url)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
             [{'name': 'Inscrits sur la plateforme', 'Première': 5, 'Terminale': 4, 'Post-bac': 3},
              {'name': 'Inscrits à au moins une immersion', 'Première': 3, 'Terminale': 4, 'Post-bac': 2},
              {'name': 'Participation à au moins une immersion', 'Première': 2, 'Terminale': 2, 'Post-bac': 0}]
        )

        # With another level
        url = "/charts/get_registration_charts/1"
        response = self.client.get(url)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['datasets'],
            [{'name': 'Inscrits sur la plateforme', 'Première': 5},
             {'name': 'Inscrits à au moins une immersion', 'Première': 3},
             {'name': 'Participation à au moins une immersion', 'Première': 2}]
        )

        # Registration charts cats (ajax query, headers needed)
        url = "/charts/get_registration_charts_cats"
        response = self.client.post(url,
            {'highschools_ids[]': [2], 'higher_institutions_ids[]': ['0673021V']}, **header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'],
            [{'name': 'Lycée Jean Monnet', 'Première': 1, 'Terminale': 1, 'Post-bac': 0},
             {'name': 'Université de Strasbourg', 'Première': 0, 'Terminale': 0, 'Post-bac': 0}]
        )

        self.assertEqual(json_content['one_immersion']['datasets'],
            [{'name': 'Lycée Jean Monnet', 'Première': 2, 'Terminale': 2, 'Post-bac': 0},
             {'name': 'Université de Strasbourg', 'Première': 0, 'Terminale': 0, 'Post-bac': 1}]
        )

        self.assertEqual(json_content['platform_regs']['datasets'],
            [{'name': 'Lycée Jean Monnet', 'Première': 3, 'Terminale': 2, 'Post-bac': 0},
             {'name': 'Université de Strasbourg', 'Première': 0, 'Terminale': 0, 'Post-bac': 1}]
        )

        url = "/charts/get_registration_charts_cats"
        response = self.client.post(url, {'highschools_ids[]': [2], 'level': 1}, **header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['attended_one']['datasets'],
            [{'Première': 1, 'name': 'Lycée Jean Monnet'}]
        )

        self.assertEqual(json_content['one_immersion']['datasets'],
            [{'Première': 2, 'name': 'Lycée Jean Monnet'}]
        )

        self.assertEqual(json_content['platform_regs']['datasets'],
            [{'Première': 3, 'name': 'Lycée Jean Monnet'}]
        )

        # Slots charts (ajax query, headers needed)
        url = "/charts/get_slots_charts"
        response = self.client.get(url, **header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content["datasets"],
            [{'component': 'Faculté des Arts',
              'slots_count': 21,
              'subData': [{'name': 'Licence Arts Plastiques & '
                                   'Design',
                           'slots_count': 13},
                          {'name': 'Licence Arts du Spectacle',
                           'slots_count': 8}]},
             {'component': 'UFR Mathématiques et Informatique',
              'slots_count': 17,
              'subData': [{'name': 'Licence Informatique',
                           'slots_count': 6},
                          {'name': 'Licence Mathématiques',
                           'slots_count': 7},
                          {'name': 'Licence Maths-Eco',
                           'slots_count': 4}]},
             {'component': 'Faculté des sciences du sport',
              'slots_count': 5,
              'subData': [{'name': 'Licence STAPS',
                           'slots_count': 5}]},
             {'component': 'Faculté des Sciences économiques et de '
                           'gestion',
              'slots_count': 9,
              'subData': [{'name': 'Licence Maths-Eco',
                           'slots_count': 9}]},
             {'component': 'IUT Louis Pasteur',
              'slots_count': 1,
              'subData': [{'name': 'DUT Informatique',
                           'slots_count': 1}]}]
        )

        # Slots data
        url = "/charts/get_slots_data"
        response = self.client.get(url, **header)
        content = response.content.decode()
        json_content = json.loads(content)

        self.assertEqual(json_content['data'],
             [{'available_seats': 15,
               'component': 'Faculté des Arts',
               'course': 'Arts du spectacle',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 15,
               'component': 'Faculté des Arts',
               'course': 'Arts plastiques',
               'slots_count': 3,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 29,
               'component': 'Faculté des Arts',
               'course': 'Arts plastiques 2',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 15,
               'component': 'Faculté des Arts',
               'course': 'Design théorie',
               'slots_count': 3,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 0,
               'component': 'Faculté des Arts',
               'course': 'Histoire des arts',
               'slots_count': 2,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 4,
               'component': 'Faculté des Arts',
               'course': 'cours test 1',
               'slots_count': 1,
               'training': 'Licence Arts Plastiques & Design'},
              {'available_seats': 10,
               'component': 'Faculté des Arts',
               'course': 'Théatre',
               'slots_count': 3,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 14,
               'component': 'Faculté des Arts',
               'course': 'Théatre 2',
               'slots_count': 3,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 16,
               'component': 'Faculté des Arts',
               'course': 'Théatre débutant',
               'slots_count': 2,
               'training': 'Licence Arts du Spectacle'},
              {'available_seats': 8,
               'component': 'Faculté des Sciences économiques et de '
                            'gestion',
               'course': 'Economie 2',
               'slots_count': 1,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 43,
               'component': 'Faculté des Sciences économiques et de '
                            'gestion',
               'course': 'Economie 3',
               'slots_count': 7,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 6,
               'component': 'Faculté des sciences du sport',
               'course': 'Ergonomie du mouvement',
               'slots_count': 2,
               'training': 'Licence STAPS'},
              {'available_seats': 20,
               'component': 'Faculté des sciences du sport',
               'course': 'Pratiques sportives',
               'slots_count': 3,
               'training': 'Licence STAPS'},
              {'available_seats': 8,
               'component': 'IUT Louis Pasteur',
               'course': 'Developpement Web',
               'slots_count': 1,
               'training': 'DUT Informatique'},
              {'available_seats': 15,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique',
               'slots_count': 3,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique 3',
               'slots_count': 0,
               'training': 'Licence Informatique'},
              {'available_seats': 19,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Algèbre 1',
               'slots_count': 3,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Anglais pour informatique',
               'slots_count': 0,
               'training': 'Licence Informatique'},
              {'available_seats': 0,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Algo_prog',
               'slots_count': 0,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 19,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Analyse S1',
               'slots_count': 1,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 15,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Organisation',
               'slots_count': 3,
               'training': 'Licence Maths-Eco'},
              {'available_seats': 47,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Algorithmique',
               'slots_count': 3,
               'training': 'Licence Mathématiques'},
              {'available_seats': 40,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Analyse 2',
               'slots_count': 3,
               'training': 'Licence Mathématiques'},
              {'available_seats': 10,
               'component': 'UFR Mathématiques et Informatique',
               'course': 'Analyse S1',
               'slots_count': 1,
               'training': 'Licence Mathématiques'}]
        )

        # Slots data, csv format
        url = "/charts/get_slots_data/csv"
        response = self.client.get(url, **header)
        content = response.content.decode()
        self.assertIn("UFR Mathématiques et Informatique,Licence Mathématiques,Analyse S1,1,10", content)
