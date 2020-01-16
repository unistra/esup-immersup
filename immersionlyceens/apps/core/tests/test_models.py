import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import BachelorMention, Building, Campus, CancelType, CourseType, PublicType, UniversityYear


class CampusTestCase(TestCase):

    def test_campus_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(str(test_campus), 'MyCampus')

    def test_campus_creation_activated(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(test_campus.active, True)

    def test_building_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        test_building = Building.objects.create(label='MyBuilding', campus=test_campus)
        self.assertEqual(str(test_building), 'MyBuilding')


class BachelorMentionTestCase(TestCase):

    def test_bachelor_mention_str(self):
        label = "Techo parade"
        o = BachelorMention.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_bachelor_mention_activated(self):
        o = BachelorMention.objects.create(label="Techo parade")
        self.assertTrue(o.active)


class CancelTypeTestCase(TestCase):

    def test_cancel_type_str(self):
        label = "Cancel type"
        o = CancelType.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_cancel_type_activated(self):
        o = CancelType.objects.create(label="Cancel type")
        self.assertTrue(o.active)


class CourseTypeTestCase(TestCase):

    def test_course_type_str(self):
        label = "course type"
        o = CourseType.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_course_type_activated(self):
        o = CourseType.objects.create(label="course type")
        self.assertTrue(o.active)


class PublicTypeTestCase(TestCase):

    def test_public_type_str(self):
        label = "PublicType"
        o = PublicType.objects.create(label=label)
        self.assertEqual(str(o), label)

    def test_public_type_activated(self):
        o = PublicType.objects.create(label="PublicType")
        self.assertTrue(o.active)

class UniversityYearTestCase(TestCase):

    def test_public_type_str(self):
        label = "UniversityYear"
        o = UniversityYear.objects.create(
            label=label,
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=4),
            registration_start_date=datetime.datetime.today().date(),
        )
        self.assertEqual(str(o), label)

    def test_public_type_activated(self):
        o1 = UniversityYear.objects.create(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=4),
            registration_start_date=datetime.datetime.today().date(),
        )

        o2 = UniversityYear.objects.create(
            label='World',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=4),
            registration_start_date=datetime.datetime.today().date(),
        )
        self.assertTrue(o1.active)
        self.assertFalse(o2.active)

        o1.delete()
        o2.label = 'Coucou'
        o2.save()
        self.assertTrue(o2.active)
