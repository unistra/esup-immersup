"""
Mails tests
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase

from immersionlyceens.apps.core.models import UniversityYear

from ..mails.variables_parser import parser

class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group', 'generalsettings']

    def setUp(self):
        self.highschool_user = get_user_model().objects.create_user(
            username='hs', password='pass', email='hs@no-reply.com', first_name='Jean', last_name='MICHEL',
        )

        self.teacher1 = get_user_model().objects.create_user(
            username='teacher1',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='teach',
            last_name='HER',
        )

        self.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            active=True,
        )

    def test_macros(self):
        test_body = "line 1" +\
            "\n<br>${nom}" +\
            "\n<br>${prenom}" +\
            "\n<br>Another line"

        body = parser(test_body, user=self.highschool_user)

        self.assertIn(self.highschool_user.first_name, body)
        self.assertIn(self.highschool_user.last_name, body)