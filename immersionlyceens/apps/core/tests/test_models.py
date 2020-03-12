import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import (
    AccompanyingDocument,
    BachelorMention,
    Building,
    Calendar,
    Campus,
    CancelType,
    Component,
    Course,
    CourseType,
    EvaluationFormLink,
    EvaluationType,
    Holiday,
    PublicDocument,
    PublicType,
    Slot,
    Training,
    TrainingDomain,
    TrainingSubdomain,
    UniversityYear,
    Vacation,
)


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
        full_label = "course full type"
        o = CourseType.objects.create(full_label=full_label, label=label)
        self.assertEqual(str(o), f"{full_label} ({label})")

    def test_course_type_activated(self):
        o = CourseType.objects.create(label="course type", full_label="course full type")
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
        o = Holiday.objects.create(label=label, date=datetime.datetime.today().date(),)
        self.assertEqual(str(o), label)

    def test_holiday__date_is_a_holiday(self):
        o = Holiday.objects.create(label="Holiday", date=datetime.datetime.today().date(),)

        self.assertTrue(Holiday.date_is_a_holiday(datetime.datetime.today().date()))
        self.assertFalse(Holiday.date_is_a_holiday(datetime.datetime.today().date() + datetime.timedelta(days=1)))


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
            label="Vacation", start_date=now + datetime.timedelta(days=1), end_date=now + datetime.timedelta(days=3),
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

    def test_vacation__date_is_inside_a_vacation(self):
        now = datetime.datetime.today().date()
        o = Vacation.objects.create(
            label="Vacation", start_date=now + datetime.timedelta(days=1), end_date=now + datetime.timedelta(days=3),
        )

        self.assertTrue(Vacation.date_is_inside_a_vacation(now + datetime.timedelta(days=2)))
        self.assertFalse(Vacation.date_is_inside_a_vacation(now + datetime.timedelta(days=999)))


class TestCalendarCase(TestCase):
    def test_calendar_str(self):
        label = "Calendar"
        o = Calendar.objects.create(
            label=label,
            year_start_date=datetime.datetime.today().date(),
            year_end_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            year_registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            year_nb_authorized_immersion=4,
        )

        self.assertEqual(str(o), label)

    def test_calendar__date_is_between(self):
        now = datetime.datetime.today().date()
        o = Calendar.objects.create(
            label='Calendar',
            year_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            year_end_date=datetime.datetime.today().date() + datetime.timedelta(days=3),
            year_registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            year_nb_authorized_immersion=4,
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


# TODO: Fix me with manytomany public_type field
# class TestAccompanyingDocumentCase(TestCase):
#     def test_accompanying_document_str(self):
#         label = "testDocument"

#         public_type_data = {'label': 'testPublicType', 'active': True}
#         public_type_obj = PublicType.objects.create(**public_type_data)


#         data = {
#             'label': label,
#             'description': 'testDescription',
#             'active': True,
#             'public_type': ["1",],
#             'document': SimpleUploadedFile(
#                 "testpron.pdf", b"toto", content_type="application/pdf"
#             ),
#         }
#         o = AccompanyingDocument.objects.create(**data)
#         o.public_type.add(public_type_obj.pk)
#         o.save()
#         self.assertEqual(str(o), label)


class TestPublicDocumentCase(TestCase):
    def test_public_document_str(self):
        label = "testDocument"

        data = {
            'label': label,
            'active': True,
            'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf"),
            'published': False,
        }
        o = PublicDocument.objects.create(**data)
        self.assertEqual(str(o), label)


class TestEvaluationTypeCase(TestCase):
    def test_evaluation_type_str(self):
        o = EvaluationType.objects.create(code='testCode', label='testLabel')
        self.assertEqual(str(o), 'testCode : testLabel')


class TestSlotCase(TestCase):
    def test_slot__creation(self):
        # Component
        c = Component(label='my component', code='R2D2', url='https://google.fr')
        c.save()
        # Training domain
        td = TrainingDomain(label='my_domain')
        td.save()
        # Training subdomain
        tsd = TrainingSubdomain(label='my_sub_domain', training_domain=td)
        tsd.save()
        # Training
        t = Training(label='training',)  #  training_subdomains={tsd}, components=[c, ])
        t.save()
        t.training_subdomains.add(tsd)
        t.components.add(c)

        # Course type
        ct = CourseType(label='CM')
        ct.save()
        # Course
        course = Course(label='my super course', training=t, component=c)
        course.save()

        # Campus
        campus = Campus(label='Campus Esplanade')
        campus.save()
        # Building
        building = Building(label='Le portique', campus=campus)
        building.save()

        s = Slot(
            course=course,
            course_type=ct,
            campus=campus,
            building=building,
            room='Secret room',
            date=datetime.datetime.today(),
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
            n_places=10,
            additional_information='Additional information',
        )
        s.save()
        self.assertTrue(Slot.objects.filter(id=s.id).count() > 0)
