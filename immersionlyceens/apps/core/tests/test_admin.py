"""
Django Admin Forms tests suite
"""
import datetime

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from ..admin import CampusAdmin, CustomAdminSite, CustomUserAdmin, EstablishmentAdmin, TrainingAdmin, StructureAdmin

from ..admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm, CampusForm, CancelTypeForm,
    ImmersionUserChangeForm, StructureForm, CourseTypeForm, EstablishmentForm, EvaluationFormLinkForm,
    EvaluationTypeForm, GeneralBachelorTeachingForm, HighSchoolForm, HolidayForm, InformationTextForm, MailTemplateForm,
    PublicDocumentForm, PublicTypeForm, TrainingDomainForm, TrainingForm, TrainingSubdomainForm, UniversityYearForm,
    VacationForm,
)
from ..models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus, CancelType, Structure, CourseType,
    Establishment, EvaluationFormLink, EvaluationType, GeneralBachelorTeaching, HighSchool, Holiday,
    ImmersionUser, InformationText, MailTemplate, MailTemplateVars, PublicDocument, PublicType, Training,
    TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)


class MockRequest:
    pass


# request = MockRequest()

request_factory = RequestFactory()
request = request_factory.get('/admin')
setattr(request, 'session', 'session')
messages = FallbackStorage(request)
setattr(request, '_messages', messages)

class AdminFormsTestCase(TestCase):
    """
    Main admin forms tests class
    """

    fixtures = ['group']

    def setUp(self):
        """
        SetUp for Admin Forms tests
        """

        # TODO Use test fixtures for all these objects

        self.site = AdminSite()
        self.superuser = get_user_model().objects.create_superuser(
            username='super', password='pass', email='immersion1@no-reply.com'
        )
        self.master_establishment = Establishment.objects.create(
            code='ETA1', label='Etablissement 1', short_label='Eta 1', active=True, master=True, email='test1@test.com',
            establishment_type='HIGHER_INST'
        )

        self.establishment = Establishment.objects.create(
            code='ETA2', label='Etablissement 2', short_label='Eta 2', active=True, master=False, email='test2@test.com',
            establishment_type='HIGHER_INST'
        )

        self.high_school = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            postbac_immersion=True
        )

        self.high_school_2 = HighSchool.objects.create(
            label='HS2',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='d@e.f',
            head_teacher_name='M. C D',
            postbac_immersion=False
        )

        self.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='immersion2@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=self.master_establishment
        )

        self.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='immersion3@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=self.establishment
        )

        self.ref_str_user = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='immersion4@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
        )

        self.ref_str_user_2 = get_user_model().objects.create_user(
            username='ref_str_2',
            password='pass',
            email='immersion5@no-reply.com',
            first_name='ref_str_2',
            last_name='ref_str_2',
        )

        self.ref_lyc_user = get_user_model().objects.create_user(
            username='ref_lyc',
            password='pass',
            email='ref-lyc@no-reply.com',
            first_name='ref_lyc',
            last_name='ref_lyc',
            highschool=self.high_school
        )

        self.ref_lyc_user_2 = get_user_model().objects.create_user(
            username='ref_lyc2',
            password='pass',
            email='ref-lyc2@no-reply.com',
            first_name='ref_lyc2',
            last_name='ref_lyc2',
            highschool=self.high_school_2
        )

        self.speaker_user = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker1@no-reply.com',
            first_name='speaker1',
            last_name='speaker1',
            highschool=self.high_school
        )

        self.speaker_user_2 = get_user_model().objects.create_user(
            username='speaker2',
            password='pass',
            email='speaker2@no-reply.com',
            first_name='speaker2',
            last_name='speaker2',
            highschool=self.high_school_2
        )

        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(self.ref_master_etab_user)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str_user)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str_user_2)
        Group.objects.get(name='REF-LYC').user_set.add(self.ref_lyc_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.ref_lyc_user_2)
        Group.objects.get(name='INTER').user_set.add(self.speaker_user)
        Group.objects.get(name='INTER').user_set.add(self.speaker_user_2)

    def test_training_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        # Failures (invalid users)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_str_user
        form = TrainingDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(TrainingDomain.objects.filter(label='test_fail').exists())

        request.user = self.ref_etab_user
        form = TrainingDomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(TrainingDomain.objects.filter(label='test_fail').exists())

        # Success
        data = {'label': 'test', 'active': True}
        request.user = self.ref_master_etab_user

        form = TrainingDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

    def test_training_sub_domain_creation(self):
        """
        Test admin TrainingDomain creation with group rights
        """
        domain_data = {'label': 'test', 'active': True}
        td = TrainingDomain.objects.create(**domain_data)

        self.assertTrue(TrainingDomain.objects.filter(label='test').exists())

        # Validation fail (invalid users)
        data = {'label': 'test_fail', 'training_domain': td, 'active': True}
        request.user = self.ref_str_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(TrainingSubdomain.objects.filter(label='test_fail').exists())

        request.user = self.ref_etab_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(TrainingSubdomain.objects.filter(label='test_fail').exists())

        # Success
        data = {'label': 'sd test', 'training_domain': td.pk, 'active': True}

        request.user = self.ref_master_etab_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingSubdomain.objects.filter(label='sd test').exists())


    def test_campus_creation(self):
        """
        Test admin Campus creation with group rights
        """
        data_campus_1 = {
            'label': 'Test Campus',
            'active': True,
            'establishment': self.master_establishment
        }

        data_campus_2 = {
            'label': 'Test Campus',
            'active': True,
            'establishment': self.establishment
        }

        # Failures (invalid user)
        request.user = self.ref_str_user
        form = CampusForm(data=data_campus_2, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Campus.objects.filter(label=data_campus_2['label']).exists())

        # Success
        request.user = self.ref_etab_user
        form = CampusForm(data=data_campus_2, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Campus.objects.filter(label=data_campus_2['label']).exists())
        self.assertEqual(Campus.objects.filter(label=data_campus_2['label']).count(), 1)

        # Second campus (same label) in another establishment : success
        request.user = self.ref_master_etab_user
        form = CampusForm(data=data_campus_1, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Campus.objects.filter(label=data_campus_1['label']).exists())
        self.assertEqual(Campus.objects.filter(label=data_campus_1['label']).count(), 2)

        # Second campus within the same establishment : fail
        form = CampusForm(data=data_campus_1, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(["A campus with this label already exists within the same establishment"], form.errors["label"])
        self.assertEqual(Campus.objects.filter(label=data_campus_1['label']).count(), 2)

        # Test campus admin queryset
        adminsite = CustomAdminSite(name='Repositories')
        campus_admin = CampusAdmin(admin_site=adminsite, model=Campus)

        request.user = self.ref_etab_user
        queryset = campus_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 1)

        request.user = self.ref_master_etab_user
        queryset = campus_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 2)


    def test_building_creation(self):
        """
        Test admin Campus creation with group rights
        """

        testCampus = Campus.objects.create(label='testCampus', active=True, establishment=self.establishment)
        data = {
            'label': 'testBuilding',
            'campus': testCampus.pk,
            'url': 'https://www.building.com',
            'active': True,
        }

        # Validation fail (invalid user)
        request.user = self.ref_str_user
        form = BuildingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(Building.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_etab_user
        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label=data['label']).exists())

        # Another success with master establishement manager
        data['label'] = "Another test"
        request.user = self.ref_master_etab_user
        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label=data['label']).exists())


    def test_structure_list(self):
        adminsite = CustomAdminSite(name='Repositories')
        structure_admin = StructureAdmin(admin_site=adminsite, model=Structure)

        structure_1_data = {'code': 'A', 'label': 'test 1', 'active': True, 'establishment': self.master_establishment}
        structure_2_data = {'code': 'B', 'label': 'test 2', 'active': True, 'establishment': self.establishment}
        structure_1 = Structure.objects.create(**structure_1_data)
        structure_2 = Structure.objects.create(**structure_2_data)

        request.user = self.ref_etab_user
        queryset = structure_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 1)

        request.user = self.ref_master_etab_user
        queryset = structure_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 2)


    def test_structure_creation(self):
        """
        Test admin structure creation with group rights
        """
        self.ref_etab_user.establishment = self.establishment
        self.ref_etab_user.save()

        data = {
            'code': 'AB123', 'label': 'test', 'active': True
        }

        request.user = self.ref_etab_user

        # Fail : missing field
        form = StructureForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn('This field is required.', form.errors['establishment'])
        self.assertFalse(Structure.objects.filter(label='test').exists())

        # Fail : bad establishment for this user
        data['establishment'] = self.master_establishment
        form = StructureForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            'Select a valid choice. That choice is not one of the available choices.',
            form.errors['establishment']
        )
        self.assertFalse(Structure.objects.filter(label='test').exists())

        # Success
        data['establishment'] = self.establishment
        form = StructureForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Structure.objects.filter(label='test').exists())

        # Validation fail (code unicity)
        data["label"] = "test_fail"
        form = StructureForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        request.user = self.ref_str_user
        form = StructureForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertEqual(Structure.objects.count(), 1)

    def test_training_creation(self):
        """
        Test admin Training creation with group rights
        """
        training_domain_data = {'label': 'domain', 'active': True}
        training_subdomain_data = {'label': 'subdomain', 'active': True}
        structure_1_data = {'code': 'A', 'label': 'test 1', 'active': True, 'establishment': self.master_establishment}
        structure_2_data = {'code': 'B', 'label': 'test 2', 'active': True, 'establishment': self.establishment}

        training_domain = TrainingDomain.objects.create(**training_domain_data)
        training_subdomain = TrainingSubdomain.objects.create(
            training_domain=training_domain, **training_subdomain_data
        )
        structure_1 = Structure.objects.create(**structure_1_data)
        structure_2 = Structure.objects.create(**structure_2_data)

        self.assertTrue(TrainingDomain.objects.all().exists())
        self.assertTrue(TrainingSubdomain.objects.all().exists())
        self.assertTrue(Structure.objects.filter(code='A').exists())
        self.assertTrue(Structure.objects.filter(code='B').exists())

        data_training_1 = {
            'label': 'test',
            'structures': [structure_1,],
            'training_subdomains': [training_subdomain.pk,],
        }

        data_training_2 = {
            'label': 'test',
            'structures': [structure_2, ],
            'training_subdomains': [training_subdomain.pk, ],
        }

        # Failures (invalid user)
        request.user = self.ref_str_user
        form = TrainingForm(data=data_training_2, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Training.objects.filter(label=data_training_2['label']).exists())

        # Success
        request.user = self.ref_etab_user
        form = TrainingForm(data=data_training_2, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Training.objects.filter(label=data_training_2['label']).exists())
        self.assertEqual(Training.objects.filter(label=data_training_1['label']).count(), 1)

        # Second training in another establishment : success
        request.user = self.ref_master_etab_user
        form = TrainingForm(data=data_training_1, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Training.objects.filter(label=data_training_1['label']).exists())
        self.assertEqual(Training.objects.filter(label=data_training_1['label']).count(), 2)

        # Second training within the same establishment : fail
        form = TrainingForm(data=data_training_1, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(["A training with this label already exists within the same establishment"], form.errors["label"])
        self.assertEqual(Training.objects.filter(label=data_training_1['label']).count(), 2)

        # Test training admin queryset
        adminsite = CustomAdminSite(name='Repositories')
        training_admin = TrainingAdmin(admin_site=adminsite, model=Training)

        request.user = self.ref_etab_user
        queryset = training_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 1)

        request.user = self.ref_master_etab_user
        queryset = training_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 2)


    def test_bachelor_mention_creation(self):
        """
        Test admin bachelor mention creation with group rights
        """

        data = {'label': 'test_failure', 'active': True}

        # Failures (invalid users)
        request.user = self.ref_etab_user
        form = BachelorMentionForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(BachelorMention.objects.filter(label='test_failure').exists())

        request.user = self.ref_str_user
        form = BachelorMentionForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(BachelorMention.objects.filter(label='test_failure').exists())

        # Success
        data = {'label': 'testBachelor', 'active': True}
        request.user = self.ref_master_etab_user
        form = BachelorMentionForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(BachelorMention.objects.filter(label=data['label']).exists())


    def test_cancel_type_creation(self):
        """
        Test admin cancellation type creation with group rights
        """
        # Failures (invalid users)
        data = {'label': 'my_cancel_type', 'active': True}
        request.user = self.ref_str_user
        form = CancelTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(CancelType.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = CancelTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(CancelType.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = CancelTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CancelType.objects.filter(label=data['label']).exists())


    def test_course_type_creation(self):
        """
        Test course type creation with group rights
        """
        data = {'label': 'testCourse', 'full_label': 'testFullCourse', 'active': True}

        # Failures (invalid users)
        data = {'label': 'testCourse', 'full_label': 'testFullCourse', 'active': True}
        request.user = self.ref_str_user
        form = CourseTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(CourseType.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = CourseTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(CourseType.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = CourseTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseType.objects.filter(label=data['label']).exists())


    def test_general_bachelor_teaching_creation(self):
        """
        Test general bachelor specialty teaching creation with group rights
        """
        data = {'label': 'test', 'active': True}

        # Failures (invalid users)
        data = {'label': 'test', 'active': True}
        request.user = self.ref_str_user
        form = GeneralBachelorTeachingForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(GeneralBachelorTeaching.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = GeneralBachelorTeachingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(GeneralBachelorTeaching.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = GeneralBachelorTeachingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(GeneralBachelorTeaching.objects.filter(label=data['label']).exists())

    def test_public_type_creation(self):
        """
        Test public type creation with group rights
        """
        # Failures (invalid users)
        data = {'label': 'test_fail', 'active': True}
        request.user = self.ref_str_user
        form = PublicTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(PublicType.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = PublicTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(PublicType.objects.filter(label=data['label']).exists())

        # Success
        data = {'label': 'testPublicType', 'active': True}
        request.user = self.ref_master_etab_user

        form = PublicTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicType.objects.filter(label=data['label']).exists())


    def test_university_year_creation(self):
        """
        Test public type mention creation with group rights
        """
        data = {
            'label': 'university_year',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=3),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }

        # Failures (invalid users)
        request.user = self.ref_str_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(UniversityYear.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(UniversityYear.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = UniversityYearForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(UniversityYear.objects.filter(label=data['label']).exists())


    def test_university_year_constraint__fail_before_now(self):
        request.user = self.ref_etab_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=3),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.ref_etab_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_university_year_constraint__fail_start_greater_end(self):
        request.user = self.ref_etab_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=9),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.ref_etab_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

    def test_university_year_constraint__fail_registrtion_before_start(self):
        request.user = self.ref_etab_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
        }
        request.user = self.ref_etab_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())


    def test_university_year_constraint__fail_registrtion_after_end(self):
        request.user = self.ref_etab_user
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=20),
        }
        request.user = self.ref_etab_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())


    def test_highschool_creation(self):
        """
        Test admin HighSchool creation with group rights
        """

        data = {
            'label': 'Santo Domingo',
            'address': 'rue Larry Kubiac',
            'address2': '',
            'address3': '',
            'department': '68',
            'city': 'MULHOUSE',
            'zip_code': '68100',
            'phone_number': '+3312345678',
            'fax': '+3397654321',
            'email': 'santodomingo@santodomingo.edu',
            'head_teacher_name': 'Madame Musso Grace',
            'convention_start_date': datetime.datetime.today().date(),
            'convention_end_date': '',
            'postbac_immersion': True,
            'mailing_list': 'test@mailing-list.fr'
        }

        form = HighSchoolForm(data=data, request=request)
        # Need to populate choices fields (ajax populated IRL)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]

        # Failures (invalid users)
        request.user = self.ref_str_user
        form = HighSchoolForm(data=data, request=request)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(HighSchool.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = HighSchoolForm(data=data, request=request)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(HighSchool.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = HighSchoolForm(data=data, request=request)
        form.fields['city'].choices = [('MULHOUSE', 'MULHOUSE')]
        form.fields['zip_code'].choices = [('68100', '68100')]
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(HighSchool.objects.filter(label=data['label']).exists())

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

        # Failures (invalid users)
        data = {
            'label': 'Holiday',
            'date': datetime.datetime.today().date() + datetime.timedelta(days=2),
        }
        request.user = self.ref_str_user
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Holiday.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Holiday.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = HolidayForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Holiday.objects.filter(label=data['label']).exists())


    def test_vacation_creation(self):
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        ).save()

        # Failures (invalid users)
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }
        request.user = self.ref_str_user
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Vacation.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Vacation.objects.filter(label=data['label']).exists())

        # Failure : invalid dates
        request.user = self.ref_master_etab_user
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=1)
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start date greater than end date", form.errors["__all__"])
        self.assertFalse(Vacation.objects.filter(label=data['label']).exists())

        # Success
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }

        form = VacationForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Vacation.objects.filter(label=data['label']).exists())


    def test_vacation__fail_before_univ_year_(self):
        request.user = self.ref_master_etab_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        ).save()
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation start date must set between university year dates", form.errors["__all__"])



    def test_vacation__fail_after_univ_year_(self):
        request.user = self.ref_master_etab_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        ).save()
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=40),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation end date must set between university year dates", form.errors["__all__"])


    def test_vacation__fail_start_date_inside_other_vacation(self):
        request.user = self.ref_master_etab_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
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
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation start inside another vacation", form.errors["__all__"])


    def test_vacation__fail_end_date_inside_other_vacation(self):
        request.user = self.ref_master_etab_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
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
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation end inside another vacation", form.errors["__all__"])


    def test_vacation__fail_other_vacation_inside_this_one(self):
        request.user = self.ref_master_etab_user
        UniversityYear(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=100),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
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
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A vacation exists inside this vacation", form.errors["__all__"])


    def test_accompanying_document_creation(self):
        """
        Test accompanying document creation with group rights
        """

        public_type_data = {'label': 'testPublicType', 'active': True}
        public_type = PublicType.objects.create(**public_type_data)

        file = {'document': SimpleUploadedFile("doc_test.pdf", b"toto", content_type="application/pdf")}
        data = {
            'label': 'testDocument',
            'description': 'testDescription',
            'active': True,
            'public_type': ['1',]
        }

        # Failures (invalid users)
        request.user = self.ref_str_user
        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(AccompanyingDocument.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(AccompanyingDocument.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(AccompanyingDocument.objects.filter(label=data['label']).exists())


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
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        # Failures (invalid users)
        request.user = self.ref_str_user
        form = CalendarForm(data=data_year, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=data_year['label']).exists())

        request.user = self.ref_etab_user
        form = CalendarForm(data=data_year, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=data_year['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

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
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        # Failures (invalid users)
        request.user = self.ref_str_user
        form = CalendarForm(data=data_year, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=data_year['label']).exists())

        request.user = self.ref_etab_user
        form = CalendarForm(data=data_year, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=data_year['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = CalendarForm(data=data_year, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=data_year['label']).exists())


    def test_calendar__validation_fail_start_before_year_beginning(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=10),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.ref_master_etab_user
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
        self.assertIn("Start date must be set between university year dates", form.errors["__all__"])


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
        request.user = self.ref_master_etab_user
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
        self.assertIn("End date must set be between university year dates", form.errors["__all__"])


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
        request.user = self.ref_master_etab_user
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
        self.assertIn("Start date greater than end date", form.errors["__all__"])



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
        request.user = self.ref_master_etab_user
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
        self.assertIn("Semester 1 start date greater than semester 1 end date", form.errors["__all__"])


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
        request.user = self.ref_master_etab_user
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
        self.assertIn("Semester 1 ends after the beginning of semester 2", form.errors["__all__"])


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
        request.user = self.ref_master_etab_user
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
        self.assertIn("Semester 2 start date greater than semester 2 end date", form.errors["__all__"])


    def test_calendar__validation_fail_sem1_registration_before_year_beginning(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=4),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.ref_master_etab_user
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
        self.assertIn(
            "semester 1 start registration date must set between university year dates",
            form.errors["__all__"]
        )


    def test_calendar__validation_fail_sem2_registration_before_year_beginning(self):
        now = datetime.datetime.today().date()
        UniversityYear(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=4),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        ).save()
        request.user = self.ref_master_etab_user
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
        self.assertIn(
            "semester 2 start registration date must set between university year dates",
            form.errors["__all__"]
        )


    def test_public_document_creation(self):
        """
        Test public document creation with group rights
        """
        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}

        # Failures (invalid users)
        data = {'label': 'test_fail', 'active': True, 'published': False}
        request.user = self.ref_str_user
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(PublicDocument.objects.filter(label='test_fail').exists())

        request.user = self.ref_etab_user
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(PublicDocument.objects.filter(label='test_fail').exists())

        # Failure #2 : invalid file format
        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/fail")}
        request.user = self.ref_master_etab_user

        file['content_type'] = "application/fail"
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(PublicDocument.objects.filter(label='test_fail').exists())

        # Success
        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}
        data = {'label': 'testPublicDocument', 'active': True, 'published': False}
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicDocument.objects.filter(label='testPublicDocument').exists())



    def test_evaluation_type_creation(self):
        """
        Test evaluation type creation
        """

        # Only superuser can create evaluation type
        data = {'code': 'testCode', 'label': 'testLabel'}

        request.user = self.superuser

        form = EvaluationTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(EvaluationType.objects.filter(label=data['label']).exists())

        # Unique code !
        data = {'code': 'testCode', 'label': 'testLabel'}

        form = EvaluationTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        # Validation fail (invalid user)
        data = {'code': 'testCode', 'label': 'test_failure'}
        request.user = self.ref_etab_user
        form = EvaluationTypeForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(EvaluationType.objects.filter(label='test_fail').exists())


    def test_evaluation_form_link_creation(self):
        """
        Test Evaluation form link creation
        """
        type = EvaluationType.objects.create(code='testCode', label='testLabel')

        # Failures (invalid users)
        data = {'evaluation_type': type.pk, 'url': 'http://googlefail.fr'}
        request.user = self.ref_str_user
        form = EvaluationFormLinkForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(EvaluationFormLink.objects.filter(url=data['url']).exists())

        request.user = self.ref_etab_user
        form = EvaluationFormLinkForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(EvaluationFormLink.objects.filter(url=data['url']).exists())

        # Success
        data = {'evaluation_type': type.pk, 'url': 'http://google.fr'}
        request.user = self.ref_master_etab_user

        form = EvaluationFormLinkForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(EvaluationFormLink.objects.filter(url=data['url']).exists())


    def test_establishment_form(self):
        """
        Test establishment form rules
        """
        self.establishment.delete()
        self.master_establishment.delete()


        self.assertFalse(Establishment.objects.filter(code='ETA1').exists())

        data = {
            'code': 'ETA1',
            'establishment_type': 'HIGHER_INST',
            'label': 'Etablissement 1',
            'short_label': 'Eta 1',
            'badge_html_color': '#112233',
            'email': 'test@test.com',
            'active': True
        }

        request.user = self.ref_etab_user
        form = EstablishmentForm(data=data, request=request)

        # Will fail (invalid user)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors['__all__'])

        # Should succeed
        request.user = self.superuser
        form = EstablishmentForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        form.save()

        eta = Establishment.objects.get(code='ETA1')
        self.assertTrue(eta.active) # default
        self.assertTrue(eta.master) # first establishment creation : master = True

        # Create a second establishment and check the 'unique' rules
        # unique code
        data['master'] = True
        form = EstablishmentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("This code already exists", form.errors['__all__'])

        data['code'] = "ETA2"

        # Label
        form = EstablishmentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("This label already exists", form.errors['__all__'])

        data['label'] = "Etablissement 2"

        # Short label
        form = EstablishmentForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("This short label already exists", form.errors['__all__'])
        data['short_label'] = "Eta 2"

        form = EstablishmentForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        form.save()

        eta2 = Establishment.objects.get(code='ETA2')
        self.assertTrue(eta2.active)  # default
        self.assertFalse(eta2.master)  # first establishment creation : master = True

        # Deletion
        structure = Structure.objects.create(code="CODE", label="LABEL", active=True, establishment=eta2)
        request.user = self.ref_master_etab_user

        adminsite = CustomAdminSite(name='Repositories')
        est_admin = EstablishmentAdmin(admin_site=adminsite, model=Establishment)

        # Bad user + structure attached to establishment:
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=eta2))

        # Super admin but structure still attached to establishment:
        request.user = self.superuser
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=eta2))

        # No more structure : success
        structure.establishment = None
        structure.save()
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=eta2))

        # Test again with bad user:
        request.user = self.ref_master_etab_user
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=eta2))

    def test_information_text_creation(self):
        """
        Test admin information text creation with group rights
        """
        # Failures (invalid users)
        data = {
            'label': 'my text',
            'code': 'my code',
            'content':'test content',
            'description': 'test desc',
            'active': True
        }

        request.user = self.ref_str_user
        form = InformationTextForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(InformationText.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = InformationTextForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(InformationText.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = InformationTextForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(InformationText.objects.filter(label=data['label']).exists())


    def test_mail_template_creation(self):
        # Test admin mail template creation with group rights
        # Failures (invalid users)
        data = {
            'label': 'my text',
            'code': 'my code',
            'subject': 'the mail subject',
            'body':'test content',
            'description': 'test desc',
            'active': True,
            'available_vars': MailTemplateVars.objects.first()
        }


        request.user = self.ref_str_user
        form = MailTemplateForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(MailTemplate.objects.filter(label=data['label']).exists())

        request.user = self.ref_etab_user
        form = MailTemplateForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(MailTemplate.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.ref_master_etab_user

        form = MailTemplateForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(MailTemplate.objects.filter(label=data['label']).exists())


    def test_admin_immersionuser(self):
        """
        Test various cases in immersion user admin form updates
        """
        adminsite = CustomAdminSite(name='Repositories')
        est_admin = CustomUserAdmin(admin_site=adminsite, model=ImmersionUser)

        structure_1_data = {'code': 'A', 'label': 'test 1', 'active': True, 'establishment': self.master_establishment}
        structure_2_data = {'code': 'B', 'label': 'test 2', 'active': True, 'establishment': self.establishment}
        structure_1 = Structure.objects.create(**structure_1_data)
        structure_2 = Structure.objects.create(**structure_2_data)

        self.ref_str_user.establishment = self.establishment
        self.ref_str_user.structure = structure_2
        self.ref_str_user.save()

        self.ref_str_user_2.establishment = self.master_establishment
        self.ref_str_user_2.structure = structure_1
        self.ref_str_user_2.save()

        # --------------------------------------
        # As superuser
        # --------------------------------------
        request.user = self.superuser
        # Should be True
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a master establishment manager
        # --------------------------------------
        request.user = self.ref_master_etab_user
        # Should be True
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a regular establishment manager
        # --------------------------------------
        request.user = self.ref_etab_user
        # Should be True
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))

        # Should NOT be True
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_master_etab_user))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a high school referent
        # --------------------------------------
        request.user = self.ref_lyc_user
        # Should be True
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.speaker_user))

        # Should NOT be True
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_master_etab_user))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.speaker_user_2))
