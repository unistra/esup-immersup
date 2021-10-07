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
    HighSchool, Calendar
)
from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


class MockRequest:
    pass


# request = MockRequest()


request_factory = RequestFactory()
request = request_factory.get('/admin')


class FormTestCase(TestCase):
    """
    Slot forms tests class
    """

    fixtures = ['group']

    def setUp(self):
        """
        SetUp for Admin Forms tests
        """
        self.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )
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
        self.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='immersion@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
        )

        self.client = Client()
        self.client.login(username='ref_etab', password='pass')

        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

        self.today = datetime.datetime.today()
        self.structure = Component.objects.create(label="test structure")
        self.t_domain = TrainingDomain.objects.create(label="test t_domain")
        self.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=self.t_domain)
        self.training = Training.objects.create(label="test training")
        self.training2 = Training.objects.create(label="test training 2")
        self.training.training_subdomains.add(self.t_sub_domain)
        self.training2.training_subdomains.add(self.t_sub_domain)
        self.training.components.add(self.structure)
        self.training2.components.add(self.structure)
        self.course = Course.objects.create(label="course 1", training=self.training, component=self.structure)
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
        self.calendar = Calendar.objects.create(label='my calendar', calendar_mode='YEAR',
                        year_start_date=self.today + datetime.timedelta(days=1),
                        year_end_date=self.today + datetime.timedelta(days=100),
                        year_registration_start_date=self.today + datetime.timedelta(days=2),
                        year_nb_authorized_immersion=4
                        )

    def test_HighSchoolStudentRecordManagerForm(self):
        """
        Test Evaluation form link creation
        """
        data = {
            'highschool': self.high_school,
            'birth_date': self.today,
            'level': 1,
            'class_name': 'Hello world ! :D',
            'student': self.high_school.id
        }
        form = HighSchoolStudentRecordManagerForm(data=data, instance=self.hs_record)
        # print(form.is_valid())
        # print(form.errors)

        self.assertTrue(form.is_valid())