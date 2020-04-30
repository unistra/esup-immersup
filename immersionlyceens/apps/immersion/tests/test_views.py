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

from immersionlyceens.apps.core.models import (
    Component, TrainingDomain, TrainingSubdomain, Training, Course, Building, CourseType, Slot, Campus,
    HighSchool, Calendar, UniversityYear, ImmersionUser
)
from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


class MockRequest:
    pass


# request = MockRequest()


request_factory = RequestFactory()
request = request_factory.get('/admin')


class ImmersionViewsTestCase(TestCase):
    """
    Immersion app views tests
    """

    fixtures = ['group']

    def setUp(self):
        """
        SetUp for Admin Forms tests
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
            email='teacher-immersion@no-reply.com',
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

        self.client = Client()

        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

        self.today = datetime.datetime.today()
        self.component = Component.objects.create(label="test component")
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
        self.high_school = HighSchool.objects.create(label='HS1', address='here',
                         department=67, city='STRASBOURG', zip_code=67000, phone_number='0123456789',
                         email='a@b.c', head_teacher_name='M. A B')
        self.hs_record = HighSchoolStudentRecord.objects.create(student=self.highschool_user,
                        highschool=self.high_school, birth_date=datetime.datetime.today(), civility=1,
                        phone='0123456789', level=1, class_name='1ere S 3',
                        bachelor_type=3, professional_bachelor_mention='My spe')
        self.lyc_ref.highschool = self.high_school
        self.lyc_ref.save()
        self.calendar = Calendar.objects.create(
            label='my calendar',
            calendar_mode='YEAR',
            year_start_date=self.today + datetime.timedelta(days=1),
            year_end_date=self.today + datetime.timedelta(days=100),
            year_registration_start_date=self.today + datetime.timedelta(days=2),
            year_nb_authorized_immersion=4
        )

        self.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=self.today.date() - datetime.timedelta(days=10),
            end_date=self.today.date() + datetime.timedelta(days=20),
            registration_start_date=self.today.date() - datetime.timedelta(days=1),
            active=True,
        )

    def test_login(self):
        self.university_year.start_date = self.today.date() + datetime.timedelta(days=10)
        self.university_year.save()

        # This will fail (year not valid yet)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("""Sorry, the university year has not begun (or already over), you can't login yet.""",
            response.content.decode('utf-8'))

        self.university_year.start_date = self.today.date() - datetime.timedelta(days=10)
        self.university_year.save()

        # This will fail (authentication error)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'wrong_pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Authentication error", response.content.decode('utf-8'))

        # This will fail (account not validated yet)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Your account hasn't been enabled yet.", response.content.decode('utf-8'))

        # Validate account then retry
        self.highschool_user.validation_string = None
        self.highschool_user.save()

        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/immersion")

    """
    def test_shibboleth_login(self):
        # Fail with missing attribute
        header = {
            'HTTP_GIVENNAME': 'student',
            'HTTP_SN': 'user',
            'HTTP_REMOTE_USER': 'test',
            'HTTP_MAIL': 'test@student.fr',
        }
        response = self.client.get('/shib/', request, **header)
        self.assertIn("Êtes-vous sûr(e) de vouloir créer votre compte ?", response.content.decode('utf-8'))

        # All attributes
        header = {
            'HTTP_GIVENNAME': 'student',
            'HTTP_SN': 'user',
            'HTTP_REMOTE_USER': 'test',
            'HTTP_MAIL': 'test@student.fr',
            'HTTP_SUPANNETABLISSEMENT': '{UAI}0673021V'
        }

        response = self.client.get('/shib/', request, **header)
        self.assertIn("Êtes-vous sûr(e) de vouloir créer votre compte ?", response.content.decode('utf-8'))
    """

    def test_register(self):
        data = {
            'first_name': 'prenom',
            'last_name': 'nom',
            'email': 'mon_email@mondomaine.fr',
            'password1': 'passw',
            'password2': 'passw_2',
        }

        # Will fail (passwords don't match, missing email2)
        response = self.client.post('/immersion/register', data)

        self.assertIn("The two password fields didn't match.", response.content.decode('utf-8'))
        self.assertIn("This field is required.", response.content.decode('utf-8'))
        self.assertIn("Error : emails don't match", response.content.decode('utf-8'))

        # Will fail (password too short)
        data['email2'] = "mon_email@mondomaine.fr"
        data['password2'] = "passw"
        response = self.client.post('/immersion/register', data)

        self.assertIn("This password is too short. It must contain at least 8 characters.",
            response.content.decode('utf-8'))

        # Should succeed and redirect
        data['password1'] = "Is this password long enough ?"
        data['password2'] = "Is this password long enough ?"

        response = self.client.post('/immersion/register', data, follow=True)
        self.assertIn("Account created. Please look at your emails for the activation procedure.",
            response.content.decode('utf-8'))

        # Check some attributes
        new_account = ImmersionUser.objects.get(username="@EXTERNAL@_mon_email@mondomaine.fr")
        self.assertNotEqual(new_account.validation_string, None)
        self.assertNotEqual(new_account.destruction_date, None)
        self.assertIsInstance(new_account.destruction_date, datetime.date)
        self.assertFalse(new_account.is_valid())

        lyc_group = Group.objects.get(name='LYC')
        self.assertIn(lyc_group, new_account.groups.all())

    def test_recovery(self):
        # Fail : not a highschool user
        response = self.client.post('/immersion/recovery', {'email': 'test@student.fr'})
        self.assertIn("Please use your establishment credentials.", response.content.decode('utf-8'))

        # Fail : email not found
        response = self.client.post('/immersion/recovery', {'email': 'test@domaine.fr'})
        self.assertIn("No account found with this email address", response.content.decode('utf-8'))

        # Success
        response = self.client.post('/immersion/recovery', {'email': 'hs@no-reply.com'})
        self.assertIn("An email has been sent with the procedure to set a new password.", response.content.decode('utf-8'))

        user = ImmersionUser.objects.get(username="@EXTERNAL@_hs")
        self.assertNotEqual(user.recovery_string, None)

        # print(response.content.decode('utf-8'))
