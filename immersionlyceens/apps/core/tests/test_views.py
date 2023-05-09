"""
Immersion app forms tests
"""
import datetime
import json

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from immersionlyceens.apps.immersion.forms import (
    HighSchoolStudentRecordManagerForm,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord,
)

from ..models import (
    BachelorMention, BachelorType, Building, Campus, Course, CourseType,
    Establishment, GeneralBachelorTeaching, GeneralSettings, HigherEducationInstitution,
    HighSchool, HighSchoolLevel, Holiday, Immersion, ImmersionUser,
    OffOfferEvent, OffOfferEventType, Period, PostBachelorLevel, Slot,
    Structure, StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UniversityYear, Visit,
)

request_factory = RequestFactory()
request = request_factory.get('/admin')

class CoreViewsTestCase(TestCase):
    fixtures = ['group', 'group_permissions', 'generalsettings', 'mailtemplatevars', 'mailtemplate', 'images', 'higher']

    @classmethod
    def setUpTestData(cls):
        """
        Test data for Core app tests
        @TODO : this is a copy/paste from immersion app setup, it may need to be cleaned a little
        """
        cls.today = timezone.localdate()

        cls.master_establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test1@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first()
        )

        cls.establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test2@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last()
        )

        cls.high_school = HighSchool.objects.create(
            active=True,
            label='HS1',
            address='here',
            country='FR',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            with_convention=True,
            convention_start_date=cls.today - datetime.timedelta(days=10),
            convention_end_date=cls.today + datetime.timedelta(days=10),
            postbac_immersion=True,
            signed_charter=True,
        )

        cls.high_school2 = HighSchool.objects.create(
            active=True,
            label='HS2',
            address='here',
            department=67,
            country='FR',
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='d@e.fr',
            head_teacher_name='M. A B',
            with_convention=True,
            convention_start_date=cls.today - datetime.timedelta(days=10),
            convention_end_date=cls.today + datetime.timedelta(days=10),
            postbac_immersion=False,
            signed_charter=True,
        )

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string='whatever',
        )

        cls.highschool_user.set_password('pass')
        cls.highschool_user.save()

        # Set a second high school student for duplicates search
        cls.highschool_user2 = get_user_model().objects.create_user(
            username='hs2',
            password='pass',
            email='hs2@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string=None,
        )

        cls.highschool_user2.set_password('pass')
        cls.highschool_user2.save()

        cls.student_user = get_user_model().objects.create_user(
            username='test@student.fr',
            password='pass',
            email='test@student.fr',
            first_name='student',
            last_name='user'
        )

        cls.student_user.set_password('pass')
        cls.student_user.save()

        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            highschool=cls.high_school
        )

        cls.speaker1.set_password('pass')
        cls.speaker1.save()

        cls.speaker2 = get_user_model().objects.create_user(
            username='speaker2',
            password='pass',
            email='speaker-immersion2@no-reply.com',
            first_name='speak2',
            last_name='HER2',
            highschool=cls.high_school2
        )

        cls.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='lycref@no-reply.com',
            first_name='lyc',
            last_name='REF',
            highschool=cls.high_school,
            is_staff=True
        )

        cls.lyc_ref.set_password('pass')
        cls.lyc_ref.save()

        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='ref_etab@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=cls.establishment,
            is_staff=True,
        )

        cls.ref_etab_user.set_password('pass')
        cls.ref_etab_user.save()

        cls.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='ref_master_etab@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=cls.master_establishment,
            is_staff=True
        )

        cls.ref_etab_user.set_password('pass')
        cls.ref_etab_user.save()

        cls.structure = Structure.objects.create(
            code='C1',
            label="test structure",
            establishment=cls.establishment
        )
        cls.structure2 = Structure.objects.create(
            code='C2',
            label="Second test structure",
            establishment=cls.establishment
        )

        cls.ref_str_user = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
            establishment=cls.establishment
        )

        cls.ref_str_user.structures.add(cls.structure)
        cls.ref_str_user.set_password('pass')
        cls.ref_str_user.save()

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='INTER').user_set.add(cls.speaker2)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user2)
        Group.objects.get(name='ETU').user_set.add(cls.student_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str_user)

        BachelorMention.objects.create(
            label="Sciences et technologies du management et de la gestion (STMG)",
            active=True
        )

        GeneralBachelorTeaching.objects.create(label="Maths", active=True)

        cls.t_domain = TrainingDomain.objects.create(label="test t_domain")
        cls.t_domain2 = TrainingDomain.objects.create(label="test t_domain 2")

        cls.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=cls.t_domain)
        cls.t_sub_domain2 = TrainingSubdomain.objects.create(label="test t_sub_domain 2",
                                                              training_domain=cls.t_domain2)

        cls.training = Training.objects.create(label="test training")
        cls.training2 = Training.objects.create(label="test training 2")
        cls.training3 = Training.objects.create(label="test training 3")

        cls.training.training_subdomains.add(cls.t_sub_domain)
        cls.training.structures.add(cls.structure)
        cls.training2.training_subdomains.add(cls.t_sub_domain)
        cls.training2.structures.add(cls.structure)
        cls.training3.training_subdomains.add(cls.t_sub_domain2)
        cls.training3.structures.add(cls.structure2)

        cls.course = Course.objects.create(label="course 1", training=cls.training, structure=cls.structure)
        cls.course.speakers.add(cls.speaker1)

        cls.course2 = Course.objects.create(label="course 2", training=cls.training3, structure=cls.structure2)
        cls.course2.speakers.add(cls.speaker2)

        cls.campus = Campus.objects.create(label='Esplanade')
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')
        cls.slot = Slot.objects.create(
            course=cls.course, course_type=cls.course_type, campus=cls.campus,
            building=cls.building, room='room 1', date=cls.today + datetime.timedelta(days=5),
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        cls.slot.speakers.add(cls.speaker1),

        # Add another slot : structure referent shouldn't have access to this one
        cls.slot2 = Slot.objects.create(
            course=cls.course2, course_type=cls.course_type, campus=cls.campus,
            building=cls.building, room='room 12', date=cls.today + datetime.timedelta(days=5),
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        cls.slot2.speakers.add(cls.speaker2)

        cls.slot3 = Slot.objects.create(
            course=cls.course2, course_type=cls.course_type, campus=cls.campus,
            building=cls.building, room='room 12', date=cls.today + datetime.timedelta(days=6),
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        cls.slot3.speakers.add(cls.speaker2)

        # Periods
        cls.period_past = Period.objects.create(
            label="Past period",
            immersion_start_date=cls.today - datetime.timedelta(days=10),
            immersion_end_date=cls.today - datetime.timedelta(days=8),
            registration_start_date=cls.today - datetime.timedelta(days=12),
            allowed_immersions=4
        )

        cls.period1 = Period.objects.create(
            label='Period 1',
            registration_start_date=cls.today + datetime.timedelta(days=2),
            immersion_start_date=cls.today + datetime.timedelta(days=5),
            immersion_end_date=cls.today + datetime.timedelta(days=40),
            allowed_immersions=4
        )

        cls.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=cls.today - datetime.timedelta(days=365),
            end_date=cls.today + datetime.timedelta(days=20),
            registration_start_date=cls.today - datetime.timedelta(days=1),
            active=True,
        )

        cls.immersion = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot,
            attendance_status=1
        )

        cls.event_type = OffOfferEventType.objects.create(label="Event type label")
        

    def setUp(self):
        self.client = Client()
        

    def test_import_holidays(self):
        self.assertFalse(Holiday.objects.all().exists())

        # No access
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/admin/holiday/import", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Holiday.objects.all().exists())

        # As master establishment manager
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/admin/holiday/import", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Holiday.objects.all().exists())


    def test_slots(self):
        # First test simple get with no structure or training parameter

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/slots/", follow=True)
        self.assertIn(self.structure, response.context["structures"])
        self.assertIsNone(response.context["structure_id"])
        self.assertIsNone(response.context["training_id"])
        self.assertEqual(self.ref_etab_user.establishment.id, response.context["establishment_id"])

        self.assertIsNone(response.context["highschool_id"])

        # with parameters
        response = self.client.get(
            reverse("establishment_filtered_course_slots_list",
                    args=[self.establishment.id, self.structure.id, self.training.id, self.course.id])
        )
        self.assertEqual(self.establishment.id, response.context["establishment_id"])
        self.assertEqual(self.structure.id, response.context["structure_id"])
        self.assertEqual(self.training.id, response.context["training_id"])

        # As structure referent
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/slots/", follow=True)
        self.assertIn(self.structure, response.context["structures"])
        self.assertEqual(response.context["structures"].count(), 1)
        self.assertNotIn(self.structure2, response.context["structures"])

        self.assertEqual(self.ref_str_user.establishment.id, response.context["establishment_id"])

        if self.ref_str_user.structures.count() == 1:
            self.assertEqual(self.ref_str_user.structures.first().id, response.context["structure_id"])
        else:
            self.assertIsNone(response.context["structure_id"])

        self.assertIsNone(response.context["training_id"])
        self.assertIsNone(response.context["highschool_id"])

        # As any other user
        self.client.login(username='hs', password='pass')
        response = self.client.get("/core/slots/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slots/")

    def test_add_slot(self):
        # As any other user
        self.client.login(username='hs', password='pass')
        response = self.client.get("/core/slot")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slot")

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/slot", follow=True)
        # self.assertIn(self.structure, response.context["structures"])

        data = {
            'structure': self.structure.id,
            'training': self.training.id,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'face_to_face': True,
            'room': "212",
            'date': (self.today - datetime.timedelta(days=9)).strftime("%Y-%m-%d"),
            'start_time': "12:00",
            'end_time': "14:00",
            'speakers': [self.speaker1.id],
            'n_places': 33,
            'additional_information': "Here is additional data.",
            'published': "on",
            'save': 1
        }

        # Fail with date in the past
        response = self.client.post("/core/slot", data, follow=True)
        self.assertFalse(Slot.objects.filter(room="212").exists())
        self.assertIn("You can&#x27;t set a date in the past", response.content.decode('utf-8'))

        # Fail with date outside of period dates (end of period : d+40)
        date = self.today + datetime.timedelta(days=60)
        data["date"] = date.strftime("%Y-%m-%d")
        response = self.client.post("/core/slot", data, follow=True)
        self.assertFalse(Slot.objects.filter(room="212").exists())
        self.assertIn(
            "No available period found for slot date &#x27;%s&#x27;, please create one first" % date.strftime("%Y-%m-%d"),
            response.content.decode('utf-8')
        )

        # Update to a valid date
        data["date"] = (self.today + datetime.timedelta(days=6)).strftime("%Y-%m-%d")

        # Fail with missing field
        del(data['speakers'])
        response = self.client.post("/core/slot", data, follow=True)
        self.assertFalse(Slot.objects.filter(room="212").exists())
        self.assertIn("Required fields are not filled in", response.content.decode('utf-8'))

        # Success
        data['speakers'] = [self.speaker1.id]

        self.course.published = False
        self.course.save()
        self.course.refresh_from_db()

        response = self.client.post("/core/slot", data, follow=True)
        self.assertTrue(Slot.objects.filter(room="212").exists())
        slot = Slot.objects.get(room="212")
        self.assertIn("Course slot \"%s\" created." % slot, response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')

        self.course.refresh_from_db()
        self.assertTrue(self.course.published)

        # get slot form with an existing slot
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/slot/%s" % self.slot.id, follow=True)
        self.assertEqual(response.context["slot"].course_id, self.course.id)

        # Save a slot and get back to add form
        data = {
            'structure': self.structure.id,
            'training': self.training.id,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'face_to_face': True,
            'room': "S40",
            'date': (self.today + datetime.timedelta(days=6)).strftime("%Y-%m-%d"),
            'start_time': "16:00",
            'end_time': "18:00",
            'speakers': [self.speaker1.id],
            'n_places': 33,
            'additional_information': "Here is additional data.",
            'published': "on",
            'save_add': 1
        }

        response = self.client.post("/core/slot", data, follow=True)
        self.assertTrue(Slot.objects.filter(room="S40").exists())
        slot = Slot.objects.get(room="S40")
        self.assertIn("Course slot \"%s\" created." % slot, response.content.decode('utf-8'))
        self.assertNotIn("Course published", response.content.decode('utf-8')) # course already published
        self.assertEqual(response.status_code, 200)

        self.assertFalse("slot" in response.context) # "Add new" form : no slot
        self.assertEqual(response.request['PATH_INFO'], '/core/slot')

        # Duplicate a slot : save, stay on form & keep data
        del(data["save_add"])
        data["duplicate"] = 1
        data["room"] = "S41"
        response = self.client.post("/core/slot", data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Slot.objects.filter(room="S41").exists())
        slot = Slot.objects.get(room="S41")
        self.assertIn("Course slot \"%s\" created." % slot, response.content.decode('utf-8'))
        self.assertNotIn("Course published", response.content.decode('utf-8')) # course already published
        self.assertEqual(response.request['PATH_INFO'], '/core/slot/%s/1' % slot.id)

        # Get as structure referent
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/slot", follow=True)

    def test_multiple_slots_creation(self):
        """
        Test Repeat feature in course slot form
        """
        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')
        self.assertFalse(Slot.objects.filter(room="REPEAT_TEST").exists())

        # Create another period and extend the university year dates
        year = UniversityYear.get_active()
        year.end_date = self.today + datetime.timedelta(days=90)
        year.save()

        period = Period.objects.create(
            label="Next period",
            registration_start_date=self.today + datetime.timedelta(days=50),
            immersion_start_date=self.today + datetime.timedelta(days=55),
            immersion_end_date=self.today + datetime.timedelta(days=65),
            allowed_immersions=4
        )

        # These slots days will be kept : +12, 19, 26, 33, 40, 61
        # Not created : 47, 54, 68
        data = {
            'structure': self.structure.id,
            'training': self.training.id,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'face_to_face': True,
            'room': "REPEAT_TEST",
            'date': (self.today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            'repeat': (self.today + datetime.timedelta(days=33)).strftime("%Y-%m-%d"),
            'slot_dates[]': [
                (self.today + datetime.timedelta(days=12)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=19)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=26)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=33)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=40)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=47)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=54)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=61)).strftime("%d/%m/%Y"),
                (self.today + datetime.timedelta(days=68)).strftime("%d/%m/%Y"),
            ],
            'start_time': "12:00",
            'end_time': "14:00",
            'speakers': [self.speaker1.id, self.speaker2.id],
            'n_places': 33,
            'additional_information': "Here is additional data.",
            'published': "on",
            'allowed_establishments': [self.establishment.id, self.master_establishment.id],
            'allowed_highschools': [self.high_school.id, self.high_school2.id],
            'allowed_highschool_levels': [HighSchoolLevel.objects.order_by('order').first().pk],
            'allowed_student_levels': [StudentLevel.objects.order_by('order').first().pk],
            'allowed_post_bachelor_levels': [PostBachelorLevel.objects.order_by('order').first().pk],
            'save': 1
        }
        # All dates have been selected : initial slot created + 6 copie, 3 won't be created
        response = self.client.post("/core/slot", data, follow=True)
        self.assertEqual(response.status_code, 200)

        slots = Slot.objects.filter(room="REPEAT_TEST").order_by('date')
        self.assertEqual(slots.count(), 7)

        delta = 5 # initial slot day
        while delta < 75:
            d = self.today + datetime.timedelta(days=delta)
            if delta in [5, 12, 19, 26, 33, 40, 61]:
                slot = Slot.objects.get(room="REPEAT_TEST", date=d)
                self.assertEqual(slot.speakers.all().count(), 2)
            else:
                self.assertFalse(Slot.objects.filter(room="REPEAT_TEST", date=d))

            delta += 7

        # Delete slots and do it again with unchecked dates (d+19 and d+40)
        # The following dates will be kept : 12, 26, 33, 61
        Slot.objects.filter(room="REPEAT_TEST").delete()
        self.assertFalse(Slot.objects.filter(room="REPEAT_TEST").exists())
        data['slot_dates[]'] = [
            (self.today + datetime.timedelta(days=12)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=26)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=33)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=47)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=54)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=61)).strftime("%d/%m/%Y"),
            (self.today + datetime.timedelta(days=68)).strftime("%d/%m/%Y"),
        ]

        response = self.client.post("/core/slot", data, follow=True)
        self.assertEqual(response.status_code, 200)

        slots = Slot.objects.filter(room="REPEAT_TEST").order_by('date')
        self.assertEqual(slots.count(), 5)

        dates = [
            self.today + datetime.timedelta(days=5),
            self.today + datetime.timedelta(days=12),
            self.today + datetime.timedelta(days=26),
            self.today + datetime.timedelta(days=33),
            self.today + datetime.timedelta(days=61)
        ]
        dates_idx = 0
        for slot in slots:
            self.assertEqual(slot.date, dates[dates_idx])
            self.assertEqual(slot.speakers.all().count(), 2)
            self.assertEqual(
                list(slot.allowed_establishments.order_by('id').values_list('id', flat=True)),
                sorted([self.establishment.id, self.master_establishment.id])
            )
            self.assertEqual(
                list(slot.allowed_highschools.order_by('id').values_list('id', flat=True)),
                sorted([self.high_school.id, self.high_school2.id])
            )
            self.assertEqual(
                slot.allowed_highschool_levels.first(),
                HighSchoolLevel.objects.order_by('order').first()
            )
            self.assertEqual(
                slot.allowed_student_levels.first(),
                StudentLevel.objects.order_by('order').first()
            )
            self.assertEqual(
                slot.allowed_post_bachelor_levels.first(),
                PostBachelorLevel.objects.order_by('order').first()
            )
            dates_idx += 1

    def test_modify_slot(self):
        # As any other user
        self.client.login(username='hs', password='pass')
        response = self.client.get("/core/slot/%s" % self.slot.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slot/%s" % self.slot.id)

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')
        # Fail with a non existing slot
        response = self.client.get("/core/slot/250", follow=True)
        self.assertIn("Slot not found", response.content.decode('utf-8'))

        # Get an existing slot
        response = self.client.get("/core/slot/%s" % self.slot.id, follow=True)

        self.course.published = False
        self.course.save()

        # Get slot data and update a few fields
        data = {
            'structure': self.slot.course.structure.id,
            'training': self.slot.course.training.id,
            'course': self.slot.course.id,
            'course_type': self.slot.course_type.id,
            'campus': self.slot.campus.id,
            'building': self.slot.building.id,
            'face_to_face': True,
            'room': "New room",
            'date': (self.slot.date + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            'start_time': "13:30",
            'end_time': "15:30",
            'speakers': [self.speaker1.id],
            'n_places': 20,
            'additional_information': "New data",
            'published': "on",
            "notify_student": "on",
            'save': 1
        }
        # Fail with missing field
        del(data['speakers'])
        response = self.client.post("/core/slot/%s" % self.slot.id, data, follow=True)
        self.assertFalse(Slot.objects.filter(room="New room").exists())

        # Success
        data['speakers'] = [self.speaker1.id]
        response = self.client.post("/core/slot/%s" % self.slot.id, data, follow=True)
        slot = Slot.objects.get(pk=self.slot.id)

        # Check updated fields
        self.assertEqual(slot.room, "New room")
        self.assertEqual(slot.start_time, datetime.time(13, 30))
        self.assertEqual(slot.end_time, datetime.time(15, 30))
        self.assertEqual(slot.n_places, 20)
        self.assertEqual(slot.additional_information, "New data")
        self.assertEqual(slot.date, (self.slot.date + datetime.timedelta(days=5)))

        self.assertIn("Course slot \"%s\" updated." % slot, response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertIn("Notifications have been sent (1)", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')

        # TODO : test save_add and duplicate

        # Get as structure referent
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/slot/%s" % self.slot.id, follow=True)

        # Test with a slot the user doesn't have access to
        response = self.client.get("/core/slot/%s" % self.slot2.id)
        self.assertTrue(response.status_code, 302)
        self.assertTrue(response.url, "/core/slots/")

        response = self.client.get("/core/slot/%s" % self.slot2.id, follow=True)
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')
        self.assertIn("This slot belongs to another structure", response.content.decode('utf-8'))

    def test_delete_slot(self):
        self.assertTrue(Slot.objects.filter(pk=self.slot.id).exists())

        # As structure referent, test with a slot the user doesn't have access to
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/slot/delete/%s" % self.slot2.id, follow=True)
        self.assertEqual(response.content.decode('utf-8'), "This slot belongs to another structure")
        self.assertTrue(Slot.objects.filter(pk=self.slot.id).exists())

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/slot/delete/%s" % self.slot.id, follow=True)
        self.assertEqual(response.content.decode('utf-8'), "ok")
        self.assertFalse(Slot.objects.filter(pk=self.slot.id).exists())

        # Non existing slot
        response = self.client.get("/core/slot/delete/123", follow=True)
        self.assertEqual(response.content.decode('utf-8'), "ok")
        self.assertFalse(Slot.objects.filter(pk=self.slot.id).exists())


    def test_courses_list(self):
        # As any other user
        self.client.login(username='hs', password='pass')
        response = self.client.get("/core/courses_list")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/courses_list")

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')

        # with invalid year dates
        self.university_year.start_date = self.today + datetime.timedelta(days=1)
        self.university_year.save()

        response = self.client.get("/core/courses_list")
        self.assertIn(self.structure, response.context["structures"])
        self.assertEqual(None, response.context["structure_id"])
        self.assertFalse(response.context["can_update_courses"])
        self.assertIn("Courses cannot be created, updated or deleted", response.content.decode('utf-8'))

        # With valid dates
        response = self.client.get("/core/courses_list")
        self.university_year.start_date = self.today - datetime.timedelta(days=365)
        self.university_year.save()
        response = self.client.get("/core/courses_list")
        self.assertTrue(response.context["can_update_courses"])

        # As structure referent
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/courses_list")
        self.assertIn(self.structure, response.context["structures"])
        self.assertNotIn(self.structure2, response.context["structures"])
        self.assertEqual(self.structure.id, response.context["structure_id"])
        self.assertTrue(response.context["can_update_courses"])


    def test_course(self):
        # As any other user
        self.client.login(username='hs', password='pass')
        response = self.client.get("/core/course")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/course")

        # As ref_etab user
        self.client.login(username='ref_etab', password='pass')

        # with invalid year dates
        self.university_year.start_date = self.today + datetime.timedelta(days=1)
        self.university_year.save()

        response = self.client.get("/core/course")
        self.assertFalse(response.context["can_update_courses"])
        self.assertIn("Courses cannot be created, updated or deleted", response.content.decode('utf-8'))

        # With valid dates
        response = self.client.get("/core/course")
        self.university_year.start_date = self.today - datetime.timedelta(days=365)
        self.university_year.save()
        response = self.client.get("/core/course")
        self.assertTrue(response.context["can_update_courses"])

        # Try to access a non-existing course
        response = self.client.get("/core/course/123456")
        self.assertIn("Create a new course", response.content.decode('utf-8'))

        # Post data to create a new course
        data = {
            'structure': self.structure.id,
            'training': self.training.id,
            'label': "New test course",
            'url': "http://new-course.test.fr",
            'published': True,
            'speakers_list':"",
            'save': 1
        }
        # Fail with missing field
        response = self.client.post("/core/course", data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertIn("At least one speaker is required", response.content.decode('utf-8'))

        data['speakers_list'] = \
            """[{"username":"jean", "firstname":"Jean", "lastname":"Jacques", "email":"jean-jacques@domain.fr"},
                {"username":"john", "firstname":"John", "lastname":"Jack", "email":"john.jack@domain.fr"}]"""

        # Fail with invalid URL format
        data['url'] = "whatever"
        response = self.client.post("/core/course", data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertIn("Enter a valid URL.", response.content.decode('utf-8'))

        data['url'] = "http://new-course.test.fr"


        ###############
        # Success
        ###############

        # Not published, without speakers
        data.pop("published")
        data["speakers_list"] = "[]"

        response = self.client.post("/core/course", data, follow=True)
        self.assertTrue(Course.objects.filter(label="New test course").exists())
        Course.objects.get(label="New test course").delete() # cleanup

        # Published, with speakers
        data["published"] = True
        data['speakers_list'] = \
            """[{"username":"jean", "firstname":"Jean", "lastname":"Jacques", "email":"jean-jacques@domain.fr"},
                {"username":"john", "firstname":"John", "lastname":"Jack", "email":"john.jack@domain.fr"}]"""
        response = self.client.post("/core/course", data, follow=True)
        # Course and speakers must exist
        self.assertTrue(Course.objects.filter(label="New test course").exists())

        course = Course.objects.get(label="New test course")
        self.assertTrue(ImmersionUser.objects.filter(username='jean-jacques@domain.fr').exists())
        self.assertTrue(ImmersionUser.objects.filter(username='john.jack@domain.fr').exists())
        self.assertEqual(course.speakers.count(), 2)
        self.assertIn("A confirmation email has been sent to jean-jacques@domain.fr", response.content.decode('utf-8'))
        self.assertIn("A confirmation email has been sent to john.jack@domain.fr", response.content.decode('utf-8'))

        # Course update
        response = self.client.get("/core/course/%s" % course.id, data, follow=True)
        self.assertIn("New test course", response.content.decode('utf-8'))

        data["label"] = "This is my new label"
        data["speakers_list"] = \
            """[{"username":"jean-jacques@domain.fr", "firstname":"Jean", "lastname":"Jacques", "email":"jean-jacques@domain.fr"}]"""
        response = self.client.post("/core/course/%s" % course.id, data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertTrue(Course.objects.filter(label="This is my new label").exists())
        self.assertIn("Course successfully updated", response.content.decode('utf-8'))
        course = Course.objects.get(label="This is my new label")
        self.assertEqual(course.speakers.count(), 1)

        # Form with course duplication
        response = self.client.get("/core/course/%s/1" % course.id, data, follow=True)
        self.assertIn(course.label, response.content.decode('utf-8'))
        self.assertIn("jean-jacques@domain.fr", response.content.decode('utf-8'))

        # Duplicate a course : save, stay on form & keep data
        del(data["save"])
        data["save_duplicate"] = 1
        data["label"] = "Duplicated course label"
        response = self.client.post("/core/course", data, follow=True)
        self.assertTrue(Course.objects.filter(label="Duplicated course label").exists())
        self.assertTrue(Course.objects.filter(label="This is my new label").exists())
        self.assertIn("Course successfully saved", response.content.decode('utf-8'))

        course2 = Course.objects.get(label="Duplicated course label")
        self.assertEqual(response.request['PATH_INFO'], '/core/course/%s/1' % course2.id)

        # Try to access a course the user doesn't have access to
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/course/%s" % self.course2.id, follow=True)
        self.assertIn("You don't have enough privileges to update this course", response.content.decode("utf-8"))
        data["label"] = "This shouldn't happen"
        response = self.client.post("/core/course/%s" % self.course2.id, data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/courses_list')
        self.assertFalse(Course.objects.filter(label="This shouldn't happen").exists())


    def test_my_courses(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/mycourses", follow=True)
        self.assertIn("My courses", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/mycourses", follow=True)
        self.assertNotIn("My courses", response.content.decode('utf-8'))

    def test_my_visits(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/myvisits", follow=True)
        self.assertIn("My visits", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/myvisits", follow=True)
        self.assertNotIn("My visits", response.content.decode('utf-8'))

    def test_my_events(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/myevents", follow=True)
        self.assertIn("My events", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/myevents", follow=True)
        self.assertNotIn("My events", response.content.decode('utf-8'))

    def test_my_courses_slots(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/myslots/courses", follow=True)
        self.assertIn("My slots - HER speak", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/myslots/courses", follow=True)
        self.assertNotIn("My slots - HER speak", response.content.decode('utf-8'))

    def test_my_visits_slots(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/myslots/visits", follow=True)
        self.assertIn("My visits slots - HER speak", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/myslots/visits", follow=True)
        self.assertNotIn("My visits slots - HER speak", response.content.decode('utf-8'))

    def test_my_events_slots(self):
        self.client.login(username='speaker1', password='pass')
        response = self.client.get("/core/myslots/events", follow=True)
        self.assertIn("My events slots - HER speak", response.content.decode('utf-8'))

        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/myslots/events", follow=True)
        self.assertNotIn("My events slots - HER speak", response.content.decode('utf-8'))

    def test_myhighschool(self):
        self.client.login(username='lycref', password='pass')
        # Shouldn't work (no access)
        response = self.client.get("/core/high_school/%s" % self.high_school2.id, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')

        # Should work
        response = self.client.get("/core/high_school/%s" % self.high_school.id, follow=True)
        self.assertIn("My high school - %s" % self.high_school.label, response.content.decode('utf-8'))
        self.assertTrue(self.high_school.with_convention)

        # Update
        data = {
            'address': "12 rue des Plantes",
            'address2': "test_line_2",
            'address3': "test_line_3",
            'department': 68,
            'city': "MULHOUSE",
            'country': "FR",
            'zip_code': '68100',
            'phone_number': '0388888888',
            'email': 'lycee@domain.fr',
            'head_teacher_name': 'Headmaster'
        }

        response = self.client.post("/core/high_school/%s" % self.high_school.id, data, follow=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(HighSchool.objects.filter(address='12 rue des Plantes').exists())

        # These settings can't be updated here
        data.update({
            'with_convention': False,
            'convention_start_date': '2023-04-02',
            'convention_end_date': '2023-06-30',
        })

        response = self.client.post("/core/high_school/%s" % self.high_school.id, data, follow=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.high_school.refresh_from_db()
        self.assertTrue(self.high_school.with_convention)
        self.assertEqual(self.high_school.convention_start_date, self.today - datetime.timedelta(days=10))
        self.assertTrue(self.high_school.convention_end_date, self.today + datetime.timedelta(days=10))


    def test_my_high_school_speakers(self):
        self.client.login(username='lycref', password='pass')

        # Shouldn't work (no access)
        response = self.client.get("/core/high_school_speakers/%s" % self.high_school2.id, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')

        # Should work
        response = self.client.get("/core/high_school_speakers/%s" % self.high_school.id, follow=True)
        self.assertIn("My high school - %s" % self.high_school.label, response.content.decode('utf-8'))
        self.assertIn(self.speaker1, response.context["speakers"])
        self.assertNotIn(self.speaker2, response.context["speakers"])


    def test_speaker(self):
        """
        Test speaker creation
        """
        self.assertFalse(ImmersionUser.objects.filter(email="test_speaker@test.com").exists())

        # No access
        for username in ['ref_etab', 'ref_master_etab', 'ref_str']:
            self.client.login(username=username, password='pass')
            response = self.client.get(reverse('speaker'))
            self.assertEqual(response.status_code, 302)

        # Success
        self.client.login(username='lycref', password='pass')
        response = self.client.get(reverse('speaker'))
        self.assertEqual(response.status_code, 200)

        data = {
            'last_name': "Test_lastname",
            'first_name': "Test_firstname",
            'email': "test_speaker@test.com"
        }

        response = self.client.post(reverse('speaker'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ImmersionUser.objects.filter(email="test_speaker@test.com").exists())
        speaker = ImmersionUser.objects.get(email="test_speaker@test.com")
        self.assertEqual(speaker.email, data["email"])
        self.assertTrue(speaker.creation_email_sent)


    def test_my_students(self):
        # As high school referent
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/my_students", follow=True)

        self.assertIn('highschool', response.context)
        self.assertEqual(response.context['highschool'], self.high_school)
        self.assertTrue(response.context['can_show_users_without_record'])

        # As a ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/my_students", follow=True)

        self.assertIn('highschool', response.context)
        self.assertEqual(response.context['highschool'], None)
        self.assertTrue(response.context['can_show_users_without_record'])


    def test_student_validation(self):
        # As a ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/student_validation/", follow=True)
        self.assertNotIn('high_school', response.context)

        response = self.client.get("/core/student_validation/%s" % self.high_school.id, follow=True)
        self.assertIn('high_school', response.context)
        self.assertEqual(response.context['high_school'], self.high_school)

        response = self.client.get("/core/student_validation/?hs_id=%s" % self.high_school.id, follow=True)
        self.assertIn('hs_id', response.context)
        self.assertEqual(response.context['hs_id'], self.high_school.id)

        # With a non-existing high school id
        response = self.client.get("/core/student_validation/99", follow=True)
        self.assertIn("This high school id does not exist", response.content.decode('utf-8'))

        # As a high school referent
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/student_validation/", follow=True)
        self.assertIn('high_school', response.context)
        self.assertEqual(response.context['high_school'], self.lyc_ref.highschool)

        # Even with a non existing high school id
        response = self.client.get("/core/student_validation/99", follow=True)
        self.assertIn('high_school', response.context)
        self.assertEqual(response.context['high_school'], self.lyc_ref.highschool)


    def test_highschool_student_record_form_manager(self):
        # As a high school referent
        hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=self.today,
            phone='0123456789',
            level=HighSchoolLevel.objects.order_by('order').first(),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe'
        )

        hs_record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school2,
            birth_date=self.today,
            phone='0123456789',
            level=HighSchoolLevel.objects.order_by('order').first(),
            class_name='1ere T3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe'
        )

        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/hs_record_manager/%s" % hs_record.id, follow=True)
        self.assertIn(self.highschool_user.last_name, response.content.decode('utf-8'))
        self.assertIn(self.highschool_user.first_name, response.content.decode('utf-8'))
        self.assertIn(hs_record.class_name, response.content.decode('utf-8'))

        # Post
        data = {
            'student': self.highschool_user.id,
            'high_school_id': self.high_school.id,
            'first_name': 'Jean',
            'last_name': 'Jacques',
            'birth_date': "01/06/2002",
            'level': HighSchoolLevel.objects.order_by('order')[1].id,
            'class_name': 'TS 3'
        }
        response = self.client.post("/core/hs_record_manager/%s" % hs_record.id, data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')

        highschool_user = ImmersionUser.objects.get(id=self.highschool_user.id)
        hs_record = HighSchoolStudentRecord.objects.get(id=hs_record.id)

        self.assertEqual(highschool_user.first_name, 'Jean')
        self.assertEqual(highschool_user.last_name, 'Jacques')
        self.assertEqual(hs_record.level, HighSchoolLevel.objects.order_by('order')[1]) # second level
        self.assertEqual(hs_record.class_name, 'TS 3')

        # Missing field
        data.pop('class_name')
        response = self.client.post("/core/hs_record_manager/%s" % hs_record.id, data, follow=True)
        self.assertIn("High school student record modification failure", response.content.decode('utf-8'))

        # Student belonging to another high school
        response = self.client.get("/core/hs_record_manager/%s" % hs_record2.id, follow=True)

        self.assertIn("This student is not in your high school", response.content.decode('utf-8'))
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')

        # Non existing record id
        response = self.client.get("/core/hs_record_manager/999", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')



    def test_structure(self):
        # As a REF-STR user
        self.client.login(username='ref_str', password='pass')
        response = self.client.get("/core/structure", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('structure', response.context)
        self.assertNotIn('structures', response.context)
        self.assertEqual(self.structure, response.context['structure'])

        # Post a new mailing list URL
        # self.assertEqual(self.structure.mailing_list, None)
        # data = {
        #     "code" : self.structure.code,
        #     "mailing_list": "new_mailing_list@mydomain.com",
        #     "submit": 1
        # }
        # response = self.client.post("/core/structure/%s" % self.structure.code, data, follow=True)

        # self.assertEqual(response.request['PATH_INFO'], '/core/structure')
        # structure = Structure.objects.get(code='C1')
        # self.assertEqual(structure.mailing_list, 'new_mailing_list@mydomain.com')

        # As any other user, first check redirection code, then redirection url
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/structure")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/core/structure", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')


    # def test_stats(self):
    #     # As a ref_etab user
    #     self.client.login(username='ref_etab', password='pass')
    #     response = self.client.get("/core/stats/", follow=True)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIn(self.structure2, response.context['structures'])
    #     self.assertNotIn('high_school_id', response.context)

    #     # As a ref-str user
    #     self.client.login(username='ref_str', password='pass')
    #     response = self.client.get("/core/stats/", follow=True)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertNotIn(self.structure2, response.context['structures'])
    #     self.assertNotIn('high_school_id', response.context)

    #     # As ref-lyc user
    #     self.client.login(username='lycref', password='pass')
    #     response = self.client.get("/core/stats/", follow=True)
    #     self.assertIn('high_school_id', response.context)
    #     self.assertEqual(response.context['high_school_id'], self.high_school.id)


    def test_students_presence(self):
        # As a ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/students_presence", follow=True)
        self.assertEqual(response.status_code, 200)

        # first slot date
        self.assertEqual(response.context['min_date'], self.slot.date.strftime("%Y-%m-%d"))
        # last slot date
        self.assertEqual(response.context['max_date'], self.slot3.date.strftime("%Y-%m-%d"))


    def test_duplicated_accounts(self):
        # As a ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get("/core/duplicates", follow=True)
        self.assertEqual(response.status_code, 200)

        # As any other user, first check redirection code, then redirection url
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/duplicates")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/core/duplicates", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')


    def test_visit(self):
        visit = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever",
            published=True
        )

        visit.speakers.add(self.speaker1)

        # As a ref_master_etab user
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/visits", follow=True)
        self.assertEqual(response.status_code, 200)

        # Update
        response = self.client.get(f"/core/visit/{visit.id}", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{visit.establishment.id}\" selected", content)
        self.assertIn(f"value=\"{visit.structure.id}\" selected", content)
        self.assertIn(f"value=\"{visit.highschool.id}\" selected", content)
        self.assertIn(f"value=\"{visit.purpose}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "username": self.speaker1.username,
            "lastname": self.speaker1.last_name,
            "firstname": self.speaker1.first_name,
            "email": self.speaker1.email,
            "display_name": f"{self.speaker1.last_name} {self.speaker1.first_name}",
            "is_removable": True
        }]))

        data = {
            "establishment": visit.establishment.id,
            "structure": visit.structure.id,
            "highschool": visit.highschool.id,
            "published": True,
            "purpose": "New visit purpose",
            "speakers_list": json.dumps([{
                "email": self.speaker2.email,
                "username": self.speaker2.username,
                "lastname": self.speaker2.last_name,
                "firstname": self.speaker2.first_name,
            }])
        }

        response = self.client.post(f"/core/visit/{visit.id}", data, follow=True)
        self.assertEqual(response.status_code, 200)
        visit.refresh_from_db()
        self.assertEqual(visit.purpose, "New visit purpose")


        # Duplicate a visit : check form values
        response = self.client.get(f"/core/visit/{visit.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{visit.establishment.id}\" selected", content)
        self.assertIn(f"value=\"{visit.structure.id}\" selected", content)
        self.assertIn(f"value=\"{visit.highschool.id}\" selected", content)
        self.assertIn(f"value=\"{visit.purpose}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "username": self.speaker2.username,
            "lastname": self.speaker2.last_name,
            "firstname": self.speaker2.first_name,
            "email": self.speaker2.email,
            "display_name": f"{self.speaker2.last_name} {self.speaker2.first_name}",
            "is_removable": True
        }]))


    def test_visit_slot(self):
        visit = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever",
            published=False
        )

        visit.speakers.add(self.speaker1)

        self.assertFalse(Slot.objects.filter(visit=visit).exists())

        # As a ref_master_etab user
        # slots list
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/visits_slots", follow=True)
        self.assertEqual(response.status_code, 200)

        # Create
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/visit_slot", follow=True)
        self.assertEqual(response.status_code, 200)

        data = {
            'visit': visit.id,
            'face_to_face': True,
            'room': "anywhere",
            'published': True,
            'date': (self.today - datetime.timedelta(days=9)).strftime("%Y-%m-%d"),
            'start_time': "12:00",
            'end_time': "14:00",
            'n_places': 20,
            'additional_information': 'whatever',
            'speakers': [self.speaker1.id],
            'save': "Save",
        }
        # Fail with date in the past
        response = self.client.post("/core/visit_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("You can&#x27;t set a date in the past", response.content.decode('utf-8'))

        # Invalid date (not between period dates)
        date = self.today + datetime.timedelta(days=60)
        data["date"] = date.strftime("%Y-%m-%d")
        response = self.client.post("/core/visit_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No available period found for slot date &#x27;%s&#x27;, please create one first" % date.strftime("%Y-%m-%d"),
            response.content.decode('utf-8')
        )

        # With a valid date, but speakers are still missing
        data["date"] = (self.today + datetime.timedelta(days=6)).strftime("%Y-%m-%d")
        del(data["speakers"])
        response = self.client.post("/core/visit_slot", data=data, follow=True)
        self.assertIn("Required fields are not filled in", response.content.decode('utf-8'))
        self.assertFalse(Slot.objects.filter(visit=visit).exists())
        self.assertEqual(response.template_name, ['core/visit_slot.html'])

        # With a speaker
        data["speakers"] = [self.speaker1.id]

        response = self.client.post("/core/visit_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ["core/visits_slots_list.html"])

        self.assertTrue(Slot.objects.filter(visit=visit).exists())
        slot = Slot.objects.get(visit=visit)
        self.assertEqual(slot.speakers.first(), self.speaker1)
        visit.refresh_from_db()
        self.assertTrue(visit.published)

        # Update
        response = self.client.get(f"/core/visit_slot/{slot.id}", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{slot.visit.establishment.id}\" selected", content)
        self.assertIn(f"value=\"{slot.visit.structure.id}\" selected", content)
        self.assertIn(f"value=\"{slot.visit.highschool.id}\" selected", content)
        self.assertIn(f"value=\"{slot.visit.id}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "id": self.speaker1.id,
            "username": self.speaker1.username,
            "lastname": self.speaker1.last_name,
            "firstname": self.speaker1.first_name,
            "email": self.speaker1.email,
            "display_name": f"{self.speaker1.last_name} {self.speaker1.first_name}",
            "is_removable": True
        }]))

        # Create an immersion, then update the slot to test mail notification
        Immersion.objects.create(
            student=self.highschool_user,
            slot=slot,
            attendance_status=1
        )

        data = {
            "visit": slot.visit.id,
            'face_to_face': False,
            'url': "http://www.whatever.com",
            'published': True,
            'date': (self.today + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            'start_time': "10:00",
            'end_time': "12:00",
            'n_places': 10,
            'additional_information': 'whatever',
            "speakers": [self.speaker1.id],
            "notify_student": "on",
            'save': "Save",
        }

        response = self.client.post(f"/core/visit_slot/{slot.id}", data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Notifications have been sent (1)", response.content.decode('utf-8'))
        self.assertEqual(response.template_name, ["core/visits_slots_list.html"])
        slot.refresh_from_db()

        self.assertEqual(slot.start_time, datetime.time(10, 0))
        self.assertEqual(slot.end_time, datetime.time(12, 0))
        self.assertEqual(slot.n_places, data["n_places"])
        self.assertFalse(slot.face_to_face)
        self.assertEqual(slot.url, data["url"])
        self.assertEqual(slot.speakers.first(), self.speaker1)


        # Duplicate a visit slot : check form values
        response = self.client.get(f"/core/visit_slot/{slot.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn(f"value=\"{slot.visit.establishment.id}\" selected>{slot.visit.establishment}<", content)
        self.assertIn(f"value=\"{slot.visit.structure.id}\" selected>{slot.visit.structure}<", content)
        self.assertIn(f"value=\"{slot.visit.highschool.id}\" selected>{slot.visit.highschool}<", content)

        # On template load, the full VisitSlot __str__ strings are displayed in the form, but we use javascript to
        # display only the 'purpose' attribute in the options fields. However, this test doesn't care about javascript.
        self.assertIn(f"value=\"{slot.visit.id}\" selected>{slot.visit}<", content)


    def test_off_offer_event(self):
        event = OffOfferEvent.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=None,
            event_type=self.event_type,
            label="Whatever",
            description="Whatever too",
            published=True
        )

        event.speakers.add(self.speaker1)

        # As a ref_master_etab user
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/off_offer_events", follow=True)
        self.assertEqual(response.status_code, 200)

        # Update
        response = self.client.get(f"/core/off_offer_event/{event.id}", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{event.establishment.id}\" selected", content)
        self.assertIn(f"value=\"{event.structure.id}\" selected", content)
        self.assertIn(f"value=\"{event.event_type.id}\" selected", content)
        self.assertIn(f"value=\"{event.label}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "username": self.speaker1.username,
            "lastname": self.speaker1.last_name,
            "firstname": self.speaker1.first_name,
            "email": self.speaker1.email,
            "display_name": f"{self.speaker1.last_name} {self.speaker1.first_name}",
            "is_removable": True
        }]))

        data = {
            "establishment": event.establishment.id,
            "structure": event.structure.id,
            "event_type": event.event_type.id,
            "published": True,
            "label": "New event label",
            "description": "Also new description",
            "speakers_list": json.dumps([{
                "email": self.speaker2.email,
                "username": self.speaker2.username,
                "lastname": self.speaker2.last_name,
                "firstname": self.speaker2.first_name,
            }])
        }

        response = self.client.post(f"/core/off_offer_event/{event.id}", data, follow=True)
        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.label, data["label"])
        self.assertEqual(event.description, data["description"])


        # Duplicate a visit : check form values
        response = self.client.get(f"/core/off_offer_event/{event.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{event.establishment.id}\" selected", content)
        self.assertIn(f"value=\"{event.structure.id}\" selected", content)
        self.assertIn(f"value=\"{event.event_type.id}\" selected", content)
        self.assertIn(f"value=\"{event.label}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "username": self.speaker2.username,
            "lastname": self.speaker2.last_name,
            "firstname": self.speaker2.first_name,
            "email": self.speaker2.email,
            "display_name": f"{self.speaker2.last_name} {self.speaker2.first_name}",
            "is_removable": True
        }]))


    def test_off_offer_event_slot(self):
        event = OffOfferEvent.objects.create(
            label="event label",
            event_type=self.event_type,
            published=False,
            establishment=self.master_establishment,
            structure=None,
        )

        event.speakers.add(self.speaker1)

        self.assertFalse(Slot.objects.filter(event=event).exists())

        # As a ref_master_etab user
        # slots list
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/off_offer_events_slots", follow=True)
        self.assertEqual(response.status_code, 200)

        # Create
        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get("/core/off_offer_event_slot", follow=True)
        self.assertEqual(response.status_code, 200)

        date = self.today + datetime.timedelta(days=60)

        data = {
            'event': event.id,
            'face_to_face': True,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': "anywhere",
            'published': True,
            'date': date.strftime("%Y-%m-%d"),
            'start_time': "12:00",
            'end_time': "14:00",
            'speakers': [self.speaker1.id],
            'n_places': 20,
            'additional_information': 'whatever',
            'save': "Save",
        }

        # Invalid date
        response = self.client.post("/core/off_offer_event_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No available period found for slot date &#x27;%s&#x27;, please create one first" % date.strftime("%Y-%m-%d"),
            response.content.decode('utf-8')
        )

        # Date in the past
        data["date"] = (self.today - datetime.timedelta(days=9)).strftime("%Y-%m-%d")
        response = self.client.post("/core/off_offer_event_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("You can&#x27;t set a date in the past", response.content.decode('utf-8'))

        # With a valid date, but speakers are still missing
        data["date"] = (self.today + datetime.timedelta(days=6)).strftime("%Y-%m-%d")
        del(data['speakers'])
        response = self.client.post("/core/off_offer_event_slot", data=data, follow=True)
        self.assertIn("Required fields are not filled in", response.content.decode('utf-8'))
        self.assertFalse(Slot.objects.filter(event=event).exists())
        self.assertEqual(response.template_name, ['core/off_offer_event_slot.html'])

        # With a speaker
        data["speakers"] = [self.speaker1.id]

        response = self.client.post("/core/off_offer_event_slot", data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ["core/off_offer_events_slots_list.html"])

        self.assertTrue(Slot.objects.filter(event=event).exists())
        slot = Slot.objects.get(event=event)
        self.assertEqual(slot.speakers.first(), self.speaker1)
        event.refresh_from_db()
        self.assertTrue(event.published)

        # Update
        response = self.client.get(f"/core/off_offer_event_slot/{slot.id}", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{slot.event.establishment.id}\" selected", content)

        #self.assertIn(f"value=\"{slot.campus.id}\" selected", content)
        #self.assertIn(f"value=\"{slot.building.id}\" selected", content)
        #self.assertIn(f"value=\"{slot.event.id}\"", content)

        self.assertEqual(response.context["speakers"], json.dumps([{
            "id": self.speaker1.id,
            "username": self.speaker1.username,
            "lastname": self.speaker1.last_name,
            "firstname": self.speaker1.first_name,
            "email": self.speaker1.email,
            "display_name": f"{self.speaker1.last_name} {self.speaker1.first_name}",
            "is_removable": True
        }]))

        # Create an immersion, then update the slot to test mail notification
        Immersion.objects.create(
            student=self.highschool_user,
            slot=slot,
            attendance_status=1
        )

        data = {
            "event": event.id,
            'face_to_face': False,
            'url': "http://www.whatever.com",
            'published': True,
            'date': (self.today + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            'start_time': "10:00",
            'end_time': "12:00",
            'n_places': 10,
            'additional_information': 'whatever',
            "speakers": [self.speaker1.id],
            "notify_student": "on",
            'save': "Save",
        }

        response = self.client.post(f"/core/off_offer_event_slot/{slot.id}", data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Notifications have been sent (1)", response.content.decode('utf-8'))
        self.assertEqual(response.template_name, ["core/off_offer_events_slots_list.html"])
        slot.refresh_from_db()

        self.assertEqual(slot.start_time, datetime.time(10, 0))
        self.assertEqual(slot.end_time, datetime.time(12, 0))
        self.assertEqual(slot.n_places, data["n_places"])
        self.assertFalse(slot.face_to_face)
        self.assertEqual(slot.url, data["url"])
        self.assertEqual(slot.speakers.first(), self.speaker1)

        # Duplicate an event slot : check form values
        response = self.client.get(f"/core/off_offer_event_slot/{slot.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(f"value=\"{slot.event.establishment.id}\" selected>{slot.event.establishment}<", content)
        self.assertIn(f"value=\"{slot.event.id}\" selected>{slot.event}<", content)

        # Update event data and test again
        event.structure = self.structure
        event.save()
        slot.event = event
        slot.save()
        response = self.client.get(f"/core/off_offer_event_slot/{slot.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn(f"value=\"{slot.event.establishment.id}\" selected>{slot.event.establishment}<", content)
        self.assertIn(f"value=\"{slot.event.structure.id}\" selected>{slot.event.structure}<", content)
        self.assertIn(f"value=\"{slot.event.id}\" selected>{slot.event}<", content)

        # With a highschool
        event.highschool = self.high_school
        event.establishment = None
        event.structure = None
        event.save()

        slot.event = event
        slot.campus = None
        slot.building = None
        slot.save()


        response = self.client.get(f"/core/off_offer_event_slot/{slot.id}/1", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn(f"value=\"{slot.event.highschool_id}\" selected>{slot.event.highschool}<", content)
        self.assertIn(f"value=\"{slot.event.id}\" selected>{slot.event}<", content)
