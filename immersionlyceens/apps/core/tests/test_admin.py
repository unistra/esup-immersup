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
from django.utils import timezone

from ..admin import (
    CalendarAdmin, CampusAdmin, CustomAdminSite, CustomUserAdmin,
    EstablishmentAdmin, StructureAdmin, TrainingAdmin,
)
from ..admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm,
    CampusForm, CancelTypeForm, CourseTypeForm, CustomThemeFileForm,
    EstablishmentForm, EvaluationFormLinkForm, EvaluationTypeForm,
    GeneralBachelorTeachingForm, GeneralSettingsForm, HighSchoolForm,
    HolidayForm, ImmersionUserChangeForm, ImmersionUserCreationForm,
    ImmersupFileForm, InformationTextForm, MailTemplateForm,
    PublicDocumentForm, PublicTypeForm, StructureForm, TrainingDomainForm,
    TrainingForm, TrainingSubdomainForm, UniversityYearForm, VacationForm,
)
from ..models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus,
    CancelType, CourseType, CustomThemeFile, Establishment, EvaluationFormLink,
    EvaluationType, GeneralBachelorTeaching, GeneralSettings,
    HigherEducationInstitution, HighSchool, Holiday, ImmersionUser,
    ImmersupFile, InformationText, MailTemplate, MailTemplateVars,
    PublicDocument, PublicType, Structure, Training, TrainingDomain,
    TrainingSubdomain, UniversityYear, Vacation,
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

    fixtures = ['group', 'group_permissions', 'high_school_levels', 'post_bachelor_levels', 'student_levels', 'higher',
                'mailtemplatevars', 'mailtemplate']

    def setUp(self):
        """
        SetUp for Admin Forms tests
        """

        # TODO Use test fixtures for all these objects

        self.site = AdminSite()
        self.today = datetime.datetime.today()

        self.superuser = get_user_model().objects.create_superuser(
            username='super', password='pass', email='immersion1@no-reply.com'
        )
        self.master_establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test1@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first()
        )

        self.establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test2@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last()
        )

        self.high_school = HighSchool.objects.create(
            label='HS1',
            address='here',
            country='FR',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            postbac_immersion=True,
            signed_charter=True,
        )

        self.high_school_2 = HighSchool.objects.create(
            label='HS2',
            address='here',
            country='FR',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='d@e.f',
            head_teacher_name='M. C D',
            postbac_immersion=False,
            signed_charter=True,
        )

        self.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='immersion2@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=self.master_establishment,
            is_staff=True,
            date_joined=timezone.now()
        )

        self.operator_user = get_user_model().objects.create_user(
            username='operator',
            password='pass',
            email='operator@no-reply.com',
            first_name='operator',
            last_name='operator'
        )

        self.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='immersion3@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=self.establishment,
            is_staff=True,
            date_joined=timezone.now()
        )

        self.ref_str_user = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='immersion4@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
            date_joined=timezone.now(),
            establishment=self.master_establishment,
        )

        self.ref_str_user_2 = get_user_model().objects.create_user(
            username='ref_str_2',
            password='pass',
            email='immersion5@no-reply.com',
            first_name='ref_str_2',
            last_name='ref_str_2',
            date_joined=timezone.now(),
            establishment=self.establishment,
        )

        self.ref_lyc_user = get_user_model().objects.create_user(
            username='ref_lyc',
            password='pass',
            email='ref-lyc@no-reply.com',
            first_name='ref_lyc',
            last_name='ref_lyc',
            is_staff=True,
            highschool=self.high_school,
            date_joined=timezone.now(),
        )

        self.ref_lyc_user_2 = get_user_model().objects.create_user(
            username='ref_lyc2',
            password='pass',
            email='ref-lyc2@no-reply.com',
            first_name='ref_lyc2',
            last_name='ref_lyc2',
            highschool=self.high_school_2,
            date_joined=timezone.now(),
        )

        self.speaker_user = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker1@no-reply.com',
            first_name='speaker1',
            last_name='speaker1',
            highschool=self.high_school,
            date_joined=timezone.now(),
        )

        self.speaker_user_2 = get_user_model().objects.create_user(
            username='speaker2',
            password='pass',
            email='speaker2@no-reply.com',
            first_name='speaker2',
            last_name='speaker2',
            highschool=self.high_school_2,
            date_joined=timezone.now()
        )

        self.student = get_user_model().objects.create_user(
            username='student',
            password='pass',
            email='student@no-reply.com',
            first_name='student',
            last_name='STUDENT',
        )

        self.visitor = get_user_model().objects.create_user(
            username='visitor',
            password='pass',
            email='visitor@no-reply.com',
            first_name='visitor',
            last_name='VISITOR',
        )

        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(self.ref_master_etab_user)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str_user)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str_user_2)
        Group.objects.get(name='REF-TEC').user_set.add(self.operator_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.ref_lyc_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.ref_lyc_user_2)
        Group.objects.get(name='INTER').user_set.add(self.speaker_user)
        Group.objects.get(name='INTER').user_set.add(self.speaker_user_2)
        Group.objects.get(name='ETU').user_set.add(self.student)
        Group.objects.get(name='VIS').user_set.add(self.visitor)

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

        # As an operator
        data = {'label': 'test2', 'active': True}
        request.user = self.operator_user

        form = TrainingDomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingDomain.objects.filter(label='test2').exists())


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

        # As an operator
        data = {'label': 'sd test 2', 'training_domain': td.pk, 'active': True}

        request.user = self.operator_user
        form = TrainingSubdomainForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(TrainingSubdomain.objects.filter(label='sd test 2').exists())


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

        # As an operator:
        data_campus_3 = {
            'label': 'Test Campus operator',
            'active': True,
            'establishment': self.master_establishment
        }
        request.user = self.operator_user
        form = CampusForm(data=data_campus_3, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Campus.objects.filter(label=data_campus_3['label']).exists())
        self.assertEqual(Campus.objects.filter(label=data_campus_3['label']).count(), 1)

        # Test campus admin queryset
        adminsite = CustomAdminSite(name='Repositories')
        campus_admin = CampusAdmin(admin_site=adminsite, model=Campus)

        request.user = self.ref_etab_user
        queryset = campus_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 1)

        request.user = self.ref_master_etab_user
        queryset = campus_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 3)

        request.user = self.operator_user
        queryset = campus_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 3)

    def test_campus_admin(self):
        """
        Test campus admin authorizations
        """
        adminsite = CustomAdminSite(name='Repositories')
        campus_admin = CampusAdmin(admin_site=adminsite, model=Campus)

        testCampus = Campus.objects.create(label='testCampus', active=True, establishment=self.master_establishment)

        success_user_list = [self.operator_user, self.ref_master_etab_user, self.superuser]
        fail_user_list = [self.ref_etab_user, self.ref_str_user, self.ref_lyc_user]

        # No building attached to the campus : success
        for user in success_user_list:
            request.user = user
            self.assertTrue(campus_admin.has_delete_permission(request=request, obj=testCampus))

        # Bad user : fail
        for user in fail_user_list:
            request.user = user
            self.assertFalse(campus_admin.has_delete_permission(request=request, obj=testCampus))

        # Building attached to the campus : fail
        Building.objects.create(label='test building', campus=testCampus)
        for user in success_user_list + fail_user_list:
            request.user = user
            self.assertFalse(campus_admin.has_delete_permission(request=request, obj=testCampus))


    def test_building_creation(self):
        """
        Test admin Campus creation with group rights
        """

        testCampus = Campus.objects.create(label='testCampus', active=True, establishment=self.establishment)
        data = {
            'label': 'testBuilding',
            'campus': testCampus.pk,
            'establishment': self.establishment,
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

        # Another success with a master establishment manager
        data['label'] = "Another test"
        request.user = self.ref_master_etab_user
        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label=data['label']).exists())

        # Another success with an operator
        data['label'] = "A last test"
        request.user = self.operator_user
        form = BuildingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Building.objects.filter(label=data['label']).exists())

        self.assertEqual(Building.objects.count(), 3)


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

        request.user = self.operator_user
        queryset = structure_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 2)


    def test_structure_creation(self):
        """
        Test admin structure creation with group rights
        """
        self.ref_etab_user.establishment = self.establishment
        self.ref_etab_user.save()

        data = {
            'code': 'AB123',
            'label': 'test',
            'active': True
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
        self.assertIn('A structure with this code already exists', form.errors["__all__"])

        # Validation fail (invalid user)
        request.user = self.ref_str_user
        data["label"] = "Another test"
        data["code"] = "CD345"
        form = StructureForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertEqual(Structure.objects.count(), 1)

        # Success as an operator
        request.user = self.operator_user
        form = StructureForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(Structure.objects.count(), 2)


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

        # Another training as an operator : success
        data_training_3 = {
            'label': 'test operator',
            'structures': [structure_2, ],
            'training_subdomains': [training_subdomain.pk, ],
        }

        request.user = self.operator_user
        form = TrainingForm(data=data_training_3, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Training.objects.filter(label=data_training_3['label']).exists())
        self.assertEqual(Training.objects.filter(label=data_training_3['label']).count(), 1)

        # Test training admin queryset
        adminsite = CustomAdminSite(name='Repositories')
        training_admin = TrainingAdmin(admin_site=adminsite, model=Training)

        request.user = self.ref_etab_user
        queryset = training_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 2)

        request.user = self.ref_master_etab_user
        queryset = training_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 3)

        request.user = self.operator_user
        queryset = training_admin.get_queryset(request=request)
        self.assertEqual(queryset.count(), 3)


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

        data = {'label': 'testBachelor 2', 'active': True}
        request.user = self.operator_user
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

        request.user = self.operator_user
        data = {'label': 'another_cancel_type', 'active': True}
        form = CancelTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CancelType.objects.filter(label=data['label']).exists())


    def test_course_type_creation(self):
        """
        Test course type creation with group rights
        """
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

        request.user = self.operator_user
        data = {'label': 'another_testCourse', 'full_label': 'another test course', 'active': True}
        form = CourseTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CourseType.objects.filter(label=data['label']).exists())


    def test_general_bachelor_teaching_creation(self):
        """
        Test general bachelor specialty teaching creation with group rights
        """
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

        data = {'label': 'another test', 'active': True}
        request.user = self.operator_user
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

        data = {'label': 'Another public type', 'active': True}
        request.user = self.operator_user
        form = PublicTypeForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicType.objects.filter(label=data['label']).exists())


    def test_university_year(self):
        """
        University year tests
        """

        ############
        # CREATION #
        ############

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

        # Fail : constraint : before now
        request.user = self.ref_master_etab_user

        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=3),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }

        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start date can't be today or earlier", form.errors["__all__"])

        # Fail : start > end
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=99),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=9),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start date greater than end date", form.errors["__all__"])

        # Fail : registration before start date
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=1),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start of registration date must be set between start and end date", form.errors["__all__"])

        # Fail : registration date after end date
        data = {
            'label': 'test_ok',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=20),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start of registration date must be set between start and end date", form.errors["__all__"])


        ###########
        # Success #
        ###########
        data = {
            'label': 'university_year',
            'active': True,
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'registration_start_date': datetime.datetime.today().date() + datetime.timedelta(days=3),
            'purge_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }

        request.user = self.ref_master_etab_user

        form = UniversityYearForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(UniversityYear.objects.filter(label=data['label']).exists())

        # As an operator
        # Fail : already active
        request.user = self.operator_user
        form = UniversityYearForm(data=data, request=request)
        self.assertFalse(form.is_valid())

        UniversityYear.objects.all().delete()

        # Success
        form = UniversityYearForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(UniversityYear.objects.filter(label=data['label']).exists())


    def test_highschool_creation(self):
        """
        Test admin HighSchool creation with group rights
        """

        data = {
            'label': 'Santo Domingo',
            'country': 'FR',
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
            'mailing_list': 'test@mailing-list.fr',
            'badge_html_color': '#112233'
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

        request.user = self.operator_user

        data['label'] = 'Another high school'
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
        university_year = UniversityYear.objects.create(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        )

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

        # As an operator user
        request.user = self.operator_user
        data = {
            'label': 'Holiday 2',
            'date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }
        form = HolidayForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Holiday.objects.filter(label=data['label']).exists())

        # Fail : University year has already begun
        university_year.start_date = datetime.datetime.today().date() - datetime.timedelta(days=1)
        university_year.save()
        data = {
            'label': 'Holiday 3',
            'date': datetime.datetime.today().date() + datetime.timedelta(days=5),
        }
        form = HolidayForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Error : the university year has already begun", form.errors['__all__'])


    def test_vacation_creation(self):
        university_year = UniversityYear.objects.create(
            label='Hello',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=10),
            registration_start_date=datetime.datetime.today().date() + datetime.timedelta(days=1),
        )

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

        # Fail : vacation before university year
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=-10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation start date must set between university year dates", form.errors["__all__"])

        # Fail : vacation after university year
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=40),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation end date must set between university year dates", form.errors["__all__"])

        # Fails : overlapping vacation dates
        university_year.end_date += datetime.timedelta(days=100)
        university_year.save()
        vacation = Vacation.objects.create(
            label='Vac 1',
            start_date=datetime.datetime.today().date() + datetime.timedelta(days=40),
            end_date=datetime.datetime.today().date() + datetime.timedelta(days=60),
        )

        # - invalid start date
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=50),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=70),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation start inside another vacation", form.errors["__all__"])

        # - invalid end date
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=30),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=50),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Vacation end inside another vacation", form.errors["__all__"])

        # - vacation period inside the new one
        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=70),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A vacation exists inside this vacation", form.errors["__all__"])

        ###########
        # Success #
        ###########
        vacation.delete() # cleanup

        data = {
            'label': 'Vacation',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=2),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=4),
        }

        form = VacationForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Vacation.objects.filter(label=data['label']).exists())

        # As an operator user
        request.user = self.operator_user
        data = {
            'label': 'Vacation 2',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=5),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=7),
        }
        form = VacationForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Vacation.objects.filter(label=data['label']).exists())

        # Fail : University year has already begun
        university_year.start_date = datetime.datetime.today().date() - datetime.timedelta(days=1)
        university_year.save()
        data = {
            'label': 'Vacation 3',
            'start_date': datetime.datetime.today().date() + datetime.timedelta(days=8),
            'end_date': datetime.datetime.today().date() + datetime.timedelta(days=10),
        }
        form = VacationForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Error : the university year has already begun", form.errors['__all__'])


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
            'public_type': [f"{public_type.id}",]
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

        # As an operator
        request.user = self.operator_user
        data['label'] = "Test document #2"
        form = AccompanyingDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(AccompanyingDocument.objects.filter(label=data['label']).exists())


    def test_calendar_creation__year_mode(self):
        """
        Test public type mention creation with group rights
        """
        now = datetime.datetime.today().date()
        UniversityYear.objects.create(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=10),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        )
        calendar_data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=15),
            'year_end_date': now + datetime.timedelta(days=50),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        # Failures (invalid users)
        request.user = self.ref_str_user
        form = CalendarForm(data=calendar_data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=calendar_data['label']).exists())

        request.user = self.ref_etab_user
        form = CalendarForm(data=calendar_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=calendar_data['label']).exists())

        # Fail : invalid start date
        request.user = self.ref_master_etab_user

        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=5),
            'year_end_date': now + datetime.timedelta(days=50),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start date must be set between university year dates", form.errors["__all__"])

        # Fail : invalid end date
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=15),
            'year_end_date': now + datetime.timedelta(days=1000),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("End date must set be between university year dates", form.errors["__all__"])

        # Fail : start > end
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'YEAR',
            'year_start_date': now + datetime.timedelta(days=50),
            'year_end_date': now + datetime.timedelta(days=15),
            'year_registration_start_date': now + datetime.timedelta(days=2),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Start date greater than end date", form.errors["__all__"])


        ###########
        # Success #
        ###########
        form = CalendarForm(data=calendar_data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=calendar_data['label']).exists())

        # As an operator
        Calendar.objects.all().delete()
        request.user = self.operator_user
        form = CalendarForm(data=calendar_data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=calendar_data['label']).exists())


    def test_calendar_creation__semester_mode(self):
        """
        Test public type mention creation with group rights
        """
        now = datetime.datetime.today().date()
        UniversityYear.objects.create(
            label='University Year',
            active=True,
            start_date=now + datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=100),
            registration_start_date=now + datetime.timedelta(days=3),
            purge_date=now + datetime.timedelta(days=5),
        )
        calendar_data = {
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
        form = CalendarForm(data=calendar_data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=calendar_data['label']).exists())

        request.user = self.ref_etab_user
        form = CalendarForm(data=calendar_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(Calendar.objects.filter(label=calendar_data['label']).exists())

        # Fail : semester 1 : start date > end date
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
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Semester 1 start date greater than semester 1 end date", form.errors["__all__"])

        # Fail : semester 1 end date > semester 2 start date
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
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Semester 1 ends after the beginning of semester 2", form.errors["__all__"])

        # Fail : semester 2 : start date > end date
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
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Semester 2 start date greater than semester 2 end date", form.errors["__all__"])

        # Fail : registration date < university year dates
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=-1),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=26),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "semester 1 start registration date must set between university year dates",
            form.errors["__all__"]
        )

        # Fail : semester 2 registration date < university year dates
        data = {
            'label': 'Calendar year',
            'calendar_mode': 'SEMESTER',
            'semester1_registration_start_date': now + datetime.timedelta(days=6),
            'semester1_start_date': now + datetime.timedelta(days=5),
            'semester1_end_date': now + datetime.timedelta(days=20),
            'semester2_start_date': now + datetime.timedelta(days=60),
            'semester2_end_date': now + datetime.timedelta(days=50),
            'semester2_registration_start_date': now + datetime.timedelta(days=-1),
            'global_evaluation_date': now + datetime.timedelta(days=2),
            'nb_authorized_immersion_per_semester': 2,
            'year_nb_authorized_immersion': 2,
        }
        form = CalendarForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "semester 2 start registration date must set between university year dates",
            form.errors["__all__"]
        )

        ###########
        # Success #
        ###########
        form = CalendarForm(data=calendar_data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=calendar_data['label']).exists())

        # As an operator
        Calendar.objects.all().delete()
        request.user = self.operator_user
        form = CalendarForm(data=calendar_data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Calendar.objects.filter(label=calendar_data['label']).exists())

    def test_calendar_admin(self):
        """
        Test calendar admin rights
        """
        adminsite = CustomAdminSite(name='Repositories')
        calendar_admin = CalendarAdmin(admin_site=adminsite, model=Calendar)

        success_user_list = [self.ref_master_etab_user, self.superuser, self.operator_user]
        fail_user_list = [self.ref_etab_user, self.ref_str_user, self.ref_lyc_user]

        # Creation rights : ok for these users, and only if no calendar exists yet
        for user in success_user_list:
            request.user = user
            self.assertTrue(calendar_admin.has_add_permission(request=request))

        # Bad user : fail
        for user in fail_user_list:
            request.user = user
            self.assertFalse(calendar_admin.has_add_permission(request=request))

        # deletion : superuser only
        success_user_list = [self.superuser, ]
        fail_user_list = [
            self.ref_master_etab_user,
            self.operator_user,
            self.ref_etab_user,
            self.ref_str_user,
            self.ref_lyc_user
        ]

        request.user = self.superuser
        self.assertTrue(calendar_admin.has_delete_permission(request=request))

        for user in fail_user_list:
            request.user = user
            self.assertFalse(calendar_admin.has_delete_permission(request=request))

        # Readonly fields
        calendar = Calendar.objects.create(
            label='my calendar',
            calendar_mode='YEAR',
            year_start_date=self.today - datetime.timedelta(days=10),
            year_end_date=self.today + datetime.timedelta(days=10),
            year_registration_start_date=self.today + datetime.timedelta(days=2),
            year_nb_authorized_immersion=4
        )

        university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=self.today.date() - datetime.timedelta(days=365),
            end_date=self.today.date() + datetime.timedelta(days=20),
            registration_start_date=self.today.date() - datetime.timedelta(days=1),
            active=True,
        )

        request.user = self.superuser
        self.assertEqual(calendar_admin.get_readonly_fields(request=request, obj=calendar), [])

        for user in fail_user_list:
            request.user = user
            self.assertEqual(
                sorted(calendar_admin.get_readonly_fields(request=request, obj=calendar)),
                ['calendar_mode', 'label', 'nb_authorized_immersion_per_semester', 'semester1_end_date',
                 'semester1_registration_start_date', 'semester1_start_date', 'semester2_end_date',
                 'semester2_registration_start_date', 'semester2_start_date', 'year_end_date',
                 'year_nb_authorized_immersion', 'year_registration_start_date', 'year_start_date']
            )

        # Creation with an existing calendar : no more allowed
        for user in success_user_list + fail_user_list:
            request.user = user
            self.assertFalse(calendar_admin.has_add_permission(request=request))


    def test_public_document_creation(self):
        """
        Test public document creation with group rights
        """
        file = {'document': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}

        # Failures (invalid users)
        data = {
            'label': 'test_fail',
            'active': True,
            'published': False
        }

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

        # As an operator
        data['label'] = "Another document"
        form = PublicDocumentForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(PublicDocument.objects.filter(label='Another document').exists())


    def test_immersupfile_creation(self):
        """
        Test ImmersupFile creation with group rights
        """
        file = {'file': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}

        # Failures (invalid users)
        data = {
            'code': 'TEST_FAIL',
        }

        for user in [self.ref_str_user, self.ref_etab_user]:
            request.user = user
            form = ImmersupFileForm(data=data, files=file, request=request)
            self.assertFalse(form.is_valid())
            self.assertIn("You don't have the required privileges", form.errors["__all__"])
            self.assertFalse(ImmersupFile.objects.filter(code='TEST_FAIL').exists())

        # Failure #2 : invalid file format (and valid user)
        file = {'file': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/fail")}
        request.user = self.ref_master_etab_user

        file['content_type'] = "application/fail"
        form = ImmersupFileForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())
        self.assertFalse(ImmersupFile.objects.filter(code='TEST_FAIL').exists())

        # Success
        file = {'file': SimpleUploadedFile("testpron.pdf", b"toto", content_type="application/pdf")}
        data = {
            'code': 'SUCCESS',
        }
        form = ImmersupFileForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(ImmersupFile.objects.filter(code='SUCCESS').exists())

        # As an operator
        data['code'] = "SUCCESS2"
        form = ImmersupFileForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(ImmersupFile.objects.filter(code='SUCCESS2').exists())


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
        data = {'code': 'testCode 2', 'label': 'test_failure'}

        for user in [self.ref_etab_user, self.operator_user, self.ref_str_user, self.ref_master_etab_user]:
            request.user = user
            form = EvaluationTypeForm(data=data, request=request)
            self.assertFalse(form.is_valid())
            self.assertIn("You don't have the required privileges", form.errors["__all__"])
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

        request.user = self.operator_user
        form = EvaluationFormLinkForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You are not allowed to create a new Evaluation Form Link", form.errors["__all__"])
        self.assertFalse(EvaluationFormLink.objects.filter(url=data['url']).exists())

        request.user = self.ref_master_etab_user
        form = EvaluationFormLinkForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You are not allowed to create a new Evaluation Form Link", form.errors["__all__"])
        self.assertFalse(EvaluationFormLink.objects.filter(url=data['url']).exists())

        # Success
        request.user = self.superuser
        data = {'evaluation_type': type.pk, 'url': 'http://google.fr'}
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
            'label': 'Etablissement 1',
            'short_label': 'Eta 1',
            'badge_html_color': '#112233',
            'email': 'test@test.com',
            'active': True,
            'address': 'address',
            'department': 'departmeent',
            'city': 'city',
            'zip_code': 'zip_code',
            'phone_number': '+33666',
            'uai_reference': HigherEducationInstitution.objects.first()
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
        self.assertIsNone(eta.data_source_plugin) # No plugin
        self.assertIsNone(eta.data_source_settings) # No plugin settings

        # Delete, recreate as an operator
        eta.delete()
        request.user = self.operator_user
        form = EstablishmentForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        eta = Establishment.objects.get(code='ETA1')
        self.assertTrue(eta.active)  # default
        self.assertTrue(eta.master)  # first establishment creation : master = True

        # Delete, recreate with account plugin, and check again
        eta.delete()
        request.user = self.superuser

        # see settings.AVAILABLE_ACCOUNTS_PLUGINS
        data["data_source_plugin"] = "LDAP"
        form = EstablishmentForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        eta = Establishment.objects.get(code='ETA1')
        self.assertTrue(eta.active)  # default
        self.assertTrue(eta.master)  # first establishment creation : master = True
        self.assertEqual(eta.data_source_plugin, 'LDAP')  # LDAP plugin
        self.assertIsNotNone(eta.data_source_settings)  # LDAP plugin settings


        # Create a second establishment and check the 'unique' rules
        # unique code
        data['uai_reference'] = HigherEducationInstitution.objects.last()
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

        # As an operator: should succeed
        request.user = self.operator_user
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=eta2))

        # TODO : create an establishment and try to delete the related HigherEducationInstitution object


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

        for user in [self.ref_str_user, self.ref_etab_user, self.ref_master_etab_user, self.operator_user]:
            request.user = user
            form = InformationTextForm(data=data, request=request)
            self.assertFalse(form.is_valid())
            self.assertIn("You don't have the required privileges", form.errors["__all__"])
            self.assertFalse(MailTemplate.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.superuser

        form = InformationTextForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        information_text = form.save()
        self.assertTrue(InformationText.objects.filter(label=data['label']).exists())
        self.assertEqual(information_text.label, 'my text')

        # Update allowed
        request.user = self.ref_master_etab_user
        data['label'] = 'another text'
        form = InformationTextForm(instance=information_text, data=data, request=request)
        self.assertTrue(form.is_valid())
        information_text = form.save()
        self.assertEqual(InformationText.objects.filter(code=data['code']).count(), 1)
        self.assertEqual(information_text.label, 'another text')


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
            'available_vars': [MailTemplateVars.objects.first()]
        }

        for user in [self.ref_str_user, self.ref_etab_user, self.ref_master_etab_user, self.operator_user]:
            request.user = user
            form = MailTemplateForm(data=data, request=request)
            self.assertFalse(form.is_valid())
            self.assertIn("You don't have the required privileges", form.errors["__all__"])
            self.assertFalse(MailTemplate.objects.filter(label=data['label']).exists())

        # Success
        request.user = self.superuser
        form = MailTemplateForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        mail_template = form.save()
        self.assertTrue(MailTemplate.objects.filter(label=data['label']).exists())
        self.assertEqual(mail_template.body, 'test content')

        # Update is allowed
        request.user = self.ref_master_etab_user

        data["body"] = "New mail body"
        form = MailTemplateForm(instance=mail_template, data=data, request=request)
        self.assertTrue(form.is_valid())
        mail_template = form.save()
        self.assertEqual(mail_template.body, "New mail body")

        # Bad template syntax error
        data["body"] = "Bad syntax in body {% elif %}"
        form = MailTemplateForm(instance=mail_template, data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("The message body contains syntax error(s) : Invalid block tag on line 1: 'elif'. Did you forget to register or load this tag?", form.errors["__all__"])


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
        self.assertTrue(est_admin.has_add_permission(request=request))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a master establishment manager
        # --------------------------------------
        request.user = self.ref_master_etab_user
        # Should be True
        self.assertTrue(est_admin.has_add_permission(request=request))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As an operator
        # --------------------------------------
        request.user = self.operator_user
        # Should be True
        self.assertTrue(est_admin.has_add_permission(request=request))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_master_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_etab_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a regular establishment manager
        # --------------------------------------
        request.user = self.ref_etab_user
        # Should be True
        self.assertTrue(est_admin.has_add_permission(request=request))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.ref_str_user))

        # Should NOT be True
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_master_etab_user))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))

        # --------------------------------------
        # As a high school referent
        # --------------------------------------
        request.user = self.ref_lyc_user
        # Should be True
        self.assertTrue(est_admin.has_add_permission(request=request))
        self.assertTrue(est_admin.has_delete_permission(request=request, obj=self.speaker_user))

        # Should NOT be True
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_master_etab_user))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.ref_str_user_2))
        self.assertFalse(est_admin.has_delete_permission(request=request, obj=self.speaker_user_2))

        # User creation
        # Check the overriden fields
        data = {
            'username' : 'speaker3',
            'email' : 'speaker3@no-reply.com',
            'first_name' : 'speaker3',
            'last_name' : 'speaker3'
        }

        form = ImmersionUserCreationForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        new_speaker = form.save()

        self.assertEqual(new_speaker.username, data['email'])
        self.assertEqual(new_speaker.email, data['email'])
        self.assertEqual(new_speaker.highschool, self.ref_lyc_user.highschool)
        self.assertTrue(new_speaker.has_groups('INTER'))


    def test_admin_immersionuser_change_form(self):
        structure_1_data = {'code': 'A', 'label': 'test 1', 'active': True, 'establishment': self.master_establishment}
        structure_2_data = {'code': 'B', 'label': 'test 2', 'active': True, 'establishment': self.establishment}
        structure_1 = Structure.objects.create(**structure_1_data)
        structure_2 = Structure.objects.create(**structure_2_data)

        self.ref_str_user.establishment = self.establishment
        self.ref_str_user.structures.add(structure_2)
        self.ref_str_user.save()

        self.assertFalse(self.ref_str_user.creation_email_sent)

        self.ref_str_user_2.establishment = self.master_establishment
        self.ref_str_user_2.structures.add(structure_1)
        self.ref_str_user_2.save()

        for user in [self.ref_master_etab_user, self.operator_user]:
            request.user = user

            # Try an establishment update : forbidden
            self.assertEqual(self.ref_etab_user.establishment, self.establishment)

            # Initial data + update
            data = ImmersionUserChangeForm(instance=self.ref_etab_user, request=request).initial
            data['establishment'] = self.master_establishment

            form = ImmersionUserChangeForm(data, instance=self.ref_etab_user, request=request)
            self.assertFalse(form.is_valid())
            self.assertIn(
                "Select a valid choice. That choice is not one of the available choices.",
                form.errors["establishment"]
            )

        # Bad structure choice
        request.user = self.ref_etab_user

        data = {
            'structures': [structure_1],
        }

        form = ImmersionUserChangeForm(data, instance=self.ref_str_user, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            f"Select a valid choice. {structure_1.id} is not one of the available choices.",
            form.errors["structures"]
        )

        # Bad group choice
        self.ref_str_user.refresh_from_db()

        etu_group = Group.objects.get(name="ETU")
        data["structures"] = [structure_2]
        data["groups"] = [etu_group]

        form = ImmersionUserChangeForm(data, instance=self.ref_str_user, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn(
            f"Select a valid choice. {etu_group.id} is not one of the available choices.",
            form.errors["groups"]
        )

        # Success
        self.ref_str_user.refresh_from_db()
        data = {
            "establishment": self.ref_str_user.establishment,
            "username": self.ref_str_user.username,
            "is_staff": True,
            "is_active": True,
            "first_name": "first",
            "last_name": "last",
            "email": "new_email@test.com",
            "groups": [Group.objects.get(name='REF-STR')],
            "structures": [structure_2]
        }
        form = ImmersionUserChangeForm(data, instance=self.ref_str_user, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.ref_str_user.refresh_from_db()
        self.assertEqual(self.ref_str_user.first_name, "first")
        self.assertEqual(self.ref_str_user.last_name, "last")
        self.assertEqual(self.ref_str_user.email, "new_email@test.com")
        self.assertTrue(self.ref_str_user.is_active)
        self.assertFalse(self.ref_str_user.is_staff) # No change
        self.assertTrue(self.ref_str_user.creation_email_sent)


        # As High school manager
        request.user = self.ref_lyc_user
        new_user = ImmersionUser.objects.create(
            username='inter@test.com',
            last_name='new',
            first_name='new',
            email='inter@test.com',
            highschool=self.ref_lyc_user.highschool
        )

        # Success : bad group and structure ignored
        ref_lyc_group = Group.objects.get(name='REF-LYC')
        inter_group = Group.objects.get(name='INTER')
        data = {
            "username": new_user.username,
            "is_staff": True,
            "is_active": True,
            "first_name": "new",
            "last_name": "new",
            "email": "new_inter@test.com",
            "groups": [ref_lyc_group],
            "structures": [structure_2],
            "highschool": self.ref_lyc_user.highschool
        }
        form = ImmersionUserChangeForm(data, instance=new_user, request=request)
        self.assertTrue(form.is_valid())
        new_user = form.save()
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.groups.filter(name='INTER').exists())
        self.assertFalse(new_user.structures.exists())
        self.assertEqual(new_user.username, new_user.email)
        self.assertFalse(new_user.is_staff)


    def test_admin_training(self):
        training_domain_data = {'label': 'domain', 'active': True}
        training_subdomain_data = {'label': 'subdomain', 'active': True}
        training_domain = TrainingDomain.objects.create(**training_domain_data)
        training_subdomain = TrainingSubdomain.objects.create(
            training_domain=training_domain, **training_subdomain_data)

        establishment3 = Establishment.objects.create(
            code='ETA1337',
            label='Etablissement 1337',
            short_label='Eta 1337',
            active=True,
            master=False,
            email='test1@test.com',
            uai_reference=HigherEducationInstitution.objects.all()[1]
        )

        structure = Structure.objects.create(label="structure1", establishment=establishment3)

        # no structure and no highschool
        data = {"label": "hello", "training_subdomains": [training_subdomain]}
        request.user = self.ref_lyc_user
        form = TrainingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Neither high school nor structure is set. Please choose one.", form.errors["__all__"])


        # High school
        data = {
            "label": "hello",
            "training_subdomains": [training_subdomain.id],
            "highschool": self.high_school.id,
        }
        form = TrainingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(str(form.errors)), 0)

        # only structure
        data = {
            "label": "hello",
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id],
            # "highschool": self.high_school.id,
        }
        form = TrainingForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(str(form.errors)), 0)

        # both
        data = {
            "label": "hello",
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id],
            "highschool": self.high_school.id,
        }
        form = TrainingForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "High school and structure can't be set together. Please choose one.",
            form.errors["__all__"]
        )


    def test_general_settings(self):
        # User =! admin nor operator
        data = {"setting": "MY_SETTING", "parameters": \
            {"type": "text", "value": "value", "description": "my super setting"}}
        request.user = self.ref_str_user
        form = GeneralSettingsForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])
        self.assertFalse(GeneralSettings.objects.filter(setting='MY_SETTING').exists())

        # Operator user
        request.user = self.operator_user
        form = GeneralSettingsForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(str(form.errors)), 0)
        form.save()
        self.assertTrue(GeneralSettings.objects.filter(setting='MY_SETTING').exists())

        # Add ACTIVATE_STUDENTS setting
        data = {"setting": "ACTIVATE_STUDENTS", "parameters": \
            {"type": "boolean", "value": True, "description": "activate students"}}

        form = GeneralSettingsForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(str(form.errors)), 0)
        form.save()

        # ACTIVATE_STUDENTS exists
        form = GeneralSettingsForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("General setting with this Setting name already exists.", form.errors['setting'])

        # ACTIVATE_STUDENTS try to deactivate with students in database
        g = GeneralSettings.objects.get(setting='ACTIVATE_STUDENTS')

        data = {"setting": "ACTIVATE_STUDENTS", "parameters": \
            {"type": "boolean", "value": False, "description": "activate students"}}

        form = GeneralSettingsForm(data=data, instance=g, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Students users exist you can't deactivate students", form.errors["__all__"])

        # ACTIVATE_STUDENTS working when no students in database
        self.student.delete()
        form = GeneralSettingsForm(data=data, instance=g, request=request)
        self.assertTrue(form.is_valid())

        # ACTIVATE_VISITORS try to deactivate with visitors in database

        data = {"setting": "ACTIVATE_VISITORS", "parameters": \
            {"type": "boolean", "value": False, "description": "activate visitors"}}

        form = GeneralSettingsForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Visitors users exist you can't deactivate visitors", form.errors["__all__"])

        # ACTIVATE_VISITORS working when no visitors in database
        self.visitor.delete()
        form = GeneralSettingsForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        # Wrong format for setting parameters
        data = {"setting": "DUMMY_PARAMETER", "parameters": \
            {"type": "wrong type", "missing_value": "value", "description": "dummy wrong format setting"}}

        form = GeneralSettingsForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        error = "Error : 'value' is a required property\n\nFailed validating 'required' in schema:\n    {'properties': {'description': {'minLength': 1, 'type': 'string'},\n                    'type': {'minLength': 1, 'type': 'string'},\n                    'value': {'minLength': 1,\n                              'type': ['boolean', 'string']}},\n     'required': ['description', 'type', 'value'],\n     'type': 'object'}\n\nOn instance:\n    {'description': 'dummy wrong format setting',\n     'missing_value': 'value',\n     'type': 'wrong type'}"

        self.assertIn(error, form.errors['parameters'][0])


def test_custom_theme_file_creation(self):
        """
        Test custom theme file creation with group rights
        """

        file = {'file': SimpleUploadedFile("shiny_css.css", b"toto", content_type="text/css")}
        data = {
            'type': 'CSS',
        }

        # Failures (invalid users)
        request.user = self.ref_str_user
        form = CustomThemeFileForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn("You don't have the required privileges", form.errors["__all__"])

        request.user = self.ref_etab_user
        form = CustomThemeFileForm(data=data, files=file, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You don't have the required privileges", form.errors["__all__"])

        # Success
        request.user = self.operator_user

        form = CustomThemeFileForm(data=data, files=file, request=request)
        self.assertTrue(form.is_valid())

        # Favicon
        file2 = {'file': SimpleUploadedFile("favicon.png", b"toto", content_type="image/png")}
        data2 = {
            'type': 'FAVICON',
        }

        form = CustomThemeFileForm(data=data2, files=file2, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        # Try to upload an other favicon file is not possible
        file3 = {'file': SimpleUploadedFile("favicon2.png", b"toto", content_type="image/png")}
        form = CustomThemeFileForm(data=data2, files=file3, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A favicon already exists", form.errors["__all__"])
