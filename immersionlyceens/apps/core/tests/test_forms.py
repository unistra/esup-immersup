"""
Django Admin Forms tests suite
"""
import datetime
import json

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import Client, RequestFactory, TestCase
from django.utils import timezone

from ...immersion.models import HighSchoolStudentRecord
from ..admin_forms import (
    AccompanyingDocumentForm, AttestationDocumentForm, BachelorMentionForm,
    BuildingForm, CampusForm, CancelTypeForm, CourseTypeForm, EvaluationFormLinkForm,
    EvaluationTypeForm, GeneralBachelorTeachingForm, GeneralSettingsForm,
    HighSchoolForm, HolidayForm, PeriodForm, PublicDocumentForm,
    PublicTypeForm, StructureForm, TrainingDomainForm, TrainingSubdomainForm,
    UniversityYearForm, VacationForm
)
from ..forms import (
    HighSchoolStudentImmersionUserForm, MyHighSchoolForm, OffOfferEventForm,
    OffOfferEventSlotForm, SlotForm
)
from ..models import (
    AccompanyingDocument, AttestationDocument, BachelorMention, BachelorType,
    Building, Campus, CancelType, Course, CourseType, Establishment, EvaluationFormLink,
    EvaluationType, GeneralBachelorTeaching, GeneralSettings, HighSchool, HighSchoolLevel,
    Holiday, Immersion, ImmersionGroupRecord, OffOfferEvent, OffOfferEventType, Period, PostBachelorLevel,
    Profile, PublicDocument, PublicType, Slot, Structure, StudentLevel,
    Training, TrainingDomain, TrainingSubdomain, UAI, UniversityYear, Vacation,
    HigherEducationInstitution, VisitorType
)

request_factory = RequestFactory()
request = request_factory.get('/admin')
setattr(request, 'session', {})
messages = FallbackStorage(request)
setattr(request, '_messages', messages)


class FormTestCase(TestCase):
    """
    Slot forms tests class
    """

    fixtures = ['group', 'high_school_levels', 'student_levels', 'post_bachelor_levels', 'higher', 'tests_uai']

    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """
        cls.master_establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test1@test.com',
            address= 'address',
            department='departmeent',
            city='city',
            zip_code= 'zip_code',
            phone_number= '+33666',
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
            address= 'address2',
            department='departmeent2',
            city='city2',
            zip_code= 'zip_code2',
            phone_number= '+33666666',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last()
        )

        cls.high_school = HighSchool.objects.create(
            label='HS1',
            address='here',
            address2='empty',
            address3='empty',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            head_teacher_name='M. A B',
            with_convention=True,
            convention_start_date=timezone.localdate() - datetime.timedelta(days=2),
            convention_end_date=timezone.localdate() + datetime.timedelta(days=2),
            signed_charter=True,
            mailing_list="my-top@mailing-list.fr",
            uses_agent_federation=True,
            uses_student_federation=True,
            active=True,
            allow_individual_immersions=True,
            postbac_immersion=False
        )

        cls.high_school.uai_codes.add(UAI.objects.get(pk='0670003P'))

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )

        cls.highschool_user2 = get_user_model().objects.create_user(
            username='hs2',
            password='pass',
            email='hs2@no-reply.com',
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

        cls.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='ref_master_etab@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=cls.master_establishment
        )

        cls.operator_user = get_user_model().objects.create_user(
            username='operator',
            password='pass',
            email='operator@no-reply.com',
            first_name='operator',
            last_name='operator'
        )

        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='immersion@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
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

        cls.visitor_type = VisitorType.objects.create(
            code='VTYPE',
            label='test',
            active=True
        )

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str_user)
        Group.objects.get(name='REF-TEC').user_set.add(cls.operator_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)

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
        cls.campus = Campus.objects.create(
            label='Esplanade',
            department='67',
            zip_code='67000',
            city='STRASBOURG',
            active=True
        )
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')
        cls.slot = Slot.objects.create(
            course=cls.course, course_type=cls.course_type, campus=cls.campus,
            building=cls.building, room='room 1', date=cls.today,
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        cls.slot.speakers.add(cls.speaker1)
        cls.ref_str_user.structures.add(cls.structure)

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

        cls.past_period = Period.objects.create(
            label='Past period',
            registration_start_date=cls.today - datetime.timedelta(days=12),
            immersion_start_date=cls.today - datetime.timedelta(days=10),
            immersion_end_date=cls.today - datetime.timedelta(days=8),
            allowed_immersions=4
        )

        cls.period1 = Period.objects.create(
            label = 'Period 1',
            registration_start_date = cls.today + datetime.timedelta(days=10),
            immersion_start_date = cls.today + datetime.timedelta(days=20),
            immersion_end_date = cls.today + datetime.timedelta(days=40),
            allowed_immersions=4
        )

        cls.evaluation_type = EvaluationType.objects.create(code='testCode', label='testLabel')
        cls.event_type = OffOfferEventType.objects.create(label="Event type label")


    def setUp(self):
        self.client = Client()
        self.client.login(username='ref_etab', password='pass')


    def test_period_form(self):
        """
        Period form tests
        """
        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        data = {
            'label': 'Period 2',
            'registration_end_date_policy': Period.REGISTRATION_END_DATE_SLOT,
            'registration_start_date': self.today - datetime.timedelta(days=8),
            'immersion_start_date': self.today - datetime.timedelta(days=6),
            'immersion_end_date': self.today + datetime.timedelta(days=1),
            'allowed_immersions': 4
        }

        # Fail : no active year
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("An active university year is required to create a period", form.errors['__all__'])

        university_year = UniversityYear.objects.create(
            label='Active year',
            start_date=self.today - datetime.timedelta(days=10),
            end_date=self.today + datetime.timedelta(days=300),
            registration_start_date=self.today,
        )

        # Fail : dates in the past
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A new period can't be set with a start_date in the past", form.errors["__all__"])

        # Fail : end date out of university year dates
        data.update({
            "registration_start_date": self.today + datetime.timedelta(days=290),
            "immersion_start_date": self.today + datetime.timedelta(days=295),
            "immersion_end_date": self.today + datetime.timedelta(days=340),
        })
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "All period dates must be between university year start/end dates",
            form.errors["__all__"]
        )

        # Fail : start date out of university year dates
        data.update({
            "registration_start_date": self.today + datetime.timedelta(days=290),
            "immersion_start_date": self.today + datetime.timedelta(days=310),
            "immersion_end_date": self.today + datetime.timedelta(days=340),
        })
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "All period dates must be between university year start/end dates",
            form.errors["__all__"]
        )

        # Fail : registration date out of university year dates
        data.update({
            "registration_start_date": self.today - datetime.timedelta(days=15),
            "immersion_start_date": self.today + datetime.timedelta(days=1),
            "immersion_end_date": self.today + datetime.timedelta(days=2),
        })
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "All period dates must be between university year start/end dates",
            form.errors["__all__"]
        )

        # Fail : dates inversions
        data.update({
            "registration_start_date": self.today + datetime.timedelta(days=50),
            "immersion_start_date": self.today + datetime.timedelta(days=70),
            "immersion_end_date": self.today + datetime.timedelta(days=60),
        })
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Immersions end date must be after immersions start date", form.errors["__all__"])

        # Fail : registration date after immersions start_date
        data.update({
            "registration_start_date": self.today + datetime.timedelta(days=60),
            "immersion_start_date": self.today + datetime.timedelta(days=50),
            "immersion_end_date": self.today + datetime.timedelta(days=70),
        })
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Registration start date must be before the immersions start date", form.errors["__all__"])

        # Fail : missing dates
        data.update({
            "registration_start_date": self.today + datetime.timedelta(days=50),
            "immersion_end_date": self.today + datetime.timedelta(days=70),
        })

        data.pop("immersion_start_date")
        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A period requires all dates to be filled in", form.errors["__all__"])

        # Fail : duplicated label
        # test 1: exact same label
        data.update({
            "label": "Period 1",
            "registration_start_date": self.today + datetime.timedelta(days=35),
            "immersion_start_date": self.today + datetime.timedelta(days=60),
            "immersion_end_date": self.today + datetime.timedelta(days=70),
        })

        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Period with this Label already exists.", form.errors["label"])

        # test 2 : using unaccent
        data.update({
            "label": "Périod 1",
        })

        form = PeriodForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("A Period object with the same label already exists", form.errors["__all__"])

        # Success
        data.update({
            "label": "Period 2",
        })

        form = PeriodForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(Period.objects.filter(label='Period 2').exists())


    def test_slot_form(self):
        """
        Slot form tests
        """
        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        data = {
            'course': self.course.id,
            'published': False,
            'n_places': 10,
        }

        ###########
        # Success #
        ###########
        # Unpublished slot
        form = SlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        # Published slot
        valid_data = {
            'place': Slot.FACE_TO_FACE,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': 'room 1',
            'date': self.today + datetime.timedelta(days=21),
            'period': self.period1,
            'start_time': datetime.time(hour=12),
            'end_time': datetime.time(hour=14),
            'n_places': 10,
            'speakers': [self.speaker1.id],
            'published': True,
        }
        form = SlotForm(data=valid_data, request=request)
        self.assertTrue(form.is_valid())

        # Published slot with an unpublished course
        self.course.published = False
        self.course.save()

        form = SlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        slot = form.save()
        self.assertFalse(slot.published)

        #############################
        # As an operator
        #############################

        slot.delete()
        self.course.published = True
        self.course.save()
        request.user = self.operator_user

        # Unpublished slot
        form = SlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        # Published slot
        valid_data = {
            'place': Slot.FACE_TO_FACE,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': 'room 1',
            'date': self.today + datetime.timedelta(days=21),
            'period': self.period1,
            'start_time': datetime.time(hour=12),
            'end_time': datetime.time(hour=14),
            'n_places': 10,
            'speakers': [self.speaker1.id],
            'published': True,
        }
        form = SlotForm(data=valid_data, request=request)
        self.assertTrue(form.is_valid())

        # Published slot with an unpublished course
        self.course.published = False
        self.course.save()

        form = SlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        slot = form.save()
        self.assertFalse(slot.published)

        #########
        # FAILS #
        #########
        request.user = self.ref_master_etab_user
        invalid_data = {
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': 'room 1',
            'date': self.today - datetime.timedelta(days=10),
            'period': self.period1,
            'start_time': datetime.time(hour=12),
            'end_time': datetime.time(hour=14),
            'n_places': 10,
            'speakers': [self.speaker1.id],
            'published': True,
        }
        # Fail : past date
        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You can't set a date in the past", form.errors["date"])

        # Fail : period not found
        i_date = self.today + datetime.timedelta(days=102)
        invalid_data["date"] = i_date
        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())

        self.assertIn(
            "Invalid date for selected period : please check periods settings",
            form.errors["__all__"]
        )

        # Fail : n_places above limit

        period_now = Period.objects.create(
            label='Now',
            registration_start_date=self.today - datetime.timedelta(days=2),
            immersion_start_date=self.today - datetime.timedelta(days=1),
            immersion_end_date=self.today + datetime.timedelta(days=1),
            allowed_immersions=4
        )
        invalid_data["period"] = period_now
        invalid_data["n_places"] = 201 # default is 200

        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("The 'n_places' field must not exceed 200", form.errors["n_places"])

        # Fail : time errors
        invalid_data["n_places"] = 10
        invalid_data["date"] = self.today
        invalid_data["start_time"] = datetime.time(hour=0)
        invalid_data["end_time"] = datetime.time(hour=1)
        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Slot is set for today : please enter a valid start_time", form.errors["start_time"])

        invalid_data["start_time"] = datetime.time(hour=20)
        invalid_data["end_time"] = datetime.time(hour=2)
        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Error: Start time must be set before end time", form.errors["start_time"])

        # Fail : missing fields for a published Slot
        data["published"] = True
        form = SlotForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Required fields are not filled in", form.errors["__all__"])

    def test_group_slot_form(self):
        """
        Slot form tests with groups attributes
        """
        activate_cohort = GeneralSettings.objects.get(setting="ACTIVATE_COHORT")
        activate_cohort.parameters["value"] = True
        activate_cohort.save()

        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        data = {
            'course': self.course.id,
            'published': False,
            'allow_group_registrations': True,
            'allow_individual_registrations': True,
        }

        ###########
        # Success #
        ###########
        # Unpublished slot
        form = SlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())

        # Published slot
        valid_data = {
            'place': Slot.FACE_TO_FACE,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': 'room 1',
            'date': self.today + datetime.timedelta(days=21),
            'period': self.period1,
            'start_time': datetime.time(hour=12),
            'end_time': datetime.time(hour=14),
            'n_places': 10,
            'speakers': [self.speaker1.id],
            'published': True,
            'allow_group_registrations': True,
            'allow_individual_registrations': True,
            'n_group_places': None,
            'group_mode': Slot.ONE_GROUP,
            'public_group': True
        }

        form = SlotForm(data=valid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Please enter a valid number for 'n_group_places' field",
            form.errors["n_group_places"]
        )

        # Valid n_group_places
        valid_data.update({
            'n_group_places': 10,
        })
        form = SlotForm(data=valid_data, request=request)
        self.assertTrue(form.is_valid())

        # 'by_places' mode and correct n_group_places
        valid_data.update({
            'group_mode': Slot.BY_PLACES,
        })

        form = SlotForm(data=valid_data, request=request)
        self.assertTrue(form.is_valid())

        slot = form.save()
        slot.refresh_from_db()

        #########
        # FAILS #
        #########
        # try to lower n_places under immersions count
        immersion1 = Immersion.objects.create(
            student=self.highschool_user,
            slot=slot,
            attendance_status=1
        )

        immersion2 = Immersion.objects.create(
            student=self.highschool_user2,
            slot=slot,
            attendance_status=1
        )

        group_immersion = ImmersionGroupRecord.objects.create(
            slot=slot,
            highschool=self.high_school,
            students_count=20,
            guides_count=2,
        )

        invalid_data = {
            'id': slot.id,
            'place': Slot.FACE_TO_FACE,
            'course': self.course.id,
            'course_type': self.course_type.id,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': 'room 1',
            'date': self.today + datetime.timedelta(days=21),
            'period': self.period1,
            'start_time': datetime.time(hour=12),
            'end_time': datetime.time(hour=14),
            'n_places': 1,
            'speakers': [self.speaker1.id],
            'published': True,
            'allow_group_registrations': True,
            'allow_individual_registrations': True,
            'n_group_places': 30,
            'group_mode': Slot.ONE_GROUP,
            'public_group': True
        }

        form = SlotForm(instance=slot, data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "You can't set places value lower than actual individual immersions",
            form.errors["n_places"]
        )

        # Fail : group places lower than registered groups people (students + guides = 22)
        invalid_data.update({
            'allow_individual_registrations': True,
            'n_group_places': 20,
            'group_mode': Slot.BY_PLACES,
        })

        form = SlotForm(instance=slot, data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "You can't set group places value lower than actual registered group(s) people count",
            form.errors["n_group_places"]
        )

        # Clean actual slot for the next tests
        slot.delete()

        # Fail : group places is incorrect
        invalid_data.update({
            'n_group_places': 0,
            'allow_group_registrations': True,
        })

        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter a valid number for 'n_group_places' field", form.errors["n_group_places"])

        # Fail : allow_individual_registrations and invalid n_places
        invalid_data.update({
            'n_group_places': 10,
            'n_places': 0,
        })

        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter a valid number for 'n_places' field", form.errors["n_places"])

        # Fail : allow_individual_registrations and invalid n_places
        invalid_data.update({
            'allow_group_registrations': False,
            'allow_individual_registrations': False,
        })
        form = SlotForm(data=invalid_data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You must allow at least one of individual or group registrations", form.errors["__all__"])

    def test_HighSchoolStudentImmersionUserForm(self):
        """
        High school student user form
        """
        # Success
        request.user = self.ref_etab_user
        data = {
            'first_name': 'hello',
            'last_name': 'world'
        }
        form = HighSchoolStudentImmersionUserForm(data=data, instance=self.highschool_user)
        self.assertTrue(form.is_valid())

        # As an operator
        request.user = self.operator_user
        form = HighSchoolStudentImmersionUserForm(data=data, instance=self.highschool_user)
        self.assertTrue(form.is_valid())

        # Fail : missing last_name
        request.user = self.ref_etab_user
        data = {
            'first_name': 'hello',
        }
        form = HighSchoolStudentImmersionUserForm(data=data, instance=self.highschool_user)
        self.assertFalse(form.is_valid())
        self.assertIn("This field must be filled", form.errors["last_name"])

        # Fail : missing first_name
        data = {
            'last_name': 'hello',
        }
        form = HighSchoolStudentImmersionUserForm(data=data, instance=self.highschool_user)
        self.assertFalse(form.is_valid())
        self.assertIn("This field must be filled", form.errors["first_name"])


    def test_event_form(self):
        """
        Event form tests
        """
        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        # Event with establishment + structure
        data = {
            'establishment': self.master_establishment.id,
            'structure': self.structure.id,
            'highschool': None,
            'label': "Label test",
            'event_type': self.event_type,
            'published': True,
            'description': "Description test"
        }

        # Fail : missing speakers
        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Please add at least one speaker.", form.errors["__all__"])

        # Success
        data["speakers_list"] = '[{"username": "%s", "email": "%s"}]' % (self.speaker1.username, self.speaker1.email)
        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        event = OffOfferEvent.objects.get(establishment=self.master_establishment, structure=self.structure)
        self.assertEqual(event.speakers.first(), self.speaker1)

        # As an operator
        event.delete()
        request.user = self.operator_user
        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        event = OffOfferEvent.objects.get(establishment=self.master_establishment, structure=self.structure)
        self.assertEqual(event.speakers.first(), self.speaker1)


        # Create an Event with no structure
        # 1st try : fail (duplicate)
        request.user = self.ref_master_etab_user
        del(data["structure"])
        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        event = OffOfferEvent.objects.get(establishment=self.master_establishment, structure=None)
        self.assertEqual(event.speakers.first(), self.speaker1)

        # As an operator
        event.delete()
        request.user = self.operator_user
        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        event = OffOfferEvent.objects.get(establishment=self.master_establishment, structure=None)
        self.assertEqual(event.speakers.first(), self.speaker1)


        # Fail : duplicate
        request.user = self.ref_master_etab_user
        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("An event with these values already exists", form.errors["__all__"])

        # Fail : establishment or highschool required
        del(data["establishment"])
        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You must select one of : Establishment or High school", form.errors["__all__"])

        # As a high school manager
        request.user = self.lyc_ref

        # Error : can't choose establishment/structure
        data = {
            'establishment': self.master_establishment.id,
            'structure': self.structure.id,
            'highschool': None,
            'label': "High school event",
            'event_type': self.event_type,
            'published': True,
            'description': "Description test 2",
            "speakers_list": '[{"username": "%s", "email": "%s"}]' % (self.speaker1.username, self.speaker1.email)
        }

        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Select a valid choice. That choice is not one of the available choices.",
            form.errors["structure"]
        )
        self.assertIn(
            "Select a valid choice. That choice is not one of the available choices.",
            form.errors["establishment"]
        )
        self.assertIn("You must select one of : Establishment or High school", form.errors["__all__"])

        # Fail : no postbac_immersion on the high school
        del(data["establishment"])
        del(data["structure"])
        data["highschool"] = self.high_school
        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Select a valid choice. That choice is not one of the available choices.",
            form.errors["highschool"]
        )

        # Success
        self.high_school.postbac_immersion = True
        self.high_school.save()

        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        # As a structure manager
        request.user = self.ref_str_user

        # Error : can't choose highschool
        data = {
            'establishment': None,
            'structure': self.structure,
            'highschool': self.high_school,
            'label': "Structure event",
            'event_type': self.event_type,
            'published': True,
            'description': "Description test 2",
            "speakers_list": '[{"username": "%s", "email": "%s"}]' % (self.speaker1.username, self.speaker1.email)
        }

        form = OffOfferEventForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Select a valid choice. That choice is not one of the available choices.",
            form.errors["highschool"]
        )

        # Success
        del (data["highschool"])
        data["establishment"] = self.ref_str_user.establishment
        form = OffOfferEventForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()


    def test_off_offer_event_slot_form(self):
        """
        Event slot form tests
        """
        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        event = OffOfferEvent.objects.create(
            label="whatever",
            event_type=self.event_type,
            published=False,
            establishment=self.master_establishment,
            structure=None,
        )

        event.speakers.add(self.speaker1)

        self.assertFalse(Slot.objects.filter(event=event).exists())

        data = {
            'event': event,
            'place': Slot.FACE_TO_FACE,
            'campus': self.campus.id,
            'building': self.building.id,
            'room': "anywhere",
            'published': True,
            'date': self.today + datetime.timedelta(days=30),
            'period': self.period1,
            'start_time': datetime.time(10, 0),
            'end_time': datetime.time(12, 0),
            'n_places':20,
            'additional_information': 'whatever'
        }

        # Fail : missing speakers
        form = OffOfferEventSlotForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required", form.errors["speakers"])

        data["speakers"] = [self.speaker1]

        # Fail : date in the past
        data["date"] = self.today - datetime.timedelta(days=10)

        form = OffOfferEventSlotForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("You can't set a date in the past", form.errors["date"])

        # Good one
        data["date"] = self.today + datetime.timedelta(days=30)

        # Fail : n_places is 0
        data["n_places"] = 0
        form = OffOfferEventSlotForm(data=data, request=request)
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter a valid number for 'n_places' field", form.errors["n_places"])

        # Success
        data["n_places"] = 10

        form = OffOfferEventSlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        self.assertTrue(Slot.objects.filter(event=event).exists())
        slot = Slot.objects.get(event=event)
        self.assertEqual(slot.speakers.count(), 1)
        self.assertEqual(slot.speakers.first(), self.speaker1)

        # As an operator
        request.user = self.operator_user
        slot.delete()
        form = OffOfferEventSlotForm(data=data, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        self.assertTrue(Slot.objects.filter(event=event).exists())
        slot = Slot.objects.get(event=event)
        self.assertEqual(slot.speakers.count(), 1)
        self.assertEqual(slot.speakers.first(), self.speaker1)


    def test_attestation_document_form(self):
        request.user = self.ref_master_etab_user
        # TODO : more tests with other users

        document = AttestationDocument.objects.create(label="Test", active=True)
        lyc_w_conv_profile = Profile.objects.get(code="LYC_W_CONV")
        lyc_wo_conv_profile = Profile.objects.get(code="LYC_WO_CONV")
        visitor_profile = Profile.objects.get(code="VIS")

        data = {
            "id": document.id,
            "order": document.order,
            "label": "New label",
            "active": True,
            "profiles": [lyc_w_conv_profile.pk, ],
            "visitor_types": [],
        }

        form = AttestationDocumentForm(data=data, instance=document, request=request)
        self.assertTrue(form.is_valid())
        form.save()

        self.assertTrue(AttestationDocument.objects.filter(label='New label').exists())
        self.assertFalse(AttestationDocument.objects.filter(label='Test').exists())

        document.refresh_from_db()

        # Should fail because ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT is disabled
        data.update({
            "profiles": [lyc_w_conv_profile.pk, lyc_wo_conv_profile.pk]
        })
        form = AttestationDocumentForm(data=data, instance=document, request=request)
        form.is_valid()

        self.assertIn(
            "Select a valid choice. %s is not one of the available choices." % lyc_wo_conv_profile.pk,
            form.errors["profiles"]
        )

        self.assertFalse(form.is_valid())

        document.refresh_from_db()

        # visitor type without VIS profile
        data.update({
            "profiles": [lyc_w_conv_profile.pk, ],
            "visitor_types": [self.visitor_type.pk, ]
        })

        form = AttestationDocumentForm(data=data, instance=document, request=request)
        form.is_valid()
        self.assertIn("Visitor profile is mandatory when adding visitor types", form.errors["__all__"])
        self.assertFalse(form.is_valid())

        # No profile
        data.update({
            "profiles": [],
            "visitor_types": [],
        })
        form = AttestationDocumentForm(data=data, instance=document, request=request)
        form.is_valid()
        self.assertIn("At least one profile is required", form.errors["__all__"])
        self.assertFalse(form.is_valid())

        # VIS profile + visitor type => success
        data["profiles"] = [visitor_profile, ]
        data["visitor_types"] = [self.visitor_type, ]
        form = AttestationDocumentForm(data=data, instance=document, request=request)
        self.assertTrue(form.is_valid())


    def test_my_highschool_form_update(self):
        """
        Test high school update as a high school manager
        Some fields should not change
        """
        request.user = self.lyc_ref
        highschool = self.high_school

        data = {
            'country': 'DE',
            'address': 'elsewhere',
            'address2': 'addr2',
            'address3': 'addr3',
            'department': '72',
            'city': 'LE MANS',
            'zip_code': '72000',
            'phone_number': '987654321',
            'fax': '147258369',
            'email': 'referent@lemans.fr',
            'head_teacher_name': 'M. Jean Jacques',
        }

        form = MyHighSchoolForm(data=data, instance=highschool, request=request)
        # Need to populate choices fields (ajax populated IRL)
        form.fields['city'].choices = [('LE MANS', 'LE MANS')]
        form.fields['zip_code'].choices = [('72000', '72100')]

        self.assertTrue(form.is_valid())
        form.save()
        highschool.refresh_from_db()

        # Fields that must have changed
        self.assertEqual(highschool.country, 'DE')
        self.assertEqual(highschool.address, 'elsewhere')
        self.assertEqual(highschool.address2, 'addr2')
        self.assertEqual(highschool.address3, 'addr3')
        self.assertEqual(highschool.department, '72')
        self.assertEqual(highschool.city, 'LE MANS')
        self.assertEqual(highschool.zip_code, '72000')
        self.assertEqual(highschool.phone_number, '987654321')
        self.assertEqual(highschool.fax, '147258369')
        self.assertEqual(highschool.email, 'referent@lemans.fr')
        self.assertEqual(highschool.head_teacher_name, 'M. Jean Jacques')
        self.assertEqual(highschool.mailing_list, 'my-top@mailing-list.fr')

        # Fields that must not
        self.assertEqual(highschool.label, 'HS1')
        self.assertEqual(highschool.convention_start_date, timezone.localdate() - datetime.timedelta(days=2))
        self.assertEqual(highschool.convention_end_date, timezone.localdate() + datetime.timedelta(days=2))
        self.assertEqual(highschool.with_convention, True)
        self.assertEqual(highschool.uses_agent_federation, True)
        self.assertEqual(highschool.uses_student_federation, True)
        self.assertEqual(highschool.active, True)
        self.assertEqual(highschool.allow_individual_immersions, True)
        self.assertEqual(highschool.postbac_immersion, False)
        self.assertEqual(highschool.uai_codes.count(), 1)
        self.assertEqual(highschool.uai_codes.first(), UAI.objects.get(pk='0670003P'))

