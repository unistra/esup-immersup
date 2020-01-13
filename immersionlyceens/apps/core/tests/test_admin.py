"""
Django Admin Forms tests suite
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, RequestFactory

from django.conf import settings
from ..admin import CourseDomainAdmin
from ..models import CourseDomain
from ..admin_forms import CourseDomainForm

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
        data = { 'label': 'test', 'active': True }

        request.user = self.scuio_user

        form = CourseDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseDomain.objects.filter(label='test').exists())

        # Validation fail (invalid user)        
        data = { 'label': 'test_fail', 'active': True }
        request.user = self.ref_cmp_user
        form = CourseDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CourseDomain.objects.filter(label='test_fail').exists())

        
        