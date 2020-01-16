"""
Django Admin Forms tests suite
"""
import datetime

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from ..admin import (BuildingAdmin, CampusAdmin, CourseDomainAdmin,
                     HighSchoolAdmin)
from ..admin_forms import (BuildingForm, CampusForm, CourseDomainForm,
                           HighSchoolForm)
from ..models import Building, Campus, CourseDomain, HighSchool


class MockRequest:
    pass

# request = MockRequest()


request_factory = RequestFactory()
request = request_factory.get('/admin')


class AdminFormsTestCase(TestCase):
    """
    Main admin forms tests class
    """
    fixtures = ['group']

    def setUp(self):
        """
        SetUp for Admin Forms tests
        """

        self.site = AdminSite()
        self.superuser = get_user_model().objects.create_superuser(
            username='super', password='pass', email='immersion@no-reply.com')

        self.scuio_user = get_user_model().objects.create_user(
            username='cmp', password='pass', email='immersion@no-reply.com',
            first_name='cmp', last_name='cmp')

        self.ref_cmp_user = get_user_model().objects.create_user(
            username='ref_cmp', password='pass', email='immersion@no-reply.com',
            first_name='ref_cmp', last_name='ref_cmp')

        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_cmp_user)

    def test_course_domain_creation(self):
        """
        Test admin CourseDomain creation with group rights
        """
        data = {'label': 'test', 'active': True}

        request.user = self.scuio_user

        form = CourseDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseDomain.objects.filter(label='test').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = CourseDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CourseDomain.objects.filter(
            label='test_fail').exists())

    def test_campus_creation(self):
        """
        Test admin Campus creation with group rights
        """

        data = {'label': 'testCampus', 'active': True}

        request.user = self.scuio_user

        form = CampusForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Campus.objects.filter(label='testCampus').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = CampusForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Campus.objects.filter(
            label='test_fail').exists())

    def test_building_creation(self):
        """
        Test admin Campus creation with group rights
        """

        testCampus = Campus.objects.create(label='testCampus', active=True)
        data = {'label': 'testBuilding', 'campus': testCampus.pk,
                'url': 'https://www.building.com', 'active': True}

        request.user = self.scuio_user

        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label='testBuilding').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = BuildingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Building.objects.filter(
            label='test_fail').exists())

    def test_highschool_creation(self):
        """
        Test admin HighSchool creation with group rights
        """

        data = {
            'label': ' Santo Domingo',
            'address': 'rue larry Kubiac',
            'address2': '',
            'address3': '',
            'department': '68',
            'city': 'MULHOUSE',
            'zip_code': '68100',
            'phone_number': '+3312345678',
            'fax': '+3397654321',
            'email': 'santodomingo@santodomingo.edu',
            'head_teacher_name': 'Madame Musso Grace',
            'referent_name': 'Franck Lemmer',
            'referent_phone_number': '+30102030',
            'referent_email': 'franck.lemmer@caramail.com',
            'convention_start_date': datetime.datetime.today().date(),
            'convention_end_date': ''
        }

        request.user = self.scuio_user

        form = HighSchoolForm(data=data, request=request)
        # Need to populate choices fields (ajax populated IRL)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(HighSchool.objects.filter(
            label='Santo Domingo').exists())

        # Validation fail (invalid user)
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
            'convention_start_date': datetime.datetime.today().date(),
            'convention_end_date': ''
        }
        request.user = self.ref_cmp_user
        form = HighSchoolForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(HighSchool.objects.filter(
            label='Degrassi Junior School').exists())
