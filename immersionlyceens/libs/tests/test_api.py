"""
Django API tests suite
"""
import json
import unittest

from compat.templatetags.compat import url
from django.test import TestCase

from immersionlyceens.apps.core.models import AccompanyingDocument


class APITestCase(TestCase):
	"""Tests for API"""

	def test_API_get_documents__ok(self):
		ajax_request = self.client.get(
			'/api/get_available_documents/',
			{},
			HTTP_X_REQUESTED_WITH='XMLHttpRequest'
		)

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
