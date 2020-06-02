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

        self.teacher1.set_password('pass')
        self.teacher1.save()

        self.teacher2 = get_user_model().objects.create_user(
            username='teacher2',
            password='pass',
            email='teacher-immersion2@no-reply.com',
            first_name='teach2',
            last_name='HER2',
        )

        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='lycref@no-reply.com',
            first_name='lyc',
            last_name='REF',
        )

        self.lyc_ref.set_password('pass')
        self.lyc_ref.save()

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
        self.t_domain2 = TrainingDomain.objects.create(label="test t_domain 2")

        self.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=self.t_domain)
        self.t_sub_domain2 = TrainingSubdomain.objects.create(label="test t_sub_domain 2", training_domain=self.t_domain2)

        self.training = Training.objects.create(label="test training")
        self.training2 = Training.objects.create(label="test training 2")
        self.training3 = Training.objects.create(label="test training 3")

        self.training.training_subdomains.add(self.t_sub_domain)
        self.training.components.add(self.component)
        self.training2.training_subdomains.add(self.t_sub_domain)
        self.training2.components.add(self.component)
        self.training3.training_subdomains.add(self.t_sub_domain2)
        self.training3.components.add(self.component2)

        self.course = Course.objects.create(label="course 1", training=self.training, component=self.component)
        self.course.teachers.add(self.teacher1)

        self.course2 = Course.objects.create(label="course 2", training=self.training3, component=self.component2)
        self.course2.teachers.add(self.teacher2)

        self.campus = Campus.objects.create(label='Esplanade')
        self.building = Building.objects.create(label='Le portique', campus=self.campus)
        self.course_type = CourseType.objects.create(label='CM')
        self.slot = Slot.objects.create(
            course=self.course, course_type=self.course_type, campus=self.campus,
            building=self.building, room='room 1', date=self.today,
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        self.slot.teachers.add(self.teacher1),

        # Add another slot : component referent shouldn't have access to this one
        self.slot2 = Slot.objects.create(
            course=self.course2, course_type=self.course_type, campus=self.campus,
            building=self.building, room='room 12', date=self.today,
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        self.slot2.teachers.add(self.teacher2),

        self.slot3 = Slot.objects.create(
            course=self.course2, course_type=self.course_type, campus=self.campus,
            building=self.building, room='room 12', date=self.today + datetime.timedelta(days=1),
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        self.slot3.teachers.add(self.teacher2),

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

        self.assertFalse("slot" in response.context) # "Add new" form : no slot
        self.assertEqual(response.request['PATH_INFO'], '/core/slot/add')

        # Duplicate a slot : save, stay on form & keep data
        del(data["save_add"])
        data["duplicate"] = 1
        data["room"] = "S41"
        response = self.client.post("/core/slot/add", data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Slot successfully added", response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertTrue(Slot.objects.filter(room="S41").exists())
        slot = Slot.objects.get(room="S41")
        self.assertEqual(response.context["slot"].course_id, self.course.id)  # empty slot
        self.assertEqual(response.request['PATH_INFO'], '/core/slot/add/%s' % slot.id)

        # Get as component referent
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/slot/add", follow=True)

        # Check that we only get the components the referent has access to
        self.assertIn(self.component, response.context["components"])
        self.assertEqual(response.context["components"].count(), 1)
        self.assertNotIn(self.component2, response.context["components"])


    def test_modify_slot(self):
        # As any other user
        self.client.login(username='@EXTERNAL@_hs', password='pass')
        response = self.client.get("/core/slot/modify/%s" % self.slot.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/slot/modify/%s" % self.slot.id)

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')
        # Fail with a non existing slot
        response = self.client.get("/core/slot/modify/250", follow=True)
        self.assertIn("This slot id does not exist", response.content.decode('utf-8'))

        # Get an existing slot
        response = self.client.get("/core/slot/modify/%s" % self.slot.id, follow=True)
        self.assertIn(self.component, response.context["components"])

        # Get slot data and update a few fields
        data = {
            'component': self.slot.course.component.id,
            'training': self.slot.course.training.id,
            'course': self.slot.course.id,
            'course_type': self.slot.course_type.id,
            'campus': self.slot.campus.id,
            'building': self.slot.building.id,
            'room': "New room",
            'date': (self.slot.date + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            'start_time': "13:30",
            'end_time': "15:30",
            'teacher_%s' % self.teacher1.id: 1,
            'n_places': 20,
            'additional_information': "New data",
            'published': "on",
            "notify_student": "on",
            'save': 1
        }
        # Fail with missing field
        del(data['teacher_%s' % self.teacher1.id])
        response = self.client.post("/core/slot/modify/%s" % self.slot.id, data, follow=True)
        self.assertFalse(Slot.objects.filter(room="New room").exists())
        self.assertIn("You have to select one or more teachers", response.content.decode('utf-8'))

        # Success
        data['teacher_%s' % self.teacher1.id] = 1
        response = self.client.post("/core/slot/modify/%s" % self.slot.id, data, follow=True)
        slot = Slot.objects.get(pk=self.slot.id)

        # Check updated fields
        self.assertEqual(slot.room, "New room")
        self.assertEqual(slot.start_time, datetime.time(13, 30))
        self.assertEqual(slot.end_time, datetime.time(15, 30))
        self.assertEqual(slot.n_places, 20)
        self.assertEqual(slot.additional_information, "New data")
        self.assertEqual(slot.date, (self.slot.date + datetime.timedelta(days=1)).date())

        self.assertIn("Slot successfully updated", response.content.decode('utf-8'))
        self.assertIn("Course published", response.content.decode('utf-8'))
        self.assertIn("Notifications have been sent (1)", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')

        # TODO : test save_add and duplicate

        # Get as component referent
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/slot/modify/%s" % self.slot.id, follow=True)

        # Check that we only get the components the referent has access to
        self.assertIn(self.component, response.context["components"])
        self.assertEqual(response.context["components"].count(), 1)
        self.assertNotIn(self.component2, response.context["components"])

        # Test with a slot the user doesn't have access to
        response = self.client.get("/core/slot/modify/%s" % self.slot2.id)
        self.assertTrue(response.status_code, 302)
        self.assertTrue(response.url, "/core/slots")

        response = self.client.get("/core/slot/modify/%s" % self.slot2.id, follow=True)
        self.assertTrue(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/core/slots/')
        self.assertIn("This slot belongs to another component", response.content.decode('utf-8'))

    def test_delete_slot(self):
        self.assertTrue(Slot.objects.filter(pk=self.slot.id).exists())

        # As component referent, test with a slot the user doesn't have access to
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/slot/delete/%s" % self.slot2.id, follow=True)
        self.assertEqual(response.content.decode('utf-8'), "This slot belongs to another component")
        self.assertTrue(Slot.objects.filter(pk=self.slot.id).exists())

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/slot/delete/%s" % self.slot.id, follow=True)
        self.assertEqual(response.content.decode('utf-8'), "ok")
        self.assertFalse(Slot.objects.filter(pk=self.slot.id).exists())

        # Non existing slot
        response = self.client.get("/core/slot/delete/123", follow=True)
        self.assertEqual(response.content.decode('utf-8'), "ok")
        self.assertFalse(Slot.objects.filter(pk=self.slot.id).exists())


    def test_courses_list(self):
        # As any other user
        self.client.login(username='@EXTERNAL@_hs', password='pass')
        response = self.client.get("/core/courses_list")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/courses_list")

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')

        # with invalid year dates
        self.university_year.start_date = self.today.date() + datetime.timedelta(days=1)
        self.university_year.save()

        response = self.client.get("/core/courses_list")
        self.assertIn(self.component, response.context["components"])
        self.assertEqual(None, response.context["component_id"])
        self.assertFalse(response.context["can_update_courses"])
        self.assertIn("Courses cannot be created, updated or deleted", response.content.decode('utf-8'))

        # With valid dates
        response = self.client.get("/core/courses_list")
        self.university_year.start_date = self.today.date() - datetime.timedelta(days=365)
        self.university_year.save()
        response = self.client.get("/core/courses_list")
        self.assertTrue(response.context["can_update_courses"])

        # As component referent
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/courses_list")
        self.assertIn(self.component, response.context["components"])
        self.assertNotIn(self.component2, response.context["components"])
        self.assertEqual(self.component.id, response.context["component_id"])
        self.assertTrue(response.context["can_update_courses"])


    def test_course(self):
        # As any other user
        self.client.login(username='@EXTERNAL@_hs', password='pass')
        response = self.client.get("/core/course")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=/core/course")

        # As scuio-ip user
        self.client.login(username='scuio', password='pass')

        # with invalid year dates
        self.university_year.start_date = self.today.date() + datetime.timedelta(days=1)
        self.university_year.save()

        response = self.client.get("/core/course")
        self.assertFalse(response.context["can_update_courses"])
        self.assertIn("Courses cannot be created, updated or deleted", response.content.decode('utf-8'))

        # With valid dates
        response = self.client.get("/core/course")
        self.university_year.start_date = self.today.date() - datetime.timedelta(days=365)
        self.university_year.save()
        response = self.client.get("/core/course")
        self.assertTrue(response.context["can_update_courses"])

        # Try to access a non-existing course
        response = self.client.get("/core/course/123456")
        self.assertIn("Create a new course", response.content.decode('utf-8'))

        # Post data to create a new course
        data = {
            'component': self.component.id,
            'training': self.training.id,
            'label': "New test course",
            'url': "http://new-course.test.fr",
            'published': True,
            'teachers_list':"",
            'save': 1
        }
        # Fail with missing field
        response = self.client.post("/core/course", data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertIn("At least one teacher is required", response.content.decode('utf-8'))

        data['teachers_list'] = \
            """[{"username":"jean", "firstname":"Jean", "lastname":"Jacques", "email":"jean-jacques@domain.fr"},
                {"username":"john", "firstname":"John", "lastname":"Jack", "email":"john.jack@domain.fr"}]"""

        # Fail with invalid URL format
        data['url'] = "whatever"
        response = self.client.post("/core/course", data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertIn("Enter a valid URL.", response.content.decode('utf-8'))

        data['url'] = "http://new-course.test.fr"

        # Success
        response = self.client.post("/core/course", data, follow=True)
        # Course and teachers must exist
        self.assertTrue(Course.objects.filter(label="New test course").exists())

        course = Course.objects.get(label="New test course")
        self.assertTrue(ImmersionUser.objects.filter(username='jean').exists())
        self.assertTrue(ImmersionUser.objects.filter(username='john').exists())
        self.assertEqual(course.teachers.count(), 2)
        self.assertIn("A confirmation email has been sent to jean-jacques@domain.fr", response.content.decode('utf-8'))
        self.assertIn("A confirmation email has been sent to john.jack@domain.fr", response.content.decode('utf-8'))

        # Course update
        response = self.client.get("/core/course/%s" % course.id, data, follow=True)
        self.assertIn("New test course", response.content.decode('utf-8'))

        data["label"] = "This is my new label"
        data["teachers_list"] = \
            """[{"username":"jean", "firstname":"Jean", "lastname":"Jacques", "email":"jean-jacques@domain.fr"}]"""
        response = self.client.post("/core/course/%s" % course.id, data, follow=True)
        self.assertFalse(Course.objects.filter(label="New test course").exists())
        self.assertTrue(Course.objects.filter(label="This is my new label").exists())
        self.assertIn("Course successfully updated", response.content.decode('utf-8'))
        course = Course.objects.get(label="This is my new label")
        self.assertEqual(course.teachers.count(), 1)

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
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/course/%s" % self.course2.id, follow=True)
        self.assertIn("You don't have enough privileges to update this course", response.content.decode("utf-8"))
        data["label"] = "This shouldn't happen"
        response = self.client.post("/core/course/%s" % self.course2.id, data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/courses_list')
        self.assertFalse(Course.objects.filter(label="This shouldn't happen").exists())

    def test_mycourses(self):
        self.client.login(username='teacher1', password='pass')
        response = self.client.get("/core/mycourses", follow=True)
        self.assertIn("Courses - HER teach", response.content.decode('utf-8'))

    def test_myslots(self):
        self.client.login(username='teacher1', password='pass')
        response = self.client.get("/core/myslots/", follow=True)
        self.assertIn("Slots - HER teach", response.content.decode('utf-8'))

    def test_myhighschool(self):
        self.client.login(username='lycref', password='pass')
        # Shouldn't work (no access)
        response = self.client.get("/core/high_school/%s" % self.high_school2.id, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')

        # Should work
        response = self.client.get("/core/high_school/%s" % self.high_school.id, follow=True)
        self.assertIn("My high school - %s" % self.high_school.label, response.content.decode('utf-8'))

        # Update
        data = {
            'address': "12 rue des Plantes",
            'address2': "test_line_2",
            'address3': "test_line_3",
            'department': 68,
            'city': "MULHOUSE",
            'zip_code': '68100',
            'phone_number': '0388888888',
            'email': 'lycee@domain.fr',
            'head_teacher_name': 'Headmaster'
        }

        response = self.client.post("/core/high_school/%s" % self.high_school.id, data, follow=True)
        self.assertTrue(HighSchool.objects.filter(address='12 rue des Plantes'))

    def test_my_students(self):
        # As high school referent
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/my_students", follow=True)

        self.assertIn('highschool', response.context)
        self.assertEqual(response.context['highschool'], self.high_school)
        self.assertFalse(response.context['is_scuio_ip_manager'])

        # As a scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/my_students", follow=True)

        self.assertIn('highschool', response.context)
        self.assertEqual(response.context['highschool'], None)
        self.assertTrue(response.context['is_scuio_ip_manager'])


    def test_student_validation(self):
        # As a scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/student_validation/", follow=True)
        self.assertNotIn('high_school', response.context)
        self.assertIn(self.high_school, response.context['high_schools'])
        self.assertIn(self.high_school2, response.context['high_schools'])

        response = self.client.get("/core/student_validation/%s" % self.high_school.id, follow=True)
        self.assertIn('high_school', response.context)
        self.assertEqual(response.context['high_school'], self.high_school)
        self.assertNotIn('high_schools', response.context)

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
            birth_date=datetime.datetime.today(), civility=1,
            phone='0123456789', level=1, class_name='1ere S 3',
            bachelor_type=3, professional_bachelor_mention='My spe')

        hs_record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school2,
            birth_date=datetime.datetime.today(), civility=1,
            phone='0123456789', level=1, class_name='1ere T3',
            bachelor_type=3, professional_bachelor_mention='My spe')

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
            'level': '2',
            'class_name': 'TS 3'
        }
        response = self.client.post("/core/hs_record_manager/%s" % hs_record.id, data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')

        highschool_user = ImmersionUser.objects.get(id=self.highschool_user.id)
        hs_record = HighSchoolStudentRecord.objects.get(id=hs_record.id)

        self.assertEqual(highschool_user.first_name, 'Jean')
        self.assertEqual(highschool_user.last_name, 'Jacques')
        self.assertEqual(hs_record.level, 2)
        self.assertEqual(hs_record.class_name, 'TS 3')

        # Missing field
        data.pop('class_name')
        response = self.client.post("/core/hs_record_manager/%s" % hs_record.id, data, follow=True)
        self.assertIn("High school student record modification failure", response.content.decode('utf-8'))

        # Student belonging to another high school
        response = self.client.get("/core/hs_record_manager/%s" % hs_record2.id, follow=True)
        self.assertIn("This student is not bound to your high school", response.content.decode('utf-8'))
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')

        # Non existing record id
        response = self.client.get("/core/hs_record_manager/999", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/core/student_validation/')



    def test_component(self):
        # As a refcmp user
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/component", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.component, response.context['component'])
        self.assertEqual(response.context['components'], None)

        # Post a new mailing list URL
        self.assertEqual(self.component.mailing_list, None)
        data = {
            "code" : self.component.code,
            "mailing_list": "new_mailing_list@mydomain.com",
            "submit": 1
        }
        response = self.client.post("/core/component/%s" % self.component.code, data, follow=True)

        self.assertEqual(response.request['PATH_INFO'], '/core/component')
        component = Component.objects.get(code='C1')
        self.assertEqual(component.mailing_list, 'new_mailing_list@mydomain.com')

        # As any other user, first check redirection code, then redirection url
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/component")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/core/component", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')


    def test_stats(self):
        # As a scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/stats/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.component2, response.context['components'])
        self.assertNotIn('high_school_id', response.context)

        # As a ref-cmp user
        self.client.login(username='refcmp', password='pass')
        response = self.client.get("/core/stats/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.component2, response.context['components'])
        self.assertNotIn('high_school_id', response.context)

        # As ref-lyc user
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/stats/", follow=True)
        self.assertIn('high_school_id', response.context)
        self.assertEqual(response.context['high_school_id'], self.high_school.id)


    def test_students_presence(self):
        # As a scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/students_presence", follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['min_date'], self.today.strftime("%Y-%m-%d"))
        self.assertEqual(response.context['max_date'], (self.today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))


    def test_duplicated_accounts(self):
        # As a scuio-ip user
        self.client.login(username='scuio', password='pass')
        response = self.client.get("/core/duplicates", follow=True)
        self.assertEqual(response.status_code, 200)

        # As any other user, first check redirection code, then redirection url
        self.client.login(username='lycref', password='pass')
        response = self.client.get("/core/duplicates")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/core/duplicates", follow=True)
        self.assertEqual(response.request['PATH_INFO'], '/')


