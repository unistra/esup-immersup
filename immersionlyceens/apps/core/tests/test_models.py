import datetime
import logging

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from ..models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus,
    CancelType, Course, CourseType, Establishment, EvaluationFormLink,
    EvaluationType, GeneralBachelorTeaching, GeneralSettings, HighSchool,
    Holiday, ImmersionUser, PublicDocument, PublicType, Slot, Structure,
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


class TrainingCase(TestCase):
    def setUp(self) -> None:
        self.today = datetime.datetime.today()
        self.hs = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=self.today - datetime.timedelta(days=10),
            convention_end_date=self.today + datetime.timedelta(days=10),
            postbac_immersion=True
        )
        self.structure = Structure.objects.create(label="test structure")

    def test_training__is_highschool(self):
        # False
        t = Training.objects.create(label='training',)
        self.assertFalse(t.is_highschool())

        t.highschool = self.hs
        t.save()
        self.assertTrue(t.is_highschool())

    def test_training__is_structure(self):
        t = Training.objects.create(label="training2")
        self.assertFalse(t.is_structure())

        t.structures.add(self.structure)
        self.assertTrue(t.is_structure())

    def test_training__can_delete(self):
        t = Training.objects.create(label="training2")
        t.structures.add(self.structure)

        self.assertTrue(t.can_delete())

        course = Course.objects.create(label="course 1", training=t, structure=self.structure)
        self.assertFalse(t.can_delete())

    def test_distinct_establishments(self):
        t = Training.objects.create(label="training2")
        establishment = Establishment.objects.create(
            code='ETA2', label='Etablissement 2', short_label='Eta 2', active=True, master=False, email='test@test.com',
            address= 'address', department='departmeent', city='city', zip_code= 'zip_code', phone_number= '+33666'
        )
        establishment2 = Establishment.objects.create(
            code='ETA3', label='Etablissement 3', short_label='Eta 3', active=True, master=False, email='test@test.com',
            address= 'address', department='departmeent', city='city', zip_code= 'zip_code', phone_number= '+33666'
        )
        self.structure.establishment=establishment
        self.structure.save()
        t.structures.add(self.structure)
        structure2 = Structure.objects.create(label="test structure2", code="str2", establishment=establishment)
        self.assertQuerysetEqual(t.distinct_establishments(), \
                                 ["<Establishment: ETA2 : Etablissement 2>", ],
                                  ordered=False)

        t.structures.add(structure2)
        # Only one establishment is returned
        self.assertTrue(t.distinct_establishments().count() == 1)
        self.assertQuerysetEqual(t.distinct_establishments(), \
                                 ["<Establishment: ETA2 : Etablissement 2>",],
                                 ordered=False)

        # Return two establishments
        structure3 = Structure.objects.create(label="test structure3", code="str3", establishment=establishment2)
        t.structures.add(structure3)
        self.assertTrue(t.distinct_establishments().count() == 2)
        self.assertQuerysetEqual(t.distinct_establishments(), \
                                 ["<Establishment: ETA2 : Etablissement 2>", "<Establishment: ETA3 : Etablissement 3>"],
                                 ordered=False)

    def test_str_training(self):
        t = Training.objects.create(label="training")
        self.assertEqual(str(t), 'training')


class StructureTestCase(TestCase):
    def setUp(self):
        self.structure = Structure.objects.create(code='test', label="test structure")

    def test_str_structure(self):
        self.assertEqual(str(self.structure), 'test : test structure')


class HighSchoolTestCase(TestCase):
    def setUp(self):
        self.today = datetime.datetime.today()
        self.hs = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=self.today - datetime.timedelta(days=10),
            convention_end_date=self.today + datetime.timedelta(days=10),
            postbac_immersion=True
        )

    def test_str_structure(self):
        self.assertEqual(str(self.hs), 'STRASBOURG - HS1')


class ImmersionUserTestCase(TestCase):
    def test_str_user(self):
        iu = ImmersionUser.objects.create_user(
            username='user',
            password='pass',
            email='bofh@no-reply.com',
            first_name='john',
            last_name='bofh',
        )
        iu.set_password('pass')
        iu.save()
        self.assertEqual(str(iu), 'bofh john')

class TrainingDomainTestCase(TestCase):
    def test_str_training_domain(self):
        td = TrainingDomain.objects.create(label="label")
        self.assertEqual(str(td), 'label')


class TrainingSubDomainTestCase(TestCase):
    def setUp(self):
        self.td = TrainingDomain.objects.create(label="label")

    def test_str_training_domain(self):
        tsd = TrainingSubdomain.objects.create(
            label="subdomain label",
            training_domain=self.td
        )
        self.assertEqual(str(tsd), 'label - subdomain label')

class GeneralBachelorTeachingTestCase(TestCase):
    def test_str_general_bachelor_teaching(self):
        gbt = GeneralBachelorTeaching.objects.create(label="GeneralBachelorTeaching")
        self.assertEqual(str(gbt), 'GeneralBachelorTeaching')
        self.assertTrue(gbt.active)

class CourseTestCase(TestCase):
    def test_str_course(self):
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

        self.assertEqual(str(course),'my super course')

class GeneralSettingsTestCase(TestCase):
    def test_str_general_settings(self):
        g = GeneralSettings.objects.create(setting="MySetting", parameters=[{'my_setting': 'myvalue'}])
        self.assertEqual(str(g), 'MySetting')
