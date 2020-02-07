"""
Django API tests suite
"""
import json
import unittest

from django.conf import settings
from compat.templatetags.compat import url
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from immersionlyceens.apps.core.models import AccompanyingDocument

request_factory = RequestFactory()
request = request_factory.get('/admin')

class APITestCase(TestCase):
    """Tests for API"""
    
    fixtures = ['group']
    
    def setUp(self):
        self.scuio_user = get_user_model().objects.create_user(
            username='scuio',
            password='pass',
            email='immersion@no-reply.com',
            first_name='scuio',
            last_name='scuio',
        )
        
        self.client = Client()
        self.client.login(username='scuio', password='pass')
        
        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)    


    def test_API_get_documents__ok(self):
        request.user = self.scuio_user
        
        url = "/api/get_available_documents/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        ajax_request = self.client.get(url, request, **header)

        content = ajax_request.content.decode()

        json_content = json.loads(content)
        self.assertIn('msg', json_content)
        self.assertIn('data', json_content)
        self.assertIsInstance(json_content['data'], list)
        self.assertIsInstance(json_content['msg'], str)

        docs = AccompanyingDocument.objects.filter(active=True)
        self.assertEqual(len(json_content['data']), docs.count())


    def test_API_get_documents__wrong_request(self):
        """No access"""
        request = self.client.get('/api/get_available_documents/')
        self.assertEqual(request.status_code, 403)  # forbidden
