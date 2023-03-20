from decimal import Decimal

from django.test import TestCase

from immersionlyceens.templatetags import immersionlyceens_tags as tags

from ..models import AccompanyingDocument


class TemplatetagsTestCase(TestCase):

    def test_fix_lang_code(self):
        self.assertEqual(
            tags.fix_lang_code('fr'), 'fr-FR')

        self.assertEqual(
            tags.fix_lang_code('fr-fr'), 'fr-FR')

        self.assertEqual(
            tags.fix_lang_code('novlang'), 'novlang')

    def test_active_accompanying_docs(self):
        self.assertEqual(
            len(tags.active_accompanying_docs()),
            0
        )