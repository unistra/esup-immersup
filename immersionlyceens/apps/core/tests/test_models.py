from asyncio import DatagramTransport
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord,
)

from ..models import (
    AccompanyingDocument, AttestationDocument, BachelorMention, BachelorType,
    Building, Campus, CancelType, Course, CourseType, CustomThemeFile,
    Establishment, EvaluationFormLink, EvaluationType, GeneralBachelorTeaching,
    GeneralSettings, HigherEducationInstitution, HighSchool, HighSchoolLevel,
    Holiday, ImmersionUser, Period, PublicDocument, PublicType,
    RefStructuresNotificationsSettings, Slot, Structure, StudentLevel,
    Training, TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)


class CampusTestCase(TestCase):
    fixtures = ['higher']

    def test_campus_model(self):
        test_campus = Campus.objects.create(
            label='MyCampus',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            active=True
        )
        self.assertEqual(test_campus.active, True)
        self.assertEqual(str(test_campus), 'MyCampus (-)')

        establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test@test.com',
            address= 'address',
            department='departement',
            city='city',
            zip_code= 'zip_code',
            phone_number= '+33666',
            uai_reference=HigherEducationInstitution.objects.first()
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
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

    def test_university_year_model(self):
        label = "UniversityYear"
        o = UniversityYear.objects.create(
            label=label,
            start_date=self.today + timedelta(days=2),
            end_date=self.today + timedelta(days=4),
            registration_start_date=self.today,
        )
        self.assertEqual(str(o), label)
        self.assertTrue(o.active)

        # Test activation
        o2 = UniversityYear.objects.create(
            label='World',
            start_date=self.today + timedelta(days=2),
            end_date=self.today + timedelta(days=4),
            registration_start_date=self.today,
        )

        self.assertFalse(o2.active)

        o.delete()
        o2.label = 'Coucou'
        o2.save()
        self.assertTrue(o2.active)


    def test_university_year__date_is_between(self):
        o = UniversityYear.objects.create(
            label='UniversityYear',
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=3),
            registration_start_date=self.today,
        )

        # inside
        # start < date < end
        self.assertTrue(o.date_is_between(self.today + timedelta(days=2)))
        # start = date
        self.assertTrue(o.date_is_between(self.today + timedelta(days=1)))
        # end = date
        self.assertTrue(o.date_is_between(self.today + timedelta(days=3)))

        # date < start < end
        self.assertFalse(o.date_is_between(self.today + timedelta(days=-99)))

        # start < end < date
        self.assertFalse(o.date_is_between(self.today + timedelta(days=99)))


class TestHolidayCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

    def test_holiday_model(self):
        label = "Holiday"
        o = Holiday.objects.create(label=label, date=self.today,)
        self.assertEqual(str(o), label)
        self.assertTrue(Holiday.date_is_a_holiday(self.today))
        self.assertFalse(Holiday.date_is_a_holiday(self.today + timedelta(days=1)))


class TestVacationCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

    def test_vacation_str(self):
        label = "Vacation"
        o = Vacation.objects.create(
            label=label,
            start_date=self.today,
            end_date=self.today + timedelta(days=1),
        )
        self.assertEqual(str(o), label)

    def test_vacation__date_is_between(self):
        o = Vacation.objects.create(
            label="Vacation",
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=3),
        )

        # inside
        # start < date < end
        self.assertTrue(o.date_is_between(self.today + timedelta(days=2)))
        # start = date
        self.assertTrue(o.date_is_between(self.today + timedelta(days=1)))
        # end = date
        self.assertTrue(o.date_is_between(self.today + timedelta(days=3)))

        # date < start < end
        self.assertFalse(o.date_is_between(self.today + timedelta(days=-99)))

        # start < end < date
        self.assertFalse(o.date_is_between(self.today + timedelta(days=99)))

    def test_vacation__date_is_inside_a_vacation(self):
        now = self.today
        o = Vacation.objects.create(
            label="Vacation", start_date=now + timedelta(days=1), end_date=now + timedelta(days=3),
        )

        self.assertTrue(Vacation.date_is_inside_a_vacation(now + timedelta(days=2)))
        self.assertFalse(Vacation.date_is_inside_a_vacation(now + timedelta(days=999)))

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
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

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
        campus = Campus.objects.create(
            label='Campus Esplanade',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            active=True
        )

        # Building
        building = Building.objects.create(label='Le portique', campus=campus)

        s = Slot(
            course=course,
            course_type=ct,
            campus=campus,
            building=building,
            room='Secret room',
            date=self.today + timedelta(days=1),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=10,
            additional_information='Additional information',
        )
        s.save()
        self.assertTrue(Slot.objects.filter(id=s.id).count() > 0)


class TrainingCase(TestCase):
    fixtures = ['higher']

    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

        cls.hs = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=cls.today - timedelta(days=10),
            convention_end_date=cls.today + timedelta(days=10),
            postbac_immersion=True
        )
        cls.structure = Structure.objects.create(label="test structure")

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

    def test_distinct_establishments(self):
        t = Training.objects.create(label="training2")
        establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test@test.com',
            address= 'address',
            department='departement',
            city='city',
            zip_code= 'zip_code',
            phone_number= '+33666',
            uai_reference=HigherEducationInstitution.objects.first()
        )
        establishment2 = Establishment.objects.create(
            code='ETA3',
            label='Etablissement 3',
            short_label='Eta 3',
            active=True,
            master=False,
            email='test@test.com',
            address= 'address',
            department='departement',
            city='city',
            zip_code= 'zip_code',
            phone_number= '+33666',
            uai_reference=HigherEducationInstitution.objects.last()
        )
        self.structure.establishment = establishment
        self.structure.save()
        t.structures.add(self.structure)
        structure2 = Structure.objects.create(
            label="test structure2",
            code="str2",
            establishment=establishment
        )
        self.assertQuerysetEqual(
            t.distinct_establishments(),
            ["<Establishment: ETA2 : Etablissement 2>", ],
            ordered=False
        )

        t.structures.add(structure2)
        # Only one establishment is returned
        self.assertTrue(t.distinct_establishments().count() == 1)
        self.assertQuerysetEqual(
            t.distinct_establishments(),
            ["<Establishment: ETA2 : Etablissement 2>",],
            ordered=False
        )

        # Return two establishments
        structure3 = Structure.objects.create(
            label="test structure3",
            code="str3",
            establishment=establishment2
        )
        t.structures.add(structure3)
        self.assertTrue(t.distinct_establishments().count() == 2)
        self.assertQuerysetEqual(
            t.distinct_establishments(),
            ["<Establishment: ETA2 : Etablissement 2>", "<Establishment: ETA3 : Etablissement 3>"],
            ordered=False
        )

    def test_str_training(self):
        t = Training.objects.create(label="training")
        self.assertEqual(str(t), 'training')


class StructureTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.structure = Structure.objects.create(code='test', label="test structure")

    def test_str_structure(self):
        self.assertEqual(str(self.structure), 'test : test structure')


class HighSchoolTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

        cls.hs = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=cls.today - timedelta(days=10),
            convention_end_date=cls.today + timedelta(days=10),
            postbac_immersion=True
        )

    def test_str_structure(self):
        self.assertEqual(str(self.hs), 'STRASBOURG - HS1')


class ImmersionUserTestCase(TestCase):
    fixtures = ['group', 'higher', 'high_school_levels', 'student_levels', 'post_bachelor_levels']

    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.now()

        cls.no_si_establishment = Establishment.objects.create(
            code='ETA',
            label='Etablissement',
            short_label='Eta',
            active=True,
            master=False,
            email='test@test.com',
            address='address',
            department='departement',
            city='city',
            zip_code='zip_code',
            phone_number='+33666',
            data_source_plugin=None,
            uai_reference=HigherEducationInstitution.objects.first()
        )
        cls.establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement2',
            short_label='Eta2',
            active=True,
            master=False,
            email='test@test.com',
            address='address',
            department='departement',
            city='city',
            zip_code='zip_code',
            phone_number='+33666',
            data_source_plugin="LDAP",
            uai_reference=HigherEducationInstitution.objects.last()
        )
        cls.hs = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=cls.today - timedelta(days=10),
            convention_end_date=cls.today + timedelta(days=10),
            postbac_immersion=True,
            signed_charter=True,
        )

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

    def test_is_local_account(self):
        user = ImmersionUser.objects.create_user(
            username="test",
            email="test@test.fr",
            password="pass",
            establishment=self.establishment
        )

        Group.objects.get(name='VIS').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='LYC').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='REF-LYC').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='INTER').user_set.add(user)
        user.highschool = self.hs
        self.assertTrue(user.is_local_account())

        user.highschool = None
        self.assertFalse(user.is_local_account())
        user.establishment = self.no_si_establishment
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='REF-ETAB').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='REF-STR').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.groups.clear()
        Group.objects.get(name='SRV-JUR').user_set.add(user)
        self.assertTrue(user.is_local_account())

        user.establishment = self.establishment
        self.assertFalse(user.is_local_account())

        user.groups.clear()
        user.establishment = self.no_si_establishment
        Group.objects.get(name='ETU').user_set.add(user)
        self.assertFalse(user.is_local_account())


    def test_student_establishment(self):
        user = ImmersionUser.objects.create_user(
            username="test",
            email="test@test.fr",
            password="pass",
            establishment=self.establishment
        )

        institution = HigherEducationInstitution.objects.last() # same as 'self.establishment.uai_reference'

        Group.objects.get(name='ETU').user_set.add(user)
        student_record = StudentRecord.objects.create(
            student=user,
            uai_code=institution.uai_code,
            birth_date=timezone.now(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=BachelorType.objects.get(label__iexact='général')
        )

        # Check that the link between the student record and Establishment is good (same object)
        self.assertEqual(user.get_student_establishment(), self.establishment)
        self.assertEqual(user.get_high_school_or_student_establishment(), self.establishment)

    def test_pupil_highschool(self):
        user = ImmersionUser.objects.create_user(
            username="test",
            email="test@test.fr",
            password="pass"
        )

        Group.objects.get(name='LYC').user_set.add(user)

        hs_record = HighSchoolStudentRecord.objects.create(
            student=user,
            highschool=self.hs,
            birth_date=datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.order_by('order').first(),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe'
        )

        self.assertEqual(user.get_high_school().label, self.hs.label)
        self.assertEqual(user.get_high_school_or_student_establishment().label, self.hs.label)


    def test_can_register(self):
        # Create all objects we need
        speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            establishment=self.establishment,
        )

        student = get_user_model().objects.create_user(
            username="test",
            email="test@test.fr",
            password="pass",
            establishment=self.establishment
        )

        institution = HigherEducationInstitution.objects.last()  # same as 'self.establishment.uai_reference'

        Group.objects.get(name='ETU').user_set.add(student)
        Group.objects.get(name='INTER').user_set.add(speaker1)
        student_record = StudentRecord.objects.create(
            student=student,
            uai_code=institution.uai_code,
            birth_date=self.today - timedelta(days=8000),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=BachelorType.objects.get(label__iexact='général')
        )

        structure = Structure.objects.create(
            label="test structure",
            code="STR",
            establishment=self.establishment
        )
        t_domain = TrainingDomain.objects.create(label="test t_domain")
        t_sub_domain = TrainingSubdomain.objects.create(
            label="test t_sub_domain",
            training_domain=t_domain
        )
        training = Training.objects.create(label="test training")
        training.training_subdomains.add(t_sub_domain)
        training.structures.add(structure)

        course = Course.objects.create(
            label="course 1",
            training=training,
            structure=structure
        )
        course.speakers.add(speaker1)
        course_type = CourseType.objects.create(label='CM')
        slot = Slot.objects.create(
            course=course,
            course_type=course_type,
            campus=None,
            building=None,
            face_to_face=False,
            url='http://www.google.fr',
            room=None,
            date=self.today + timedelta(days=1),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            published=True,
            additional_information="Hello there!",
            establishments_restrictions=False
        )

        can_register, errors = student.can_register_slot(slot)
        self.assertTrue(can_register)
        self.assertEqual(errors, [])

        # Add a restriction on the slot and try again
        slot.establishments_restrictions = True
        slot.allowed_establishments.add(self.no_si_establishment)
        slot.save()

        can_register, errors = student.can_register_slot(slot)
        self.assertFalse(can_register)
        self.assertEqual(errors, ['Establishments restrictions in effect'])

        # Todo : test other restrictions here


class TrainingDomainTestCase(TestCase):
    def test_str_training_domain(self):
        td = TrainingDomain.objects.create(label="label")
        self.assertEqual(str(td), 'label')


class TrainingSubDomainTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.td = TrainingDomain.objects.create(label="label")

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
        g = GeneralSettings.objects.create(setting="MySetting", parameters={'value': 'myvalue'})
        self.assertEqual(str(g), 'MySetting')
        self.assertEqual(g.parameters["value"], 'myvalue')


class CustomThemeFileTestCase(TestCase):
    def test_str_custom_theme_file(self):
        data = {
            'type': 'CSS',
            'file': SimpleUploadedFile("test.css", b"toto", content_type="text/css"),
        }
        c = CustomThemeFile.objects.create(**data)
        self.assertEqual(str(c), "file : %s (%s)" % (c.file.name, c.type))


class AttestationDocumentTestCase(TestCase):
    def test_attestation_creation(self):
        attestation = AttestationDocument.objects.create(
            label='Test',
            active=True
        )

        attestation2 = AttestationDocument.objects.create(
            label='Test 2',
            active=True
        )

        # Default values
        self.assertTrue(attestation.active)
        self.assertTrue(attestation.for_minors)
        self.assertTrue(attestation.mandatory)
        self.assertTrue(attestation.requires_validity_date)
        self.assertEqual(attestation.order, 1) # Careful with this value if we add fixtures

        # Order increase
        self.assertEqual(attestation2.order, 2)

class RefStructuresNotificationsSettingsTestCase(TestCase):
    def test_str_ref_structures_notifications_settings(self):

        r = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='immersion4@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
            date_joined=timezone.now(),
            establishment=Establishment.objects.first(),
        )

        s = Structure.objects.create(label='my structure', code='666')

        n = RefStructuresNotificationsSettings.objects.create(
            user = r
        )
        n.structures.add(s)
        self.assertEqual(str(n), "%s (%s)" % (str(r), str(s.label)))