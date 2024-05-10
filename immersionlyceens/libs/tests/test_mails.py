"""
Mails tests
"""
import datetime
import uuid

from django.core import management
from django.contrib.auth import get_user_model
from django.utils.formats import date_format
from django.utils import timezone
from django.urls import reverse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.conf import settings
from django.contrib.auth.models import Group

from immersionlyceens.libs.utils import get_general_setting
from ..mails.variables_parser import parser

from immersionlyceens.apps.core.models import (
    AttestationDocument, BachelorType, UniversityYear, MailTemplate,
    Structure, Slot, Course, TrainingDomain, TrainingSubdomain, Campus,
    Building, CourseType, Training, Vacation, HighSchool, Immersion,
    EvaluationFormLink, EvaluationType, CancelType, HighSchoolLevel,
    StudentLevel, Period, PostBachelorLevel, Profile, Establishment,
    HigherEducationInstitution, PendingUserGroup
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, HighSchoolStudentRecordDocument

class MailsTestCase(TestCase):
    """Mail templates tests"""

    fixtures = ['group', 'evaluationtype', 'canceltype', 'high_school_levels', 'post_bachelor_levels',
                'student_levels', 'higher']

    @classmethod
    def setUpTestData(cls):
        management.call_command("restore_group_rights")

        cls.today = timezone.now()

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
            convention_start_date=cls.today - datetime.timedelta(days=10),
            convention_end_date=cls.today + datetime.timedelta(days=10),
            signed_charter=True,
        )

        cls.highschool_user = get_user_model().objects.create_user(
            username='the_username',
            password='pass',
            email='hs@no-reply.com',
            first_name='Jean',
            last_name='MICHEL',
        )

        cls.highschool_user.set_validation_string()
        cls.highschool_user.destruction_date = cls.today.date() + datetime.timedelta(days=settings.DESTRUCTION_DELAY)
        cls.highschool_user.save()

        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            highschool=cls.high_school,
        )

        cls.speaker2 = get_user_model().objects.create_user(
            username='speaker2',
            password='pass',
            email='speaker-immersion2@no-reply.com',
            first_name='Jean',
            last_name='Philippe',
            establishment=cls.establishment,
        )

        cls.ref_str = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
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

        cls.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=cls.today.date() + datetime.timedelta(days=1),
            end_date=cls.today.date() + datetime.timedelta(days=10),
            registration_start_date=cls.today.date() + datetime.timedelta(days=1),
            active=True,
        )

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='INTER').user_set.add(cls.speaker2)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str)

        cls.period1 = Period.objects.create(
            label='period 1',
            immersion_start_date=cls.today - datetime.timedelta(days=9),
            immersion_end_date=cls.today + datetime.timedelta(days=10),
            registration_start_date=cls.today - datetime.timedelta(days=10),
            allowed_immersions=4,
        )
        cls.vac = Vacation.objects.create(
            label="vac",
            start_date=cls.today - datetime.timedelta(days=2),
            end_date=cls.today + datetime.timedelta(days=2)
        )
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
            department=67,
            city='Strasbourg',
            zip_code='67000'
        )
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM', full_label='Cours magistral')
        cls.slot = Slot.objects.create(
            course=cls.course,
            course_type=cls.course_type,
            campus=cls.campus,
            building=cls.building,
            room='room 1',
            date=cls.today,
            period=cls.period1,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        cls.slot2 = Slot.objects.create(
            course=cls.course,
            course_type=cls.course_type,
            campus=cls.campus,
            building=cls.building,
            room='room 2',
            date=cls.today,
            period=cls.period1,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        cls.slot.speakers.add(cls.speaker1),
        cls.slot2.speakers.add(cls.speaker1),

        cls.hs_record = HighSchoolStudentRecord.objects.create(
            student=cls.highschool_user,
            highschool=cls.high_school,
            birth_date=datetime.datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=1),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
            validation=1,
        )

        cls.immersion = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot,
        )

        cls.slot_eval_type = EvaluationType.objects.get(code='EVA_CRENEAU')
        cls.global_eval_type = EvaluationType.objects.get(code='EVA_DISPOSITIF')

        cls.slot_eval_link = EvaluationFormLink.objects.create(
            evaluation_type=cls.slot_eval_type, active=True, url='http://slot.evaluation.test/')
        cls.global_eval_link = EvaluationFormLink.objects.create(
            evaluation_type=cls.global_eval_type, active=True, url='http://disp.evaluation.test/')

        # Attestations
        cls.attestation_1 = AttestationDocument.objects.create(
            label='Test label',
            mandatory=True,
            active=True,
            for_minors=True,
            requires_validity_date=True
        )

        cls.attestation_1.profiles.add(Profile.objects.get(code='LYC_W_CONV'))
        cls.attestation_1.profiles.add(Profile.objects.get(code='LYC_WO_CONV'))
        cls.attestation_1.profiles.add(Profile.objects.get(code='VIS'))

        cls.attestation_2 = AttestationDocument.objects.create(
            label='Test label 2',
            mandatory=True,
            active=True,
            for_minors=False,
            requires_validity_date=True
        )

        cls.attestation_2.profiles.add(Profile.objects.get(code='VIS'))

        cls.hs_record_document=HighSchoolStudentRecordDocument.objects.create(
            record=cls.hs_record,
            attestation=cls.attestation_1,
            mandatory=True,
            for_minors=False,
            requires_validity_date=True,
            validity_date=cls.today.date() + datetime.timedelta(days=5)
        )


    def test_variables(self):
        # user : ${prenom} ${nom} ${jourDestructionCptMin} ${lienValidation} ${identifiant}
        # university year : ${annee}

        message_body = MailTemplate.objects.get(code='CPT_MIN_CREATE')
        parsed_body = parser(message_body.body, user=self.highschool_user)

        self.assertIn(self.highschool_user.first_name, parsed_body)
        self.assertIn(self.highschool_user.last_name, parsed_body)
        self.assertIn(self.highschool_user.validation_string, parsed_body)
        self.assertIn(self.highschool_user.username, parsed_body)
        self.assertIn(self.highschool_user.get_localized_destruction_date(), parsed_body)
        self.assertIn(self.university_year.label, parsed_body)

        # Slots
        message_body = MailTemplate.objects.get(code='IMMERSION_RAPPEL')
        parsed_body = parser(message_body.body, user=self.highschool_user, slot=self.slot)

        self.assertIn(self.highschool_user.first_name, parsed_body)
        self.assertIn(self.highschool_user.last_name, parsed_body)
        self.assertIn(self.slot.building.label, parsed_body)
        self.assertIn(self.slot.campus.label, parsed_body)
        self.assertIn(self.slot.course.label, parsed_body)
        self.assertIn(self.slot.course.training.label, parsed_body)
        self.assertIn(date_format(self.slot.date), parsed_body)
        self.assertIn(self.slot.additional_information, parsed_body)
        self.assertIn(self.slot.room, parsed_body)
        self.assertIn(self.slot.start_time.strftime("%-Hh%M"), parsed_body)
        self.assertIn(self.slot.end_time.strftime("%-Hh%M"), parsed_body)

        # Slots : registered users list
        message_body = MailTemplate.objects.get(code='IMMERSION_RAPPEL_INT')
        parsed_body = parser(message_body.body, user=self.speaker1, slot=self.slot)

        self.assertIn(self.speaker1.first_name, parsed_body)
        self.assertIn(self.speaker1.last_name, parsed_body)
        self.assertIn(self.highschool_user.first_name, parsed_body)
        self.assertIn(self.highschool_user.last_name, parsed_body)

        # Slots : slot list
        message_body = MailTemplate.objects.get(code='RAPPEL_STRUCTURE')
        parsed_body = parser(message_body.body, user=self.ref_str, slot_list=[self.slot])
        self.assertIn(self.slot.course.label, parsed_body)
        self.assertIn(self.slot.course_type.label, parsed_body)
        self.assertIn(self.slot.building.label, parsed_body)
        self.assertIn(self.slot.room, parsed_body)
        self.assertIn(self.speaker1.last_name, parsed_body)

        # Slots : availability
        message_body = MailTemplate.objects.get(code='ALERTE_DISPO')
        parsed_body = parser(message_body.body, user=self.highschool_user, course=self.slot.course,
                             slot_list=[self.slot])
        self.assertIn(self.slot.course.label, parsed_body)

        # Slots : evaluation
        message_body = MailTemplate.objects.get(code='EVALUATION_CRENEAU')
        parsed_body = parser(message_body.body, user=self.highschool_user, slot=self.slot)
        self.assertIn(self.slot_eval_link.url, parsed_body)
        self.assertIn(self.slot.course_type.full_label, parsed_body)

        # self.assertIn(self.speaker1.last_name, parsed_body)

        # highschool
        message_body = MailTemplate.objects.get(code='CPT_AVALIDER_LYCEE')
        parsed_body = parser(message_body.body, user=self.lyc_ref, slot=self.slot)

        self.assertIn(self.lyc_ref.first_name, parsed_body)
        self.assertIn(self.lyc_ref.last_name, parsed_body)
        self.assertIn(self.high_school.label, parsed_body)
        self.assertIn(get_general_setting("PLATFORM_URL"), parsed_body)

        # high school referent account creation : check recovery string
        self.lyc_ref.set_recovery_string()
        message_body = MailTemplate.objects.get(code='CPT_CREATE')
        parsed_body = parser(message_body.body, user=self.lyc_ref)
        self.assertIn(self.lyc_ref.recovery_string, parsed_body)

        # Global evaluation
        message_body = MailTemplate.objects.get(code='EVALUATION_GLOBALE')
        parsed_body = parser(message_body.body, user=self.highschool_user)
        self.assertIn(self.global_eval_link.url, parsed_body)

        # Slot cancellation
        canceltype = CancelType.objects.all().first()
        self.immersion.cancellation_type = canceltype
        self.immersion.save()

        message_body = MailTemplate.objects.get(code='IMMERSION_ANNUL')
        parsed_body = parser(message_body.body, user=self.highschool_user, immersion=self.immersion)
        self.assertIn(self.immersion.cancellation_type.label, parsed_body)

        # Account links
        pending = PendingUserGroup.objects.create(
            immersionuser1=self.speaker1,
            immersionuser2=self.speaker2,
            validation_string=uuid.uuid4().hex
        )

        platform_url = get_general_setting("PLATFORM_URL")
        url = reverse("immersion:link", kwargs={'hash': pending.validation_string})

        message_body = MailTemplate.objects.get(code='CPT_FUSION')
        parsed_body = parser(
            message_body.body,
            link_validation_string=pending.validation_string,
            link_source_user=self.speaker1
        )
        self.assertIn(f"{self.speaker1.last_name} {self.speaker1.first_name}", parsed_body)
        self.assertIn(f"{platform_url}{url}", parsed_body)

        # Attestations renewal
        message_body = MailTemplate.objects.get(code='CPT_DEPOT_PIECE')

        parsed_body = parser(
            message_body.body,
            user=self.highschool_user
        )
        self.assertIn(self.attestation_1.label, parsed_body)


    def test_condition(self):
        message_body = "{% if prenom == 'Jean' %}Hello{% else %}World{% endif %}"
        parsed_body = parser(message_body, user=self.highschool_user)

        self.assertEqual("Hello", parsed_body)

        self.highschool_user.first_name = "dsfgfd"
        parsed_body = parser(message_body, user=self.highschool_user)
        self.assertEqual("World", parsed_body)
