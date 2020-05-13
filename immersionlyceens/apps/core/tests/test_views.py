"""
Immersion app forms tests
"""
import datetime

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, Client

from ..models import (
    Component, TrainingDomain, TrainingSubdomain, Training, Course, Building, CourseType, Slot, Campus,
    HighSchool, Calendar, UniversityYear, ImmersionUser, GeneralBachelorTeaching, BachelorMention,
    Immersion, Holiday
)
from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord

request_factory = RequestFactory()
request = request_factory.get('/admin')

class CoreViewsTestCase(TestCase):
    fixtures = ['group', 'generalsettings', 'mailtemplatevars', 'mailtemplate', 'images']

    def setUp(self):
        """
        SetUp for Core app tests
        @TODO : this is a copy/paste from immersion app setup, it may need to be cleaned a little
        """
        self.highschool_user = get_user_model().objects.create_user(
            username='@EXTERNAL@_hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string='whatever',
        )

        self.highschool_user.set_password('pass')
        self.highschool_user.save()

        # Set a second high school student for duplicates search
        self.highschool_user2 = get_user_model().objects.create_user(
            username='@EXTERNAL@_hs2',
            password='pass',
            email='hs2@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string=None,
        )

        self.highschool_user2.set_password('pass')
        self.highschool_user2.save()

        self.student_user = get_user_model().objects.create_user(
            username='test@student.fr',
            password='pass',
            email='test@student.fr',
            first_name='student',
            last_name='user'
        )

        self.student_user.set_password('pass')
        self.student_user.save()

        self.teacher1 = get_user_model().objects.create_user(
            username='teacher1',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='teach',
            last_name='HER',
        )
        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='lycref@no-reply.com',
            first_name='lyc',
            last_name='REF',
        )
        self.scuio_user = get_user_model().objects.create_user(
            username='scuio',
            password='pass',
            email='immersion@no-reply.com',
            first_name='scuio',
            last_name='scuio',
        )

        self.scuio_user.set_password('pass')
        self.scuio_user.save()

        self.component = Component.objects.create(code='C1', label="test component")
        self.component2 = Component.objects.create(code='C2', label="Second test component")

        self.ref_cmp_user = get_user_model().objects.create_user(
            username='refcmp',
            password='pass',
            email='immersion@no-reply.com',
            first_name='refcmp',
            last_name='refcmp',
        )

        self.ref_cmp_user.components.add(self.component)
        self.ref_cmp_user.set_password('pass')
        self.ref_cmp_user.save()

        self.client = Client()

        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user2)
        Group.objects.get(name='ETU').user_set.add(self.student_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)
        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_cmp_user)

        BachelorMention.objects.create(
            label="Sciences et technologies du management et de la gestion (STMG)",
            active=True
        )

        GeneralBachelorTeaching.objects.create(label="Maths", active=True)

        self.today = datetime.datetime.today()
        self.t_domain = TrainingDomain.objects.create(label="test t_domain")
        self.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=self.t_domain)
        self.training = Training.objects.create(label="test training")
        self.training2 = Training.objects.create(label="test training 2")
        self.training.training_subdomains.add(self.t_sub_domain)
        self.training2.training_subdomains.add(self.t_sub_domain)
        self.training.components.add(self.component)
        self.training2.components.add(self.component)
        self.course = Course.objects.create(label="course 1", training=self.training, component=self.component)
        self.course.teachers.add(self.teacher1)
        self.campus = Campus.objects.create(label='Esplanade')
        self.building = Building.objects.create(label='Le portique', campus=self.campus)
        self.course_type = CourseType.objects.create(label='CM')
        self.slot = Slot.objects.create(
            course=self.course, course_type=self.course_type, campus=self.campus,
            building=self.building, room='room 1', date=self.today,
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        self.slot.teachers.add(self.teacher1),
        self.high_school = HighSchool.objects.create(
            label='HS1', address='here', department=67, city='STRASBOURG', zip_code=67000, phone_number='0123456789',
            email='a@b.c', head_teacher_name='M. A B', convention_start_date=self.today - datetime.timedelta(days=10),
            convention_end_date=self.today + datetime.timedelta(days=10))

        self.high_school2 = HighSchool.objects.create(
            label='HS2', address='here', department=67, city='STRASBOURG', zip_code=67000, phone_number='0123456789',
            email='d@e.fr', head_teacher_name='M. A B', convention_start_date=self.today - datetime.timedelta(days=10),
            convention_end_date=self.today + datetime.timedelta(days=10))
        """
        self.hs_record = HighSchoolStudentRecord.objects.create(student=self.highschool_user,
                        highschool=self.high_school, birth_date=datetime.datetime.today(), civility=1,
                        phone='0123456789', level=1, class_name='1ere S 3',
                        bachelor_type=3, professional_bachelor_mention='My spe')
        """
        self.lyc_ref.highschool = self.high_school
        self.lyc_ref.save()
        self.calendar = Calendar.objects.create(
            label='my calendar',
            calendar_mode='YEAR',
            year_start_date=self.today - datetime.timedelta(days=10),
            year_end_date=self.today + datetime.timedelta(days=10),
            year_registration_start_date=self.today + datetime.timedelta(days=2),
            year_nb_authorized_immersion=4
        )

        self.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=self.today.date() - datetime.timedelta(days=365),
            end_date=self.today.date() + datetime.timedelta(days=20),
            registration_start_date=self.today.date() - datetime.timedelta(days=1),
            active=True,
        )

        self.immersion = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.slot,
            attendance_status=1
        )

    def test_import_holidays(self):
        self.client.login(username='scuio', password='pass')
        self.assertFalse(Holiday.objects.all().exists())
        self.client.get("/admin/holiday/import", follow=True)
        self.assertTrue(Holiday.objects.all().exists())


    def test_slots(self):
        # First test simple get with no component or training parameter

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/slots/", follow=True)
        self.assertIn(self.component, response.context["components"])
        self.assertNotIn("component_id", response.context["components"])
        self.assertNotIn("train_id", response.context["components"])

        # with parameters
        response = self.client.get("/core/slots/?c=%s&t=%s" % (self.component.id, self.training.id))
        self.assertEqual(str(self.component.id), response.context["component_id"])
        self.assertEqual(str(self.training.id), response.context["training_id"])

        # As component referent
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/slots/", follow=True)
        self.assertIn(self.component, response.context["components"])
        self.assertEqual(response.context["components"].count(), 1)
        self.assertNotIn(self.component2, response.context["components"])
        self.assertNotIn("component_id", response.context["components"])
        self.assertNotIn("train_id", response.context["components"])

        # As any other user
        self.client.login(username='@EXTERNAL@_hs', password='pass')
        response = self.client.get("/core/slots/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slots/")

    def test_add_slot(self):
        # As any other user
        self.client.login(username='@EXTERNAL@_hs', password='pass')
        response = self.client.get("/core/slot/add")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slot/add")

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/slot/add", follow=True)
        self.assertIn(self.component, response.context["components"])

        data = {
            'component': self.component.id,
            'training': self.training.id,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': "212",
            'date': (self.today - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
            'start_time': "12:00",
            'end_time': "14:00",
            'teacher_%s' % self.teacher1.id: 1,
            'n_places': 33,
            'additional_information': "Here is additional data.",
            'published': "on",
            'save': 1
        }

        # Fail with date outside of calendar boundaries and missing field
        response = self.client.post("/core/slot/add", data, follow=True)
        self.assertFalse(Slot.objects.filter(room="212").exists())
        self.assertIn("Error: The date must be between the dates of the current calendar",
            response.content.decode('utf-8'))

        # Update to a valid date
        data["date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        # Fail with missing field
        del(data['teacher_%s' % self.teacher1.id])
        response = self.client.post("/core/slot/add", data, follow=True)
        self.assertFalse(Slot.objects.filter(room="212").exists())
        self.assertIn("You have to select one or more teachers", response.content.decode('utf-8'))

        # Success
        data['teacher_%s' % self.teacher1.id] = 1
        response = self.client.post("/core/slot/add", data, follow=True)

        self.assertTrue(Slot.objects.filter(room="212").exists())
        self.assertIn("Slot successfully added", response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')

        # get add_slot form with an existing slot
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/slot/add/%s" % self.slot.id, follow=True)
        self.assertEqual(response.context["slot"].course_id, self.course.id)

        # Save a slot and get back to add form
        data = {
            'component': self.component.id,
            'training': self.training.id,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': "S40",
            'date': (self.today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            'start_time': "16:00",
            'end_time': "18:00",
            'teacher_%s' % self.teacher1.id: 1,
            'n_places': 33,
            'additional_information': "Here is additional data.",
            'published': "on",
            'save_add': 1
        }

        response = self.client.post("/core/slot/add", data, follow=True)

        self.assertTrue(Slot.objects.filter(room="S40").exists())
        self.assertIn("Slot successfully added", response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slot/add')

        # Get as component referent
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/slot/add", follow=True)

        # Check that we only get the components the referent has access to
        self.assertIn(self.component, response.context["components"])
        self.assertEqual(response.context["components"].count(), 1)
        self.assertNotIn(self.component2, response.context["components"])