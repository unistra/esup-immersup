"""
Django Admin Forms tests suite
"""

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from ..models import (
    Building, Campus, Component, TrainingDomain,
    TrainingSubdomain,
    BachelorMention, CancelType, CourseType, PublicType)

from ..admin_forms import (
    BuildingForm, CampusForm, ComponentForm,
    TrainingDomainForm, TrainingSubdomainForm,
    BachelorMentionForm, CancelTypeForm, CourseTypeForm, PublicTypeForm)


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


    def test_training_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        data = { 'label': 'test', 'active': True }

        request.user = self.scuio_user

        form = TrainingDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

        # Validation fail (invalid user)        
        data = { 'label': 'test_fail', 'active': True }
        request.user = self.ref_cmp_user
        form = TrainingDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(TrainingDomain.objects.filter(label='test_fail').exists())


    def test_training_sub_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        domain_data = { 'label': 'test', 'active': True }
        td = TrainingDomain.objects.create(**domain_data)

        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

        data = { 'label': 'sd test', 'training_domain':td.pk, 'active': True }

        request.user = self.scuio_user

        form = TrainingSubdomainForm(data=data, request=request)

        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingSubdomain.objects.filter(label='sd test').exists())

        # Validation fail (invalid user)
        data = { 'label': 'test_fail', 'training_domain':td, 'active': True }
        request.user = self.ref_cmp_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(TrainingSubdomain.objects.filter(label='test_fail').exists())

    
    def test_campus_creation(self):
        """
        Test admin Campus creation with group rights
        """

        data = { 'label': 'testCampus', 'active': True }

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
        data = {
            'label': 'testBuilding',
            'campus': testCampus.pk,
            'url': 'https://www.building.com',
            'active': True
        }

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


    def test_component_creation(self):
        """
        Test admin Component creation with group rights
        """
        data = {
            'code':'AB123',
            'label': 'test',
            'url':'http://url.fr',
            'active': True
        }

        request.user = self.scuio_user

        form = ComponentForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Component.objects.filter(label='test').exists())

        # Validation fail (code unicity)
        data["label"] = "test_fail"
        form = ComponentForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        request.user = self.ref_cmp_user
        form = ComponentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertEqual(Component.objects.count(), 1)


    def test_training_creation(self):
        """
        Test admin Training creation with group rights
        """
        training_domain_data = {'label': 'domain', 'active': True}
        training_subdomain_data = {'label': 'subdomain', 'active': True}
        component_data = {
            'code': 'AB123',
            'label': 'test',
            'url': 'http://url.fr',
            'active': True
        }

        training_domain = TrainingDomain.objects.create(**training_domain_data)
        training_subdomain = TrainingSubdomain.objects.create(
            training_domain=training_domain, **training_subdomain_data)
        component = Component.objects.create(**component_data)

        self.assertTrue(TrainingDomain.objects.all().exists())
        self.assertTrue(TrainingSubdomain.objects.all().exists())
        self.assertTrue(Component.objects.all().exists())

        data = {
            'label': 'test',
            'url':'http://url.fr',
            'components': [component.pk, ],
            'training_subdomains': [training_subdomain.pk, ],
        }

    def test_bachelor_mention_creation(self):
        """
        Test admin bachelor mention creation with group rights
        """

        data = {
            'label': 'testBachelor',
            'active': True
        }

        request.user = self.scuio_user

        form = BachelorMentionForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(BachelorMention.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = BachelorMentionForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(BachelorMention.objects.filter(
            label='test_fail').exists())

    def test_cancel_type_creation(self):
        """
        Test admin bachelor mention creation with group rights
        """

        data = {
            'label': 'testBachelor',
            'active': True
        }

        request.user = self.scuio_user

        form = CancelTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CancelType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = CancelTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CancelType.objects.filter(
            label='test_fail').exists())


    def test_course_type_creation(self):
        """
        Test course type creation with group rights
        """
        data = {
            'label': 'testCourse',
            'active': True
        }

        request.user = self.scuio_user

        form = CourseTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = CourseTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CourseType.objects.filter(
            label='test_fail').exists())


    def test_public_type_creation(self):
        """
        Test public type mention creation with group rights
        """
        data = {
            'label': 'testCourse',
            'active': True
        }

        request.user = self.scuio_user

        form = PublicTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = PublicTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(PublicType.objects.filter(
            label='test_fail').exists())
