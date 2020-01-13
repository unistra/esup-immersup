from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import Campus


class CampusTestCase(TestCase):

    def test_campus_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(str(test_campus), 'MyCampus')

    def test_campus_creation_activated(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(test_campus.active, True)
