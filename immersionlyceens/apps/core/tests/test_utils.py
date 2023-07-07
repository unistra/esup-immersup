"""
Core utils tests
"""
import json
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token


from immersionlyceens.apps.core.models import (
    AccompanyingDocument, AttestationDocument, BachelorMention, BachelorType,
    Building, Campus, CancelType, Course, CourseType, Establishment,
    GeneralBachelorTeaching, GeneralSettings, HigherEducationInstitution,
    HighSchool, HighSchoolLevel, Immersion, ImmersionUser, MailTemplate,
    MailTemplateVars, OffOfferEvent, OffOfferEventType, Period,
    PostBachelorLevel, Profile, Slot, Structure, StudentLevel, Training,
    TrainingDomain, TrainingSubdomain, UserCourseAlert, Vacation, Visit,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument,
    HighSchoolStudentRecordQuota, StudentRecord, VisitorRecord,
    VisitorRecordDocument, VisitorRecordQuota,
)

request_factory = RequestFactory()
request = request_factory.get('/admin')

class UtilsTestCase(TestCase):
    """Tests for API"""

    # 'group', 'group_permissions'

    fixtures = [
        'generalsettings', 'high_school_levels', 'student_levels', 'post_bachelor_levels',
        'mailtemplatevars', 'mailtemplate', 'higher'
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """

        cls.today = timezone.now()
        cls.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        cls.establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test@test.com',
            mailing_list='test@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first()
        )

        cls.establishment2 = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test2@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last()
        )

        cls.establishment3 = Establishment.objects.create(
            code='ETA3',
            label='Etablissement 3',
            short_label='Eta 3',
            active=True,
            master=False,
            email='test3@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.get(pk='0062120X'),
            data_source_plugin="LDAP"
        )

        cls.structure = Structure.objects.create(
            label="test structure",
            code="STR",
            establishment=cls.establishment,
            mailing_list="structure@no-reply.com"
        )

        cls.structure2 = Structure.objects.create(
            label="test structure 2",
            code="STR2",
            establishment=cls.establishment2
        )

        cls.structure3 = Structure.objects.create(
            label="test structure 3",
            code="STR3",
            establishment=cls.establishment3
        )

        cls.bachelor_mention = BachelorMention.objects.create(
            label="s2tmd",
            active=True
        )

        cls.bachelor_mention2 = BachelorMention.objects.create(
            label="Anything",
            active=True
        )

        cls.bachelor_teaching = GeneralBachelorTeaching.objects.create(
            label="Série A",
            active=True
        )

        cls.bachelor_teaching2 = GeneralBachelorTeaching.objects.create(
            label="Whatever",
            active=True
        )

        cls.high_school = HighSchool.objects.create(
            label='HS1',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='a@b.c',
            mailing_list='a@b.c',
            head_teacher_name='M. A B',
            convention_start_date=cls.today - timedelta(days=10),
            convention_end_date=cls.today + timedelta(days=10),
            postbac_immersion=True,
            signed_charter=True,
        )

        cls.visit = Visit.objects.first()

        cls.visitor = get_user_model().objects.create_user(
            username="visitor",
            password="pass",
            email="visitor@no-reply.com",
            first_name="Godefroy",
            last_name="De Montmirail",
        )
        cls.visitor.set_password("pass")
        cls.visitor.save()

        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='ref_etab@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=cls.establishment
        )
        cls.ref_etab_user.set_password('pass')
        cls.ref_etab_user.save()

        cls.ref_etab3_user = get_user_model().objects.create_user(
            username='ref_etab3',
            password='pass',
            email='ref_etab3@no-reply.com',
            first_name='ref_etab3',
            last_name='ref_etab3',
            establishment=cls.establishment3
        )
        cls.ref_etab3_user.set_password('pass')
        cls.ref_etab3_user.save()

        cls.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='ref_master_etab@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=cls.establishment
        )
        cls.ref_master_etab_user.set_password('pass')
        cls.ref_master_etab_user.save()

        cls.operator_user = get_user_model().objects.create_user(
            username='operator',
            password='pass',
            email='operator@no-reply.com',
            first_name='operator',
            last_name='operator'
        )
        cls.operator_user.set_password('pass')
        cls.operator_user.save()

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )
        cls.highschool_user.set_password('pass')
        cls.highschool_user.save()

        cls.highschool_user2 = get_user_model().objects.create_user(
            username='hs2',
            password='pass',
            email='hs2@no-reply.com',
            first_name='high2',
            last_name='SCHOOL2',
        )
        cls.highschool_user2.set_password('pass')
        cls.highschool_user2.save()

        cls.highschool_user3 = get_user_model().objects.create_user(
            username='hs3', password='pass',
            email='hs3@no-reply.com',
            first_name='high3',
            last_name='SCHOOL3',
        )
        cls.highschool_user3.set_password('pass')
        cls.highschool_user3.save()

        cls.ref_str = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
            establishment=cls.establishment,
        )
        cls.ref_str2 = get_user_model().objects.create_user(
            username='ref_str2',
            password='pass',
            email='ref_str2@no-reply.com',
            first_name='ref_str2',
            last_name='ref_str2',
            establishment=cls.establishment,
        )
        cls.ref_str2.set_password("pass")

        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            establishment=cls.establishment,
        )
        cls.highschool_speaker = get_user_model().objects.create_user(
            username='highschool_speaker',
            password='pass',
            email='highschool_speaker@no-reply.com',
            first_name='highschool_speaker',
            last_name='highschool_speaker',
            highschool=cls.high_school
        )
        cls.ref_lyc = get_user_model().objects.create_user(
            username='ref_lyc',
            password='pass',
            email='lycref-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
            highschool=cls.high_school
        )
        cls.student = get_user_model().objects.create_user(
            username='student',
            password='pass',
            email='student@no-reply.com',
            first_name='student',
            last_name='STUDENT',
        )
        cls.student2 = get_user_model().objects.create_user(
            username='student2',
            password='pass',
            email='student2@no-reply.com',
            first_name='student2',
            last_name='STUDENT2',
        )
        cls.visitor_user = get_user_model().objects.create_user(
            username='visitor666',
            password='pass',
            email='visitor666@no-reply.com',
            first_name='visitor666',
            last_name='VISITOR666',
        )
        cls.cons_str = get_user_model().objects.create_user(
            username='cons_str',
            password='pass',
            email='cons_str@no-reply.com',
            first_name='cons_str',
            last_name='cons_str',
            establishment=cls.establishment,
        )
        cls.api_user = get_user_model().objects.create_user(
            username='api',
            password='pass',
            email='api@no-reply.com',
            first_name='api',
            last_name='api'
        )
        cls.api_user.set_password('pass')
        cls.api_user.save()

        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user)
        Group.objects.get(name='REF-TEC').user_set.add(cls.operator_user)
        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='INTER').user_set.add(cls.highschool_speaker)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str2)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user2)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user3)
        Group.objects.get(name='ETU').user_set.add(cls.student)
        Group.objects.get(name='ETU').user_set.add(cls.student2)
        Group.objects.get(name='REF-LYC').user_set.add(cls.ref_lyc)
        Group.objects.get(name='VIS').user_set.add(cls.visitor)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab3_user)
        Group.objects.get(name='CONS-STR').user_set.add(cls.cons_str)

        cls.ref_str.structures.add(cls.structure)
        cls.ref_str2.structures.add(cls.structure2)
        cls.cons_str.structures.add(cls.structure)
        cls.cons_str.structures.add(cls.structure2)

        cls.cancel_type = CancelType.objects.create(label='Hello world')

        cls.past_period = Period.objects.create(
            label="Past Period",
            registration_start_date=cls.today - timedelta(days=10),
            immersion_start_date=cls.today - timedelta(days=9),
            immersion_end_date=cls.today,
            allowed_immersions = 4,
        )

        cls.period = Period.objects.create(
            label="Period 1",
            registration_start_date=cls.today, # + timedelta(days=1),
            immersion_start_date=cls.today + timedelta(days=2),
            immersion_end_date=cls.today + timedelta(days=20),
            allowed_immersions=4,
        )

        cls.vac = Vacation.objects.create(
            label="vac",
            start_date=cls.today - timedelta(days=2),
            end_date=cls.today + timedelta(days=2)
        )

        cls.t_domain = TrainingDomain.objects.create(label="test t_domain")
        cls.t_sub_domain = TrainingSubdomain.objects.create(
            label="test t_sub_domain",
            training_domain=cls.t_domain
        )
        cls.training = Training.objects.create(label="test training")
        cls.training2 = Training.objects.create(label="test training 2")
        cls.highschool_training = Training.objects.create(
            label="test highschool training",
            highschool=cls.high_school
        )
        cls.training.training_subdomains.add(cls.t_sub_domain)
        cls.training2.training_subdomains.add(cls.t_sub_domain)
        cls.highschool_training.training_subdomains.add(cls.t_sub_domain)
        cls.training.structures.add(cls.structure)
        cls.training2.structures.add(cls.structure)

        cls.highschool_course = Course.objects.create(
            label="course 1",
            training=cls.highschool_training,
            highschool=cls.high_school
        )
        cls.highschool_course.speakers.add(cls.highschool_speaker)

        cls.campus = Campus.objects.create(
            label='Esplanade',
            establishment=cls.establishment,
            department='67',
            zip_code='67000',
            city='STRASBOURG',
            active=True
        )
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')

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

    def setUp(self):
        self.client = Client()
        self.client.login(username='ref_etab', password='pass')

        self.course = Course.objects.create(
            label="course 1",
            training=self.training,
            structure=self.structure
        )
        self.course.speakers.add(self.speaker1)

        self.slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 1',
            date=self.today,
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.slot2 = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=3),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.slot3 = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=3),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.highschool_slot = Slot.objects.create(
            course=self.highschool_course,
            course_type=self.course_type,
            room='room 212',
            date=self.today,
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="High school additional information"
        )
        self.full_slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=3),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=0,
            additional_information="Hello there!"
        )
        self.past_slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today - timedelta(days=1),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.passed_registration_date_slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=2),
            registration_limit_delay=72,
            cancellation_limit_delay=72,
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.unpublished_slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=2),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            published=False,
            additional_information="Hello there!"
        )
        self.slot.speakers.add(self.speaker1),
        self.past_slot.speakers.add(self.speaker1),
        self.slot2.speakers.add(self.speaker1),
        self.highschool_slot.speakers.add(self.highschool_speaker),

        self.highschool_restricted_level = HighSchoolLevel.objects.create(label="level label")
        self.highschool_level_restricted_slot = Slot.objects.create(
            course=self.highschool_course,
            course_type=self.course_type,
            room='room 237',
            date=self.today + timedelta(days=2),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="High school additional information",
            levels_restrictions=True
        )

        self.highschool_level_restricted_slot.allowed_highschool_levels.add(
            self.highschool_restricted_level
        )

        # Bachelor restricted slot
        self.bachelor_restricted_slot = Slot.objects.create(
            course=self.highschool_course,
            course_type=self.course_type,
            room='room 1',
            date=self.today + timedelta(days=2),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="High school additional information",
            bachelors_restrictions=True
        )

        self.bachelor_restricted_slot.allowed_bachelor_types.add(
            BachelorType.objects.get(label__iexact='général')
        )

        self.hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=2),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True
        )

        # Set custom quota for this student
        HighSchoolStudentRecordQuota.objects.create(
            record=self.hs_record,
            period=self.past_period,
            allowed_immersions=2,
        )

        HighSchoolStudentRecordQuota.objects.create(
            record=self.hs_record,
            period=self.period,
            allowed_immersions=1
        )

        self.hs_record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school,
            birth_date=datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=3),
            class_name='TS 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True
        )
        self.student_record = StudentRecord.objects.create(
            student=self.student,
            uai_code='0673021V',  # Université de Strasbourg
            institution=HigherEducationInstitution.objects.get(uai_code__iexact='0673021V'),
            birth_date=datetime.today(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=BachelorType.objects.get(label__iexact='général'),
        )
        self.student_record2 = StudentRecord.objects.create(
            student=self.student2,
            uai_code='0597065J',  # Université de Lille
            institution=HigherEducationInstitution.objects.get(uai_code__iexact='0597065J'),
            birth_date=datetime.today(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=BachelorType.objects.get(label__iexact='général')
        )
        self.visitor_record = VisitorRecord.objects.create(
            visitor=self.visitor,
            birth_date=datetime.today(),
            validation=1,
        )

        self.slot4 = Slot.objects.create(
            visit=Visit.objects.first(),
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=2),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )

        self.immersion = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.slot,
        )
        self.immersion2 = Immersion.objects.create(
            student=self.student,
            slot=self.slot
        )
        self.immersion3 = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.past_slot,
        )
        self.immersion4 = Immersion.objects.create(
            student=self.visitor_user,
            slot=self.slot4,
        )
        self.mail_t = MailTemplate.objects.create(
            code="code",
            label="label",
            description="description",
            subject="subject",
            body="body",
        )
        self.var = MailTemplateVars.objects.create(
            code='code',
            description='description'
        )
        self.mail_t.available_vars.add(self.var)
        self.alert = UserCourseAlert.objects.create(
            email=self.student.email,
            course=self.course
        )

        self.event_type = OffOfferEventType.objects.create(label="Event type label")

        self.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        self.token = Token.objects.create(user=self.ref_master_etab_user)
        self.client_token = Client(HTTP_AUTHORIZATION=f" Token {self.token.key}")

        self.api_token = Token.objects.create(user=self.api_user)
        self.api_client_token = Client(HTTP_AUTHORIZATION=f" Token {self.api_token.key}")


    def test_get_slots(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/core/utils/slots"
        data = {
            'training_id': self.training.id,
            'past': "true",
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 7)
        slot = content['data'][0]
        self.assertEqual(slot['id'], self.past_slot.id)
        self.assertEqual(slot['published'], self.past_slot.published)
        self.assertEqual(slot['course_label'], self.past_slot.course.label)
        self.assertEqual(slot['structure_code'], self.past_slot.course.structure.code)
        self.assertTrue(slot['structure_managed_by_me'])
        self.assertEqual(slot['course_type_label'], self.past_slot.course_type.label)
        self.assertEqual(slot['date'], (self.today - timedelta(days=1)).strftime("%Y-%m-%d"))
        self.assertEqual(slot['start_time'], '12:00:00')
        self.assertEqual(slot['end_time'], '14:00:00')
        self.assertEqual(slot['campus_label'], self.past_slot.campus.label)
        self.assertEqual(slot['building_label'], self.past_slot.building.label)
        self.assertEqual(slot['room'], self.past_slot.room)
        self.assertEqual(slot['n_register'], self.past_slot.registered_students())
        self.assertEqual(slot['n_places'], self.past_slot.n_places)

        # With no training id : no result
        # Todo : redefine test data
        data = {}
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error : a valid training must be selected")

        # Logged as structure manager
        client = Client()
        client.login(username='ref_str', password='pass')
        data = {'training_id': self.training.id}
        response = client.get(url, data, **self.header)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 7)

        # Logged as highschool manager
        client = Client()
        client.login(username='ref_lyc', password='pass')
        data = {'training_id': self.training.id}
        response = client.get(url, data, **self.header)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 7)


    def test_get_my_slots(self):
        client = Client()
        url = "/core/utils/slots?visits=false"
        # as a high school speaker
        client.login(username='highschool_speaker', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.highschool_slot.id, s['id'])
        self.assertEqual(self.highschool_slot.published, s['published'])
        self.assertEqual(self.high_school.city, s['highschool_city'])
        self.assertEqual(self.high_school.label, s['highschool_label'])
        self.assertEqual(self.highschool_slot.course.training.label, s['course_training_label'])
        self.assertEqual(self.highschool_slot.course_type.label, s['course_type_label'])
        self.assertEqual(self.highschool_slot.course_type.full_label, s['course_type_full_label'])
        self.assertEqual(s['campus_label'], None)
        self.assertEqual(self.highschool_slot.room, s['room'])
        self.assertEqual(self.highschool_slot.date.strftime("%Y-%m-%d"), s['date'])
        self.assertEqual(self.highschool_slot.start_time.strftime("%H:%M:%S"), s['start_time'])
        self.assertEqual(self.highschool_slot.end_time.strftime("%H:%M:%S"), s['end_time'])

        # as a "structure" speaker
        request.user = self.speaker1
        client.login(username='speaker1', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.past_slot.id, s['id'])
        self.assertEqual(self.past_slot.published, s['published'])
        self.assertEqual(self.past_slot.course.structure.code, s['structure_code'])
        self.assertEqual(self.past_slot.course.training.label, s['course_training_label'])
        self.assertEqual(self.past_slot.course_type.label, s['course_type_label'])
        self.assertEqual(self.past_slot.course_type.full_label, s['course_type_full_label'])
        self.assertEqual(self.past_slot.campus.label, s['campus_label'])
        self.assertEqual(self.past_slot.building.label, s['building_label'])

        self.assertEqual(self.past_slot.room, s['room'])

        self.assertEqual(self.past_slot.date.strftime("%Y-%m-%d"), s['date'])
        self.assertEqual(self.past_slot.start_time.strftime("%H:%M:%S"), s['start_time'])
        self.assertEqual(self.past_slot.end_time.strftime("%H:%M:%S"), s['end_time'])

        self.assertEqual(self.past_slot.course.label, s['course_label'])
        # TODO: speakers
        self.assertEqual(self.past_slot.n_places, s['n_places'])
        self.assertEqual(self.past_slot.registered_students(), s['n_register'])
        self.assertEqual(self.past_slot.additional_information, s['additional_information'])

        # Past Slots
        self.slot.date = self.today - timedelta(days=10)
        self.slot.save()
        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.slot.id, s['id'])

        # No immersion
        self.slot.date = self.today - timedelta(days=10)
        self.slot.save()
        self.immersion.delete()
        self.immersion2.delete()

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)


    def test_get_visits_slots(self):
        visit = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever",
            published=True
        )

        slot = Slot.objects.create(
            visit=visit,
            room='Here',
            date=self.today + timedelta(days=1),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )

        self.client.login(username='ref_etab', password='pass')
        data = {
            'visits': True
        }
        response = self.client.get(reverse('get_slots'), {'visits': 'true'}, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], slot.id)
        self.assertEqual(content['data'][0]['visit_id'], slot.visit.id)
        self.assertEqual(content['data'][0]['visit_purpose'], slot.visit.purpose)
        self.assertEqual(content['data'][0]['establishment_code'], slot.visit.establishment.code)
        self.assertEqual(content['data'][0]['establishment_label'], slot.visit.establishment.label)
        self.assertEqual(content['data'][0]['establishment_short_label'], slot.visit.establishment.short_label)
        self.assertEqual(content['data'][0]['structure_code'], slot.visit.structure.code)
        self.assertEqual(content['data'][0]['structure_label'], slot.visit.structure.label)
        self.assertEqual(content['data'][0]['highschool_city'], slot.visit.highschool.city)
        self.assertEqual(content['data'][0]['highschool_label'], slot.visit.highschool.label)


    def test_get_events_slots(self):
        event = OffOfferEvent.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            event_type=self.event_type,
            label="Whatever",
            description="The event description",
            published=True
        )

        slot = Slot.objects.create(
            event=event,
            room='Here',
            date=self.today + timedelta(days=1),
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )

        self.client.login(username='ref_etab', password='pass')
        data = {
            'events': True
        }
        response = self.client.get(reverse('get_slots'), {'events': 'true'}, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], slot.id)
        self.assertEqual(content['data'][0]['event_id'], slot.event.id)
        self.assertEqual(content['data'][0]['event_label'], slot.event.label)
        self.assertEqual(content['data'][0]['event_type_label'], slot.event.event_type.label)
        self.assertEqual(content['data'][0]['establishment_code'], slot.event.establishment.code)
        self.assertEqual(content['data'][0]['establishment_label'], slot.event.establishment.label)
        self.assertEqual(content['data'][0]['establishment_short_label'], slot.event.establishment.short_label)
        self.assertEqual(content['data'][0]['structure_code'], slot.event.structure.code)
        self.assertEqual(content['data'][0]['structure_label'], slot.event.structure.label)
        self.assertEqual(content['data'][0]['highschool_city'], slot.event.highschool.city)
        self.assertEqual(content['data'][0]['highschool_label'], slot.event.highschool.label)
        self.assertEqual(content['data'][0]['event_description'], slot.event.description)

    def test_set_training_quota(self):
        url = reverse('set_training_quota')

        data = {
            'id': self.training.id,
            'value': 4
        }

        self.assertEqual(self.training.allowed_immersions, None)
        self.client.post(url, data, **self.header)

        self.training.refresh_from_db()
        self.assertEqual(self.training.allowed_immersions, 4)

        # other structure : no access
        self.client.logout()
        self.client.login(username='ref_str2', password='pass')

        data['value'] = 2

        response = self.client.post(url, data, **self.header)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result["error"], "You are not allowed to set quota for this training")

        self.training.refresh_from_db()
        self.assertEqual(self.training.allowed_immersions, 4)