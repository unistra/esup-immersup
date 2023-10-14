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
    BachelorType, Structure, TrainingDomain, TrainingSubdomain,
    Training, Course, Building, CourseType, Slot, Campus,
    HighSchool, HighSchoolLevel, PostBachelorLevel, StudentLevel,
    Establishment, HigherEducationInstitution
)
from immersionlyceens.apps.immersion.forms import HighSchoolStudentRecordManagerForm
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

class MockRequest:
    pass

request_factory = RequestFactory()
request = request_factory.get('/admin')


class FormTestCase(TestCase):
    """
    Slot forms tests class
    """

    fixtures = ['group', 'high_school_levels', 'student_levels', 'post_bachelor_levels', 'higher']

    @classmethod
    def setUpTestData(cls):
        cls.establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first()
        )

        cls.high_school = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            signed_charter=True, )

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )
        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            establishment=cls.establishment,
        )
        cls.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='lycref-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
            highschool=cls.high_school,
        )
        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='ref_etab@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=cls.establishment,
        )

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)

        cls.today = datetime.datetime.today()
        cls.structure = Structure.objects.create(label="test structure", establishment=cls.establishment)
        cls.t_domain = TrainingDomain.objects.create(label="test t_domain")
        cls.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=cls.t_domain)
        cls.training = Training.objects.create(label="test training")
        cls.training2 = Training.objects.create(label="test training 2")
        cls.training.training_subdomains.add(cls.t_sub_domain)
        cls.training2.training_subdomains.add(cls.t_sub_domain)
        cls.training.structures.add(cls.structure)
        cls.training2.structures.add(cls.structure)
        cls.course = Course.objects.create(label="course 1", training=cls.training, structure=cls.structure)
        cls.course.speakers.add(cls.speaker1)
        cls.campus = Campus.objects.create(label='Esplanade')
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')
        cls.slot = Slot.objects.create(
            course=cls.course, 
            course_type=cls.course_type, 
            campus=cls.campus,
            building=cls.building, 
            room='room 1', date=cls.today,
            start_time=datetime.time(12, 0), 
            end_time=datetime.time(14, 0), 
            n_places=20
        )
        cls.slot.speakers.add(cls.speaker1)

        cls.hs_record = HighSchoolStudentRecord.objects.create(
            student=cls.highschool_user,
            highschool=cls.high_school,
            birth_date=datetime.datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=1),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe'
        )


    def setUp(self):
        """
        SetUp for Admin Forms tests
        """
        self.client = Client()
        self.client.login(username='ref_etab', password='pass')
        

    def test_HighSchoolStudentRecordManagerForm(self):
        """
        Test High school student record manager form
        """
        data = {
            'highschool': self.high_school,
            'birth_date': self.today,
            'level': 1,
            'class_name': 'Hello world ! :D',
            'student': self.highschool_user.id
        }
        form = HighSchoolStudentRecordManagerForm(data=data, instance=self.hs_record)
        self.assertTrue(form.is_valid())