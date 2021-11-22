from decimal import Decimal

from django.test import TestCase
from immersionlyceens.templatetags import immersionlyceens_tags as tags


class TemplatetagsTestCase(TestCase):

    def test_fix_lang_code(self):
        self.assertEqual(
            tags.fix_lang_code('fr'), 'fr-FR')

        self.assertEqual(
            tags.fix_lang_code('fr-fr'), 'fr-FR')

        self.assertEqual(
            tags.fix_lang_code('novlang'), 'novlang')
