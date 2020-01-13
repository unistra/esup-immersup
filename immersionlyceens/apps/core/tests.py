from django.test import TestCase

# Create your tests here.
from immersionlyceens.apps.core.models import BachelorMention


class BachelorMentionTestCase(TestCase):

    def test_bachelor_mention_str(self):
        label = "Techo parade"
        o = BachelorMention.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_bachelor_mention_activated(self):
        o = BachelorMention.objects.create(label="Techo parade")
        self.assertTrue(o.active)
