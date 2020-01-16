from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import BachelorMention, Building, Campus, HighSchool


class CampusTestCase(TestCase):

    def test_campus_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(str(test_campus), 'MyCampus')

    def test_campus_creation_activated(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(test_campus.active, True)

    def test_building_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        test_building = Building.objects.create(
            label='MyBuilding', campus=test_campus)
        self.assertEqual(str(test_building), 'MyBuilding')


class BachelorMentionTestCase(TestCase):

    def test_bachelor_mention_str(self):
        label = "Techo parade"
        o = BachelorMention.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_bachelor_mention_activated(self):
        o = BachelorMention.objects.create(label="Techo parade")
        self.assertTrue(o.active)


class HighSchoolTestCase(TestCase):

    def test_highschool_str(self):

        data = {
            'label': 'Degrassi Junior School',
            'address': 'rue Joey Jeremiah',
            'address2': '',
            'address3': '',
            'department': '68',
            'city': 'MULHOUSE',
            'zip_code': '68100',
            'phone_number': '+3312345678',
            'fax': '+3397654321',
            'email': 'degrassi@degrassi.edu',
            'head_teacher_name': 'M. Daniel Raditch',
            'referent_name': 'Spike Nelson',
            'referent_phone_number': '+30102030',
            'referent_email': 'spike@caramail.com',
            'convention_start_date': '1977-05-30'
        }

        test_highschool = HighSchool.objects.create(**data)
        self.assertEqual(str(test_highschool), 'Degrassi Junior School')
