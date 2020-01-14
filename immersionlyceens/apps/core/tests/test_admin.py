"""
Django Admin Forms tests suite
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory

from django.conf import settings
from ..admin import TrainingDomainAdmin
from ..models import (
    TrainingDomain, TrainingSubdomain
)

from ..admin_forms import (
    TrainingDomainForm, TrainingSubdomainForm
)

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

        
        