"""
Django Admin Forms tests suite
"""
import datetime

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from ..admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm, CampusForm,
    CancelTypeForm, ComponentForm, CourseTypeForm, GeneralBachelorTeachingForm, HighSchoolForm,
    HolidayForm, PublicDocumentForm, PublicTypeForm, TrainingDomainForm, TrainingSubdomainForm,
    UniversityYearForm, VacationForm,
)
from ..models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus, CancelType, Component,
    CourseType, GeneralBachelorTeaching, HighSchool, Holiday, PublicDocument, PublicType,
    TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)


class MockRequest:
    pass


# request = MockRequest()


request_factory = RequestFactory()
request = request_factory.get('/admin')


class AdminFormsTestCase(TestCase):
    """
    Main admin forms tests class
    """

    fixtures = ['group']

    def setUp(self):
        """
        SetUp for Admin Forms tests
        """

        self.site = AdminSite()
        self.superuser = get_user_model().objects.create_superuser(
            username='super', password='pass', email='immersion@no-reply.com'
        )

        self.scuio_user = get_user_model().objects.create_user(
            username='cmp',
            password='pass',
            email='immersion@no-reply.com',
            first_name='cmp',
            last_name='cmp',
        )

        self.ref_cmp_user = get_user_model().objects.create_user(
            username='ref_cmp',
            password='pass',
            email='immersion@no-reply.com',
            first_name='ref_cmp',
            last_name='ref_cmp',
        )

        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_cmp_user)

    def test_training_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        data = {'label': 'test', 'active': True}

        request.user = self.scuio_user

        form = TrainingDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = TrainingDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(TrainingDomain.objects.filter(label='test_fail').exists())

    def test_training_sub_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        domain_data = {'label': 'test', 'active': True}
        td = TrainingDomain.objects.create(**domain_data)

        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

        data = {'label': 'sd test', 'training_domain': td.pk, 'active': True}

        request.user = self.scuio_user

        form = TrainingSubdomainForm(data=data, request=request)

        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingSubdomain.objects.filter(label='sd test').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'training_domain': td, 'active': True}
        request.user = self.ref_cmp_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(TrainingSubdomain.objects.filter(label='test_fail').exists())

    def test_campus_creation(self):
        """
        Test admin Campus creation with group rights
        """

        data = {'label': 'testCampus', 'active': True}

        request.user = self.scuio_user

        form = CampusForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Campus.objects.filter(label='testCampus').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = CampusForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Campus.objects.filter(label='test_fail').exists())

    def test_building_creation(self):
        """
        Test admin Campus creation with group rights
        """

        testCampus = Campus.objects.create(label='testCampus', active=True)
        data = {
            'label': 'testBuilding',
            'campus': testCampus.pk,
            'url': 'https://www.building.com',
            'active': True,
        }

        request.user = self.scuio_user

        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label='testBuilding').exists())

        # Validation fail (invalid user)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_cmp_user
        form = BuildingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Building.objects.filter(label='test_fail').exists())

    def test_component_creation(self):
        """
        Test admin Component creation with group rights
        """
        data = {'code': 'AB123', 'label': 'test', 'url': 'http://url.fr', 'active': True}

        request.user = self.scuio_user

        form = ComponentForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Component.objects.filter(label='test').exists())

        # Validation fail (code unicity)
        data["label"] = "test_fail"
        form = ComponentForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        request.user = self.ref_cmp_user
        form = ComponentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertEqual(Component.objects.count(), 1)

    def test_training_creation(self):
        """
        Test admin Training creation with group rights
        """
        training_domain_data = {'label': 'domain', 'active': True}
        training_subdomain_data = {'label': 'subdomain', 'active': True}
        component_data = {'code': 'AB123', 'label': 'test', 'url': 'http://url.fr', 'active': True}

        training_domain = TrainingDomain.objects.create(**training_domain_data)
        training_subdomain = TrainingSubdomain.objects.create(
            training_domain=training_domain, **training_subdomain_data
        )
        component = Component.objects.create(**component_data)

        self.assertTrue(TrainingDomain.objects.all().exists())
        self.assertTrue(TrainingSubdomain.objects.all().exists())
        self.assertTrue(Component.objects.all().exists())

        data = {
            'label': 'test',
            'url': 'http://url.fr',
            'components': [component.pk,],
            'training_subdomains': [training_subdomain.pk,],
        }

    def test_bachelor_mention_creation(self):
        """
        Test admin bachelor mention creation with group rights
        """

        data = {'label': 'testBachelor', 'active': True}

        request.user = self.scuio_user

        form = BachelorMentionForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(BachelorMention.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = BachelorMentionForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(BachelorMention.objects.filter(label='test_failure').exists())

    def test_cancel_type_creation(self):
        """
        Test admin bachelor mention creation with group rights
        """

        data = {'label': 'testBachelor', 'active': True}

        request.user = self.scuio_user

        form = CancelTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CancelType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = CancelTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CancelType.objects.filter(label='test_failure').exists())

    def test_course_type_creation(self):
        """
        Test course type creation with group rights
        """
        data = {'label': 'testCourse', 'active': True}

        request.user = self.scuio_user

        form = CourseTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = CourseTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(CourseType.objects.filter(label='test_failure').exists())

    def test_general_bachelor_teaching_creation(self):
        """
        Test general bachelor specialty teaching creation with group rights
        """
        data = {'label': 'test', 'active': True}

        request.user = self.scuio_user

        form = GeneralBachelorTeachingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(GeneralBachelorTeaching.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = GeneralBachelorTeachingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(GeneralBachelorTeaching.objects.filter(label='test_failure').exists())

    def test_public_type_creation(self):
        """
        Test public type mention creation with group rights
        """
        data = {'label': 'testCourse', 'active': True}

        request.user = self.scuio_user

        form = PublicTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicType.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = PublicTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(PublicType.objects.filter(label='test_fail').exists())

    def test_university_year_creation(self):
        """
        Test public type mention creation with group rights
        """
        data = {
            'label': 'university_year',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'registration_start_date': datetime.datetime.today().date()+ datetime.timedelta(days=3),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }

        request.user = self.scuio_user

        form = UniversityYearForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(UniversityYear.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data = {
            'label': 'test_failure',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'registration_start_date': datetime.datetime.today().date(),
        }
        request.user = self.ref_cmp_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(UniversityYear.objects.filter(label='test_fail').exists())

    def test_university_year_constraint__fail_before_now(self):
        request.user = self.scuio_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=3),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.scuio_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_university_year_constraint__fail_start_greater_end(self):
        request.user = self.scuio_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=9),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.scuio_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_university_year_constraint__fail_registrtion_before_start(self):
        request.user = self.scuio_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.scuio_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_university_year_constraint__fail_registrtion_after_end(self):
        request.user = self.scuio_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=20),
        }
        request.user = self.scuio_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_highschool_creation(self):
        """
        Test admin HighSchool creation with group rights
        """

        data = {
            'label': ' Santo Domingo',
            'address': 'rue larry Kubiac',
            'address2': '',
            'address3': '',
            'department': '68',
            'city': 'MULHOUSE',
            'zip_code': '68100',
            'phone_number': '+3312345678',
            'fax': '+3397654321',
            'email': 'santodomingo@santodomingo.edu',
            'head_teacher_name': 'Madame Musso Grace',
            'referent_name': 'Franck Lemmer',
            'referent_phone_number': '+30102030',
            'referent_email': 'franck.lemmer@caramail.com',
            'convention_start_date': datetime.datetime.today().date(),
            'convention_end_date': '',
        }

        request.user = self.scuio_user

        form = HighSchoolForm(data=data, request=request)
        # Need to populate choices fields (ajax populated IRL)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(HighSchool.objects.filter(label='Santo Domingo').exists())

        # Validation fail (invalid user)
        data = {
            'label': 'Degrassi Junior School',
            'address': 'rue Joey Jeremiah',
            'address2': '',
            'address3': '',
            'department': '68',
            'city': 'MULHOUSE',
            'zip_code': '68100',
            'phone_number': '+3312345678',
            'fax': '+3397654321',
            'email': 'degrassi@degrassi.edu',
            'head_teacher_name': 'M. Daniel Raditch',
            'referent_name': 'Spike Nelson',
            'referent_phone_number': '+30102030',
            'referent_email': 'spike@caramail.com',
            'convention_start_date': datetime.datetime.today().date(),
            'convention_end_date': '',
        }
        request.user = self.ref_cmp_user
        form = HighSchoolForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(HighSchool.objects.filter(label='Degrassi Junior School').exists())

    def test_holiday_creation(self):
        """
        Test public type mention creation with group rights
        """
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        ).save()

        data = {
            'label': 'Holiday',
            'date': datetime.datetime.today().date() + datetime.timedelta(days=2),
        }

        request.user = self.scuio_user

        form = HolidayForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Holiday.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data['label'] = 'test failure'

        request.user = self.ref_cmp_user
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Holiday.objects.filter(label='test_fail').exists())

    def test_vacation_creation(self):
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        ).save()
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }

        request.user = self.scuio_user

        form = VacationForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Vacation.objects.filter(label=data['label']).exists())

        # Validation fail (invalid user)
        data['label'] = 'test failure'

        request.user = self.ref_cmp_user
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Vacation.objects.filter(label='test failure').exists())

        # wrong dates
        data['label'] = 'test failure 2'
        data['end_date'] = datetime.datetime.today().date() + datetime.timedelta(days=1)

        request.user = self.ref_cmp_user
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Vacation.objects.filter(label='test failure 2').exists())

    def test_vacation__fail_before_univ_year_(self):
        request.user = self.scuio_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
        ).save()
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_vacation__fail_after_univ_year_(self):
        request.user = self.scuio_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
        ).save()
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=40),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_vacation__fail_start_date_inside_other_vacation(self):
        request.user = self.scuio_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
        ).save()
        Vacation(
            label='Vac 1',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
        ).save()

        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=40),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_vacation__fail_end_date_inside_other_vacation(self):
        request.user = self.scuio_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
        ).save()
        Vacation(
            label='Vac 1',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=50),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=60),
        ).save()

        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=55),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_vacation__fail_other_vacation_inside_this_one(self):
        request.user = self.scuio_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(
                days=1),
        ).save()
        Vacation(
            label='Vac 1',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=30),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=40),
        ).save()

        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=60),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_accompanying_document_creation(self):
        """
        Test accompanying document creation with group rights
        """

        public_type_data = {'label': 'testPublicType', 'active': True}
        public_type = PublicType.objects.create(**public_type_data)

        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}

        data = {
            'label': 'testDocument',
            'public_type': public_type.pk,
            'description': 'testDescription',
            'active': True,
        }

        request.user = self.scuio_user

        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(AccompanyingDocument.objects.filter(label=data['label']).exists())

        # Validation fail (invalid file format
        file['content_type'] = "application/fail"
        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = AccompanyingDocumentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(AccompanyingDocument.objects.filter(label='test_fail').exists())

    def test_calendar_creation__year_mode(self):
        """
        Test public type mention creation with group rights
        """
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        data_year = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=5),
            'year_end_date': now + datetime.timedelta(days=50),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        request.user = self.scuio_user

        form = CalendarForm(data=data_year, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=data_year['label']).exists())

    def test_calendar_creation__semester_mode(self):
        """
        Test public type mention creation with group rights
        """
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        data_year = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester1_start_date': now + datetime.timedelta(days=6),
            'semester2_start_date': now + datetime.timedelta(days=25),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        request.user = self.scuio_user

        form = CalendarForm(data=data_year, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=data_year['label']).exists())

    def test_calendar__validation_fail_start_before_year_begining(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=10),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=5),
            'year_end_date': now + datetime.timedelta(days=50),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_end_after_year_end(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=5),
            'year_end_date': now + datetime.timedelta(days=1000),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_start_after_end(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=50),
            'year_end_date': now + datetime.timedelta(days=10),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_semestrer1_start_after_end_of_semester_end(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=5),
            'semester1_start_date': now + datetime.timedelta(days=21),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=25),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_semestrer1_end_after_start_semester2_start(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=5),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=30),
            'semester2_start_date': now + datetime.timedelta(days=25),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_semestrer2_start_after_end_semester2_end(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=5),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_sem1_registration_before_year_begining(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=4),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=1),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_sem2_registration_before_year_begining(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=4),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=6),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=1),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_calendar__validation_fail_sem2_registration_before_year_begining(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=4),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.scuio_user
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=6),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=1),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'registration_start_date_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())


    def test_public_document_creation(self):
        """
        Test public document creation with group rights
        """

        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}

        data = {
            'label': 'testPublicDocument',
            'active': True,
            'published': False
        }

        request.user = self.scuio_user

        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicDocument.objects.filter(label=data['label']).exists())

        # Validation fail (invalid file format
        file['content_type'] = "application/fail"
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        data = {'label': 'test_failure', 'active': True}
        request.user = self.ref_cmp_user
        form = PublicDocumentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(PublicDocument.objects.filter(label='test_fail').exists())
