import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import (BachelorMention, Building, Campus, CancelType,
                      CourseType, PublicType, UniversityYear,
                      Holiday, Vacation, Calendar)


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

    def test_university_year__date_is_between(self):
        now = datetime.datetime.today().date()
        o = UniversityYear.objects.create(
            label='UniversityYear',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=3),
            registration_start_date=datetime.datetime.today().date(),
        )

        # inside
        # start < date < end
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=2)))
        # start = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=1)))
        # end = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=3)))

        # date < start < end
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=-99)))

        # start < end < date
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=99)))


class TestHolidayCase(TestCase):

    def test_holiday_str(self):
        label = "Holiday"
        o = Holiday.objects.create(
            label=label,
            date=datetime.datetime.today().date(),
        )
        self.assertEqual(str(o), label)


class TestVacationCase(TestCase):

    def test_vacation_str(self):
        label = "Vacation"
        o = Vacation.objects.create(
            label=label,
            start_date=datetime.datetime.today().date(),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        )
        self.assertEqual(str(o), label)

    def test_vacation__date_is_between(self):
        now = datetime.datetime.today().date()
        o = Vacation.objects.create(
            label="Vacation",
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=3),
        )

        # inside
        # start < date < end
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=2)))
        # start = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=1)))
        # end = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=3)))

        # date < start < end
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=-99)))

        # start < end < date
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=99)))



class TestCalendarCase(TestCase):

    def test_calendar_str(self):
        label = "Calendar"
        o = Calendar.objects.create(
            label=label,
            year_start_date=datetime.datetime.today().date(),
            year_end_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            year_registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            year_nb_authorized_immersion=4
        )

        self.assertEqual(str(o), label)

    def test_calendar__date_is_between(self):
        now = datetime.datetime.today().date()
        o = Calendar.objects.create(
            label='Calendar',
            year_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            year_end_date=datetime.datetime.today().date() + datetime.timedelta(days=3),
            year_registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
            year_nb_authorized_immersion=4
        )

        # inside
        # start < date < end
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=2)))
        # start = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=1)))
        # end = date
        self.assertTrue(o.date_is_between(now + datetime.timedelta(days=3)))

        # date < start < end
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=-99)))

        # start < end < date
        self.assertFalse(o.date_is_between(now + datetime.timedelta(days=99)))
