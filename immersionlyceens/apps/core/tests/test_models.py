import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from ..models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus,
    CancelType, Course, CourseType, Establishment, EvaluationFormLink,
    EvaluationType, Holiday, PublicDocument, PublicType, Slot, Structure,
    Training, TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)


class CampusTestCase(TestCase):
    def test_campus_model(self):
        test_campus = Campus.objects.create(label='MyCampus')
        self.assertEqual(test_campus.active, True)
        self.assertEqual(str(test_campus), 'MyCampus (-)')

        establishment = Establishment.objects.create(
            code='ETA2', label='Etablissement 2', short_label='Eta 2', active=True, master=False, email='test@test.com',
            address= 'address', department='departmeent', city='city', zip_code= 'zip_code', phone_number= '+33666'
        )

        test_campus.establishment = establishment
        test_campus.save()

        self.assertEqual(str(test_campus), f'{test_campus.label} ({establishment.label})')


    def test_building_str(self):
        test_campus = Campus.objects.create(label='MyCampus')
        test_building = Building.objects.create(label='MyBuilding', campus=test_campus)
        self.assertEqual(str(test_building), 'MyBuilding')


class BachelorMentionTestCase(TestCase):
    def test_bachelor_mention_model(self):
        label = "Techo parade"
        o = BachelorMention.objects.create(label=label)
        self.assertEqual(str(o), label)
        self.assertTrue(o.active)


class CancelTypeTestCase(TestCase):
    def test_cancel_type_model(self):
        label = "Cancel type"
        o = CancelType.objects.create(label=label)
        self.assertEqual(str(o), label)
        self.assertTrue(o.active)


class CourseTypeTestCase(TestCase):
    def test_course_type_model(self):
        label = "course type"
        full_label = "course full type"
        o = CourseType.objects.create(full_label=full_label, label=label)
        self.assertEqual(str(o), f"{full_label} ({label})")
        self.assertTrue(o.active)


class PublicTypeTestCase(TestCase):
    def test_public_type_model(self):
        label = "PublicType"
        o = PublicType.objects.create(label=label)
        self.assertEqual(str(o), label)
        self.assertTrue(o.active)



class UniversityYearTestCase(TestCase):
    def test_university_year_model(self):
        label = "UniversityYear"
        o = UniversityYear.objects.create(
            label=label,
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=4),
            registration_start_date=datetime.datetime.today().date(),
        )
        self.assertEqual(str(o), label)
        self.assertTrue(o.active)

        # Test activation
        o2 = UniversityYear.objects.create(
            label='World',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=2),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=4),
            registration_start_date=datetime.datetime.today().date(),
        )

        self.assertFalse(o2.active)

        o.delete()
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
    def test_holiday_model(self):
        label = "Holiday"
        o = Holiday.objects.create(label=label, date=datetime.datetime.today().date(),)
        self.assertEqual(str(o), label)
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
        # Structure
        c = Structure.objects.create(label='my structure', code='R2D2')
        # Training domain
        td = TrainingDomain.objects.create(label='my_domain')
        # Training subdomain
        tsd = TrainingSubdomain.objects.create(label='my_sub_domain', training_domain=td)
        # Training
        t = Training.objects.create(label='training',)  #  training_subdomains={tsd}, structures=[c, ])

        t.training_subdomains.add(tsd)
        t.structures.add(c)

        # Course type
        ct = CourseType.objects.create(label='CM')
        # Course
        course = Course.objects.create(label='my super course', training=t, structure=c)

        # Campus
        campus = Campus.objects.create(label='Campus Esplanade')

        # Building
        building = Building.objects.create(label='Le portique', campus=campus)

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
