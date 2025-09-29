"""
Django API tests suite
"""
import csv
import json
import unittest
import codecs

from datetime import datetime, time, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.core import mail
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _, pgettext
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from django.conf import settings

from immersionlyceens.apps.core.models import (
    AccompanyingDocument, AttestationDocument, BachelorMention, BachelorType,
    Building, Campus, CancelType, Course, CourseType, Establishment,
    GeneralBachelorTeaching, GeneralSettings, HigherEducationInstitution,
    HighSchool, HighSchoolLevel, Immersion, ImmersionUser, MailTemplate,
    MailTemplateVars, OffOfferEvent, OffOfferEventType, Period,
    PostBachelorLevel, Profile, RefStructuresNotificationsSettings,
    Slot, Structure, StudentLevel, Training,
    TrainingDomain, TrainingSubdomain, UserCourseAlert, Vacation,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument,
    HighSchoolStudentRecordQuota, StudentRecord, VisitorRecord,
    VisitorRecordDocument, VisitorRecordQuota,
)
from immersionlyceens.libs.utils import get_general_setting
from immersionlyceens.libs.api.accounts.rest import AccountAPI

from .mocks import mocked_ldap_connection, mocked_search_user, mocked_ldap_bind

request_factory = RequestFactory()
request = request_factory.get('/admin')


class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['high_school_levels', 'student_levels', 'post_bachelor_levels', 'higher', 'tests_uai']

    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """

        cls.today = timezone.localtime()
        cls.today_utc_offset = cls.today.utcoffset()
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

        cls.notification = RefStructuresNotificationsSettings.objects.create(
            user=cls.ref_str
        )

        cls.notification.structures.add(cls.structure)

        cls.ref_str2 = get_user_model().objects.create_user(
            username='ref_str2',
            password='pass',
            email='ref_str2@no-reply.com',
            first_name='ref_str2',
            last_name='ref_str2',
            establishment=cls.establishment,
        )
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

        cls.period2 = Period.objects.create(
            label="Period 2",
            registration_start_date=cls.today,  # + timedelta(days=1),
            immersion_start_date=cls.today - timedelta(days=1),
            immersion_end_date=cls.today + timedelta(days=1),
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

        self.event_type = OffOfferEventType.objects.create(label="Event type label")

        self.course = Course.objects.create(
            label="course 1",
            training=self.training,
            structure=self.structure
        )
        self.course.speakers.add(self.speaker1)

        """
        self.event = OffOfferEvent.objects.create(
            label="event 1",
            event_type=self.event_type,
            structure=self.structure
        )
        """
        self.course.speakers.add(self.speaker1)

        self.slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 1',
            date=self.today,
            period=self.period2,
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
            period=self.period,
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
            period=self.period,
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
            period=self.period2,
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
            period=self.period,
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
            period=self.period2,
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
            period=self.period,
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
            period=self.period,
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
            period=self.period,
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
            period=self.period,
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
            validation=StudentRecord.TO_COMPLETE
        )
        self.student_record2 = StudentRecord.objects.create(
            student=self.student2,
            uai_code='0597065J',  # Université de Lille
            institution=HigherEducationInstitution.objects.get(uai_code__iexact='0597065J'),
            birth_date=datetime.today(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=BachelorType.objects.get(label__iexact='général'),
            validation=StudentRecord.TO_COMPLETE
        )
        self.visitor_record = VisitorRecord.objects.create(
            visitor=self.visitor,
            birth_date=datetime.today(),
            validation=1,
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

        self.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        self.token = Token.objects.create(user=self.ref_master_etab_user)
        self.client_token = Client(HTTP_AUTHORIZATION=f" Token {self.token.key}")

        self.api_token = Token.objects.create(user=self.api_user)
        self.api_client_token = Client(HTTP_AUTHORIZATION=f" Token {self.api_token.key}")

    def test_API_get_documents(self):
        url = "/api/get_available_documents/"

        # Fail : Anonymous request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # forbidden

        # Authenticated users
        for user in [self.ref_master_etab_user, self.ref_etab_user, self.operator_user]:
            request.user = user

            response = self.client.get(url, request, **self.header)
            self.assertEqual(response.status_code, 200)
            content = response.content.decode()

            json_content = json.loads(content)
            self.assertIn('msg', json_content)
            self.assertIn('data', json_content)
            self.assertIsInstance(json_content['data'], list)
            self.assertIsInstance(json_content['msg'], str)

            docs = AccompanyingDocument.objects.filter(active=True)
            self.assertEqual(len(json_content['data']), docs.count())

    def test_API_ajax_get_buildings(self):
        self.client.login(username='ref_etab', password='pass')
        url = f"/api/get_buildings/{self.campus.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], self.building.id)
        self.assertEqual(content['data'][0]['label'], self.building.label)

    def test_course_slot_creation(self):
        """
        Course slot creation
        """
        view_permission = Permission.objects.get(codename='view_slot')
        add_permission = Permission.objects.get(codename='add_slot')
        url = reverse("slot_list")

        # This date is inside a valid period
        date = (self.today + timedelta(days=10)).strftime("%Y-%m-%d")
        speaker = self.course.speakers.first()

        data = {
            "course": self.course.id,
            "n_places": "30",
            "n_group_places": "",
            "course_type": self.course_type.id,
            "building": self.building.pk,
            "campus": self.campus.pk,
            "date": date,
            "period": self.period.pk,
            "start_time": "10:00",
            "end_time": "12:00",
            "place": Slot.FACE_TO_FACE,
            "room": "salle 113",
            "levels_restrictions": True,
            "allowed_highschool_levels": [1],
            "registration_limit_delay": 24,
            "cancellation_limit_delay": 48,
            "speakers": [speaker.pk],
            "allow_individual_registrations": True,
            "allow_group_registrations": False,
            "group_mode": 0,
            "public_group": ""
        }

        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        slot = Slot.objects.get(period=self.period, date=date, course=self.course.pk)

        test_data = {
            "id":slot.pk,
            "room":"salle 113",
            "date":date,
            "period":self.period.pk,
            "start_time":"10:00:00",
            "end_time":"12:00:00",
            "n_places":30,
            "n_group_places": None,
            "additional_information":None,
            "url":None,
            "published":False,
            "place": Slot.FACE_TO_FACE,
            "establishments_restrictions":False,
            "levels_restrictions":True,
            "bachelors_restrictions":False,
            "course":self.course.pk,
            "course_type":self.course_type.pk,
            "event":None,
            "campus":self.campus.pk,
            "building":self.building.pk,
            "speakers":[speaker.id],
            "allow_individual_registrations": True,
            "allow_group_registrations": False,
            "group_mode": 0,
            "public_group": False,
            "allowed_establishments":[],
            "allowed_highschools":[],
            "allowed_highschool_levels":[1],
            "allowed_student_levels":[],
            "allowed_post_bachelor_levels":[],
            "allowed_bachelor_types":[],
            "allowed_bachelor_mentions":[],
            "allowed_bachelor_teachings":[],
            "registration_limit_delay":24,
            "cancellation_limit_delay":48,
            "registration_limit_date":f"{(self.today + timedelta(days=10) - timedelta(hours=24)).date()}T10:00:00+0{str(int(self.today_utc_offset.total_seconds()/3600))}:00",
            "cancellation_limit_date":f"{(self.today + timedelta(days=10) - timedelta(hours=48)).date()}T10:00:00+0{str(int(self.today_utc_offset.total_seconds()/3600))}:00",
            "reminder_notification_sent":False,
        }

        """
        import dictdiffer
        print([x for x in dictdiffer.diff(test_data, result)])
        """

        self.assertEqual(result, {
            "id":slot.pk,
            "room":"salle 113",
            "date":date,
            "period": self.period.pk,
            "start_time":"10:00:00",
            "end_time":"12:00:00",
            "n_places":30,
            "n_group_places": None,
            "additional_information":None,
            "url":None,
            "published":False,
            "place": Slot.FACE_TO_FACE,
            "establishments_restrictions":False,
            "levels_restrictions":True,
            "bachelors_restrictions":False,
            "course":self.course.pk,
            "course_type":self.course_type.pk,
            "event":None,
            "campus":self.campus.pk,
            "building":self.building.pk,
            "speakers":[speaker.id],
            "allow_individual_registrations": True,
            "allow_group_registrations": False,
            "group_mode": 0,
            "public_group": False,
            "allowed_establishments":[],
            "allowed_highschools":[],
            "allowed_highschool_levels":[1],
            "allowed_student_levels":[],
            "allowed_post_bachelor_levels":[],
            "allowed_bachelor_types":[],
            "allowed_bachelor_mentions":[],
            "allowed_bachelor_teachings":[],
            "registration_limit_delay":24,
            "cancellation_limit_delay":48,
            "registration_limit_date":f"{(self.today + timedelta(days=10) - timedelta(hours=24)).date()}T10:00:00+0{str(int(self.today_utc_offset.total_seconds()/3600))}:00",
            "cancellation_limit_date":f"{(self.today + timedelta(days=10) - timedelta(hours=48)).date()}T10:00:00+0{str(int(self.today_utc_offset.total_seconds()/3600))}:00",
            "reminder_notification_sent":False,
        })

        # Published course - test missing fields
        data2 = {
            "course": self.course.id,
            "published": True,
            "place": Slot.FACE_TO_FACE,
            "room": "salle 113",
            "levels_restrictions": True,
            "allowed_highschool_levels": [1]
        }

        response = self.api_client_token.post(url, data2)
        result = json.loads(response.content.decode('utf-8'))

        for field in ["n_places", "date", "period", "start_time", "end_time", "speakers"]:
            self.assertEqual(
                [f"Field '{field}' is required for a new published slot"],
                result['error'][field]
            )

        self.assertEqual(
            ["The building field is required when creating a new slot for a structure course"],
            result['error']['building']
        )
        self.assertEqual(
            ["The campus field is required when creating a new slot for a structure course"],
            result['error']['campus']
        )
        self.assertEqual(
            ["The course_type field is required when creating a new course slot"],
            result['error']['course_type']
        )

        # Bad start/end time
        data2.update({
            "campus": self.campus.pk,
            "building": self.building.pk,
            "course_type": self.course_type.pk,
            "date": (self.today + timedelta(days=11)).strftime("%Y-%m-%d"),
            "period":self.period.pk,
            "n_places": "30",
            "start_time": "14:00",
            "end_time": "12:00",
            "speakers": [speaker.pk]
        })

        response = self.api_client_token.post(url, data2)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(["end_time can't be set before or equal to start_time"], result['error']['end_time'])

        # Bad speaker choice (not linked to self.course)
        data2["start_time"] = "10:00"
        data2["speakers"] = [self.operator_user.pk]
        response = self.api_client_token.post(url, data2)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            [f"Speaker '{self.operator_user}' is not linked to course '{self.course}'"],
            result['error']['speakers']
        )

        # Test bad date/period
        new_date = self.today + timedelta(days=30)
        data["date"] = new_date.strftime("%Y-%m-%d")
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            ["Invalid date for selected period : please check periods settings"],
            result['error']['date']
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Slot.objects.filter(date=new_date, course=self.course.pk).exists())

    def test_slot_detail(self):
        """
        Test get slot
        :return:
        """
        url = reverse("slot_detail", args=[self.slot.id, ])
        add_permission = Permission.objects.get(codename='view_slot')
        delete_permission = Permission.objects.get(codename='delete_slot')

        # No permission
        self.api_user.user_permissions.remove(add_permission)
        self.api_user.user_permissions.remove(delete_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        response = self.api_client_token.delete(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Get
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.get(url)
        slot = json.loads(response.content.decode('utf-8'))
        self.assertEqual(slot["additional_information"], "Hello there!")

        # Delete
        self.api_user.user_permissions.add(delete_permission)
        response = self.api_client_token.delete(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result["error"], "This slot has registered immersions: delete not allowed")


    def test_API_get_student_records(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/get_student_records/"

        # No action
        data = {}
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])
        self.assertEqual("Error: No action selected for request", content['msg'])

        # To validate - With high school id
        # Add some attestations to the record, to check invalid_dates
        HighSchoolStudentRecordDocument.objects.create(
            record=self.hs_record,
            attestation=self.attestation_1,
            validity_date=None,
            for_minors=self.attestation_1.for_minors,
            mandatory=self.attestation_1.mandatory,
            requires_validity_date=self.attestation_1.requires_validity_date,
        )

        HighSchoolStudentRecordDocument.objects.create(
            record=self.hs_record,
            attestation=self.attestation_2,
            validity_date=None,
            for_minors=self.attestation_2.for_minors,
            mandatory=self.attestation_2.mandatory,
            requires_validity_date=self.attestation_2.requires_validity_date,
        )

        self.hs_record.validation = 1  # to validate
        self.hs_record.save()
        data = {
            'action': 'TO_VALIDATE',
            'high_school_id': self.high_school.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)

        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)
        self.assertEqual(hs_record['user_first_name'], self.hs_record.student.first_name)
        self.assertEqual(hs_record['user_last_name'], self.hs_record.student.last_name)
        self.assertEqual(hs_record['record_level'], self.hs_record.level.label)
        self.assertEqual(hs_record['class_name'], self.hs_record.class_name)
        self.assertEqual(hs_record['invalid_dates'], 2)

        # Validated
        self.hs_record.validation = 2  # valid
        self.hs_record.save()
        data = {
            'action': 'VALIDATED',
            'high_school_id': self.high_school.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)

        # Rejected
        self.hs_record.validation = 3  # rejected
        self.hs_record.save()
        data = {
            'action': 'REJECTED',
            'high_school_id': self.high_school.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)

    def test_API_ajax_get_reject_student(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/reject_student/"

        # no high school student id
        data = {}
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertIsNone(content['data'])
        self.assertEqual(content['msg'], "Error: No student selected")

        # Fail with record id error
        data = {
            'student_record_id': 0
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertIsNone(content['data'])
        self.assertEqual(content['msg'], "Error: No student record")

        # Success
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()
        data = {
            'student_record_id': self.hs_record.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 3)  # rejected

        # As a high school manager
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()

        client = Client()
        client.login(username='ref_lyc', password='pass')
        response = client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 3)  # rejected

    def test_API_ajax_get_validate_student__ok(self):
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()
        self.client.login(username=self.ref_etab_user.username, password='pass')
        url = "/api/validate_student/"

        data = {
            'student_record_id': self.hs_record.id
        }

        # Fail : missing attestation date
        document = HighSchoolStudentRecordDocument.objects.create(
            record=self.hs_record,
            attestation=self.attestation_1,
            validity_date=None,
            for_minors=self.attestation_1.for_minors,
            mandatory=self.attestation_1.mandatory,
            requires_validity_date=self.attestation_1.requires_validity_date,
        )

        # This one should be deleted after validation
        document2 = HighSchoolStudentRecordDocument.objects.create(
            record=self.hs_record,
            attestation=self.attestation_2,
            validity_date=None,
            for_minors=self.attestation_2.for_minors,
            mandatory=self.attestation_2.mandatory,
            requires_validity_date=False,
        )
        self.assertEqual(self.hs_record.attestation.count(), 2)

        response = self.client.post(url, data, **self.header)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Error: record has missing or invalid attestation dates")
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 1)
        self.assertEqual(self.hs_record.attestation.count(), 2)

        # delete document and retry : Success
        # document.delete()
        document.validity_date = self.today + timedelta(days=10)
        document.save()

        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 2)  # validated
        self.assertEqual(self.hs_record.attestation.count(), 1)

    def test_API_get_csv_anonymous(self):
        # ref master etab
        self.client.login(username='ref_master_etab', password='pass')

        # No type specified
        url = '/api/get_csv_anonymous/'
        response = self.client.get(url, request)
        self.assertEqual(response.status_code, 404)

        # type=course
        url = '/api/get_csv_anonymous/?type=course'
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('establishment'),
            _('structure'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
            _('course_type'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('speakers'),
            _('registration number'),
            _('place number'),
            _('additional information'),
        ]

        n = 0
        for row in content:
            # header check
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)

            elif n == 1:
                self.assertEqual(self.establishment.label, row[0])
                self.assertEqual(self.structure.label, row[1])
                self.assertIn(self.t_domain.label, row[2].split('|'))
                self.assertIn(self.t_sub_domain.label, row[3].split('|'))
                self.assertEqual(self.training.label, row[4])
                self.assertEqual(self.course.label, row[5])
                self.assertEqual(self.course_type.label, row[6])
                self.assertEqual(self.slot.period.label, row[7])
                self.assertEqual(_date(self.slot.date, 'd/m/Y'), row[8])
                self.assertIn(self.slot.start_time.strftime("%H:%M"), row[9])
                self.assertIn(self.slot.end_time.strftime("%H:%M"), row[10])
                self.assertEqual(self.campus.label, row[11])
                self.assertEqual(self.building.label, row[12])
                self.assertEqual(self.slot.room, row[13])
                self.assertEqual(str(self.speaker1), row[14])
                self.assertEqual(str(self.slot.registered_students()), row[15])
                self.assertEqual(str(self.slot.n_places), row[16])
                self.assertEqual(self.slot.additional_information, row[17])
            elif n == 1:  # high school slot
                self.assertEqual(f"{self.high_school.label} - {self.high_school.city}", row[0])
                self.assertEqual(self.highschool_training.label, row[4])
                self.assertEqual(self.highschool_course.label, row[5])
                self.assertEqual(self.highschool_slot.period.label, row[7])
                self.assertIn(self.highschool_slot.start_time.strftime("%H:%M"), row[9])
                self.assertIn(self.highschool_slot.end_time.strftime("%H:%M"), row[10])
                self.assertEqual("", row[11])
                self.assertEqual("", row[12])
                self.assertEqual(self.highschool_slot.room, row[13])
                self.assertEqual(str(self.highschool_slot.registered_students()), row[15])
                self.assertEqual(self.highschool_slot.additional_information, row[17])

            n += 1

        # ref etab
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('structure'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
            _('course_type'),
            _('period'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('speakers'),
            _('registration number'),
            _('place number'),
            _('additional information'),
        ]

        n = 0

        for row in content:
            # header check
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(self.structure.label, row[0])
                self.assertIn(self.t_domain.label, row[1].split('|'))
                self.assertIn(self.t_sub_domain.label, row[2].split('|'))
                self.assertEqual(self.training.label, row[3])
                self.assertEqual(self.course.label, row[4])
                self.assertEqual(self.course_type.label, row[5])
                self.assertEqual(self.slot.period.label, row[6])
                self.assertEqual(_date(self.slot.date, 'd/m/Y'), row[7])
                self.assertIn(self.slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.slot.end_time.strftime("%H:%M"), row[9])
                self.assertEqual(self.campus.label, row[10])
                self.assertEqual(self.building.label, row[11])
                self.assertEqual(self.slot.room, row[12])
                self.assertEqual(str(self.speaker1), row[13])
                self.assertEqual(str(self.slot.registered_students()), row[14])
                self.assertEqual(str(self.slot.n_places), row[15])
                self.assertEqual(self.slot.additional_information, row[16])
            elif n == 2:  # high school slot
                self.assertEqual(self.structure.label, row[0])
                self.assertEqual(self.training.label, row[3])
                self.assertEqual(self.highschool_course.label, row[4])
                self.assertEqual(self.slot2.period.label, row[6])
                self.assertIn(self.slot2.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.slot2.end_time.strftime("%H:%M"), row[9])
                self.assertEqual(self.slot2.room, row[12])
                self.assertEqual(str(self.highschool_slot.registered_students()), row[14])
                self.assertEqual(self.slot2.additional_information, row[16])

            n += 1

    def test_API_get_csv_highschool(self):
        # Ref highschool
        self.client.login(username='ref_lyc', password='pass')
        url = '/api/get_csv_highschool/'
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('last name'),
            _('first name'),
            _('birthdate'),
            _('level'),
            _('class name'),
            _('bachelor type'),
            _('establishment'),
            _('type'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course/event label'),
            _('period'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('attendance status'),
            _('additional information')
        ]

        n = 0
        for row in content:
            # header check
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            if n == 1:
                self.assertEqual(self.hs_record.student.last_name, row[0])
                self.assertEqual(self.hs_record.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record.level.label, row[3])
                self.assertEqual(self.hs_record.class_name, row[4])
                self.assertEqual(self.hs_record.bachelor_type.label, row[5])
                self.assertEqual('', row[6])
                self.assertEqual('', row[7])
                self.assertEqual('', row[8])
                self.assertEqual('', row[9])
                self.assertEqual('', row[10])
                self.assertEqual('', row[11])
                self.assertEqual('', row[12])
                self.assertEqual('', row[13])
                self.assertEqual('', row[14])
                self.assertEqual('', row[15])
                self.assertEqual('', row[16])
                self.assertEqual('', row[17])
                self.assertEqual('', row[18])
                self.assertEqual('', row[19])
                self.assertEqual('', row[20])
                self.assertEqual('No', row[21])
                self.assertEqual('Yes', row[22])

            elif n == 2:
                self.assertEqual(self.hs_record2.student.last_name, row[0])
                self.assertEqual(self.hs_record2.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record2.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record2.level.label, row[3])
                self.assertEqual(self.hs_record2.class_name, row[4])
                self.assertEqual(self.hs_record2.bachelor_type.label, row[5])
                self.assertEqual('', row[6])
                self.assertEqual('', row[7])
                self.assertEqual('', row[8])
                self.assertEqual('', row[9])
                self.assertEqual('', row[10])
                self.assertEqual('', row[11])
                self.assertEqual('', row[12])
                self.assertEqual('', row[13])
                self.assertEqual('', row[14])
                self.assertEqual('', row[15])
                self.assertEqual('', row[16])
                self.assertEqual('', row[17])
                self.assertEqual('', row[18])
                self.assertEqual('', row[19])
                self.assertEqual('', row[20])
                self.assertEqual('No', row[21])
                self.assertEqual('Yes', row[22])

            n += 1

        self.hs_record.allow_high_school_consultation = True
        self.hs_record.save()

        self.hs_record2.allow_high_school_consultation = True
        self.hs_record2.save()

        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        n = 0
        for row in content:
            # header check
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(self.hs_record.student.last_name, row[0])
                self.assertEqual(self.hs_record.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record.level.label, row[3])
                self.assertEqual(self.hs_record.class_name, row[4])
                self.assertEqual(self.hs_record.bachelor_type.label, row[5])
                self.assertEqual(self.establishment.label, row[6])
                self.assertEqual('Course', row[7])
                self.assertIn(self.t_domain.label, row[8].split('|'))
                self.assertIn(self.t_sub_domain.label, row[9].split('|'))
                self.assertIn(self.training.label, row[10])
                self.assertIn(self.course.label, row[11])
                self.assertEqual(self.past_slot.period.label, row[12])
                self.assertEqual(_date(self.past_slot.date, 'd/m/Y'), row[13])
                self.assertEqual(self.past_slot.start_time.strftime("%H:%M:%S"), row[14])
                self.assertEqual(self.past_slot.end_time.strftime("%H:%M:%S"), row[15])
                self.assertEqual(self.past_slot.campus.label, row[16])
                self.assertEqual(self.past_slot.building.label, row[17])
                self.assertEqual(self.past_slot.room, row[18])
                self.assertEqual(self.immersion3.get_attendance_status_display(), row[19])
                self.assertEqual(self.past_slot.additional_information, row[20])
                self.assertEqual('Yes', row[21])
                self.assertEqual('Yes', row[22])

            elif n == 2:
                self.assertEqual(self.hs_record.student.last_name, row[0])
                self.assertEqual(self.hs_record.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record.level.label, row[3])
                self.assertEqual(self.hs_record.class_name, row[4])
                self.assertEqual(self.hs_record.bachelor_type.label, row[5])
                self.assertEqual(self.establishment.label, row[6])
                self.assertIn('Course', row[7])
                self.assertIn(self.t_domain.label, row[8].split('|'))
                self.assertIn(self.t_sub_domain.label, row[9].split('|'))
                self.assertIn(self.training.label, row[10])
                self.assertEqual(self.course.label, row[11])
                self.assertEqual(self.slot.period.label, row[12])
                self.assertIn(_date(self.slot.date, 'd/m/Y'), row[13])
                self.assertIn(self.slot.start_time.strftime("%H:%M:%S"), row[14])
                self.assertIn(self.slot.end_time.strftime("%H:%M:%S"), row[15])
                self.assertEqual(self.slot.campus.label, row[16])
                self.assertEqual(self.slot.building.label, row[17])
                self.assertEqual(self.slot.room, row[18])
                self.assertEqual(self.immersion.get_attendance_status_display(), row[19])
                self.assertEqual(self.slot.additional_information, row[20])
                self.assertEqual('Yes', row[21])
                self.assertEqual('Yes', row[22])

            elif n == 3:
                self.assertEqual(self.hs_record2.student.last_name, row[0])
                self.assertEqual(self.hs_record2.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record2.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record2.level.label, row[3])
                self.assertEqual(self.hs_record2.class_name, row[4])
                self.assertEqual(self.hs_record2.bachelor_type.label, row[5])
                self.assertEqual('', row[6])
                self.assertEqual('', row[7])
                self.assertEqual('', row[8])
                self.assertEqual('', row[9])
                self.assertEqual('', row[10])
                self.assertEqual('', row[11])
                self.assertEqual('', row[12])
                self.assertEqual('', row[13])
                self.assertEqual('', row[14])
                self.assertEqual('', row[15])
                self.assertEqual('', row[16])
                self.assertEqual('', row[17])
                self.assertEqual('', row[18])
                self.assertEqual('', row[19])
                self.assertEqual('', row[20])
                self.assertEqual('Yes', row[21])
                self.assertEqual('Yes', row[22])

            n += 1

        self.hs_record.allow_high_school_consultation = False
        self.hs_record.save()

        self.hs_record2.allow_high_school_consultation = False
        self.hs_record2.save()

    def test_API_get_csv_structures(self):
        # No type specified
        url = '/api/get_csv_structures/'
        response = self.client.get(url, request)
        self.assertEqual(response.status_code, 404)

        url = '/api/get_csv_structures/?type=course'
        # Ref structure
        self.client.login(username='ref_str', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('structure'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
            _('course_type'),
            _('period'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('speakers'),
            _('registration number'),
            _('place number'),
            _('additional information'),
        ]

        n = 0

        for row in content:
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertIn(self.structure.label, row[0])
                self.assertIn(self.t_domain.label, row[1].split('|'))
                self.assertIn(self.t_sub_domain.label, row[2].split('|'))
                self.assertIn(self.training.label, row[3])
                self.assertIn(self.course.label, row[4])
                self.assertIn(self.course_type.label, row[5])
                self.assertIn(self.past_slot.period.label, row[6])
                self.assertIn(_date(self.past_slot.date, 'd/m/Y'), row[7])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[9])
                self.assertIn(self.past_slot.campus.label, row[10])
                self.assertIn(self.past_slot.building.label, row[11])
                self.assertEqual(self.past_slot.room, row[12])
                self.assertIn(
                    f'{self.speaker1.last_name} {self.speaker1.first_name}',
                    row[13].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[14])
                self.assertEqual(str(self.past_slot.n_places), row[15])
                self.assertEqual(self.past_slot.additional_information, row[16])

            n += 1

        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('structure'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
            _('course_type'),
            _('period'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('speakers'),
            _('registration number'),
            _('place number'),
            _('additional information'),
        ]

        n = 0

        for row in content:
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(self.structure.label, row[0])
                self.assertIn(self.t_domain.label, row[1].split('|'))
                self.assertIn(self.t_sub_domain.label, row[2].split('|'))
                self.assertIn(self.training.label, row[3])
                self.assertIn(self.course.label, row[4])
                self.assertIn(self.course_type.label, row[5])
                self.assertIn(self.past_slot.period.label, row[6])
                self.assertIn(_date(self.past_slot.date, 'd/m/Y'), row[7])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[9])
                self.assertIn(self.past_slot.campus.label, row[10])
                self.assertIn(self.past_slot.building.label, row[11])
                self.assertEqual(self.past_slot.room, row[12])
                self.assertIn(
                    f'{self.speaker1.last_name} {self.speaker1.first_name}',
                    row[13].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[14])
                self.assertEqual(str(self.past_slot.n_places), row[15])
                self.assertEqual(self.past_slot.additional_information, row[16])

            n += 1

        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode('utf-8-sig').split('\n'), **settings.CSV_OPTIONS)
        headers = [
            _('establishment'),
            _('structure'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
            _('course_type'),
            _('period'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('speakers'),
            _('registration number'),
            _('place number'),
            _('additional information'),
        ]

        n = 0

        for row in content:
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(self.establishment.label, row[0])
                self.assertEqual(self.structure.label, row[1])
                self.assertIn(self.t_domain.label, row[2].split('|'))
                self.assertIn(self.t_sub_domain.label, row[3].split('|'))
                self.assertIn(self.training.label, row[4])
                self.assertIn(self.course.label, row[5])
                self.assertIn(self.course_type.label, row[6])
                self.assertIn(self.past_slot.period.label, row[7])
                self.assertIn(_date(self.past_slot.date, 'd/m/Y'), row[8])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[9])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[10])
                self.assertIn(self.past_slot.campus.label, row[11])
                self.assertIn(self.past_slot.building.label, row[12])
                self.assertEqual(self.past_slot.room, row[13])
                self.assertIn(
                    f'{self.speaker1.last_name} {self.speaker1.first_name}',
                    row[14].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[15])
                self.assertEqual(str(self.past_slot.n_places), row[16])
                self.assertEqual(self.past_slot.additional_information, row[17])

            n += 1

    def test_API_ajax_get_available_vars(self):
        self.client.login(username='ref_etab', password='pass')
        request.user = self.ref_etab_user

        url = f"/api/get_available_vars/{self.mail_t.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 1)
        var = content['data'][0]
        self.assertEqual(var['id'], self.var.id)
        self.assertEqual(var['code'], self.var.code)
        self.assertEqual(var['description'], self.var.description)

        # Empty
        url = "/api/get_available_vars/0"
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content["msg"], "Error : no template id")
        self.assertEqual(content['data'], [])

    def test_API_get_person(self):
        self.client.login(username='ref_etab', password='pass')

        url = f"/api/get_person"
        data = {
            'establishment_id': self.establishment.id
        }

        # No username search string
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Search string is empty")
        self.assertEqual(content['data'], [])

        # Establishment has no source plugin configured : look for 'local' speakers
        data = {
            'username': "whatever",
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Please select an establishment or a high school first")
        self.assertEqual(content['data'], [])

        # Structure does not exist & no establishment
        data = {
            'username': "whatever",
            'structure_id': self.structure.id
        }

        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Please select an establishment or a high school first")

        # Establishment does not exist
        data = {
            'establishment_id': 99999,
            'username': 'whatever'
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Sorry, establishment not found")

        # Establishment does not exist
        data = {
            'establishment_id': 99999,
            'username': 'whatever'
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Sorry, establishment not found")

        # High school does not exist
        data = {
            'highschool_id': 99999,
            'username': 'whatever'
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Sorry, high school not found")

        # No establishment or highschool in search query
        data = {
            'username': 'bofh',
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Please select an establishment or a high school first")
        self.assertEqual(content['data'], [])

        # local plugin : test incomplete settings
        self.establishment3.data_source_settings = None
        self.establishment3.save()

        data = {
            'username': 'ref_etab3',
            'establishment_id': self.establishment3.id
        }
        self.client.login(username='ref_etab3', password='pass')
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(
            content['msg'],
            "Error : Please check establishment LDAP plugin settings : LDAP plugin settings are empty"
        )
        self.assertEqual(content['data'], [])

    def test_API_ajax_get_speaker_courses(self):
        # As a 'structure' speaker
        request.user = self.speaker1
        client = Client()
        client.login(username='speaker1', password='pass')

        url = reverse("course_list")

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content), 0)
        c = content[0]
        self.assertEqual(self.course.id, c['id'])
        self.assertEqual(self.course.published, c['published'])
        self.assertEqual(
            f"{self.course.structure.establishment.code} - {self.course.structure.code}",
            c['managed_by']
        )
        self.assertEqual(self.course.training.label, c['training']['label'])
        self.assertEqual(self.course.label, c['label'])
        # speakers
        self.assertEqual(self.course.slots_count(speakers=self.speaker1.id), c['slots_count'])
        self.assertEqual(self.course.free_seats(speakers=self.speaker1.id), c['n_places'])
        self.assertEqual(
            self.course.published_slots_count(speakers=self.speaker1.id),
            c['published_slots_count']
        )
        self.assertEqual(self.course.get_alerts_count(), c['alerts_count'])

        # as a high school speaker
        client.login(username='highschool_speaker', password='pass')
        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content), 0)
        c = content[0]
        self.assertEqual(self.highschool_course.id, c['id'])
        self.assertEqual(self.highschool_course.published, c['published'])
        self.assertEqual(f"{self.high_school.city} - {self.high_school.label}", c['managed_by'])
        self.assertEqual(self.highschool_course.training.label, c['training']['label'])
        self.assertEqual(self.highschool_course.label, c['label'])
        # speakers
        self.assertEqual(self.highschool_course.slots_count(speakers=self.highschool_speaker.id), c['slots_count'])
        self.assertEqual(self.highschool_course.free_seats(speakers=self.highschool_speaker.id), c['n_places'])
        self.assertEqual(
            self.highschool_course.published_slots_count(speakers=self.highschool_speaker.id),
            c['published_slots_count']
        )

    def test_API_get_agreed_highschools(self):
        """
        Get only high schools with valid agreements
        """

        # Create another high school without agreement just to be sure it doesn't show up in the results
        HighSchool.objects.create(
            label='no-agreement',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0987654321',
            email='b@domain.tld',
            mailing_list='ml@domain.tld',
            head_teacher_name='M. A B',
            postbac_immersion=True,
            signed_charter=True,
        )

        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        url = "/api/highschools?agreed=true"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content), 1)
        hs = content[0]
        self.assertEqual(self.high_school.id, hs['id'])
        self.assertEqual(self.high_school.label, hs['label'])
        self.assertEqual(self.high_school.address, hs['address'])
        self.assertEqual(self.high_school.address2, hs['address2'])
        self.assertEqual(self.high_school.address3, hs['address3'])
        self.assertEqual(str(self.high_school.department), hs['department'])
        self.assertEqual(self.high_school.city, hs['city'])
        self.assertEqual(str(self.high_school.zip_code), hs['zip_code'])
        self.assertEqual(self.high_school.phone_number, hs['phone_number'])
        self.assertEqual(self.high_school.fax, hs['fax'])
        self.assertEqual(self.high_school.email, hs['email'])
        self.assertEqual(self.high_school.head_teacher_name, hs['head_teacher_name'])
        self.assertEqual(_date(self.high_school.convention_start_date, 'Y-m-d'), hs['convention_start_date'])
        self.assertEqual(_date(self.high_school.convention_end_date, 'Y-m-d'), hs['convention_end_date'])

    def test_API_ajax_get_immersions(self):
        # Wrong user
        request.user = self.student
        self.client.login(username='student', password='pass')

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            **self.header
        )

        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error : invalid user id")
        self.assertEqual(content['data'], [])

        # User not found
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': 99999999}),
            **self.header
        )
        content = json.loads(response.content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Error : no such user")

        # No user
        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': 0}),
            **self.header
        )
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error : missing user id")
        self.assertEqual(content['data'], [])

        # Get future immersions
        self.slot.date = self.today + timedelta(days=2)
        self.slot.save()

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            {'immersion_type': 'future'},
            **self.header
        )
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]

        """
        This doesn't work yet because of cancellation_limit_date comparison
        """
        self.maxDiff = None
        self.assertEqual(
            content['data'][0],
            {
                'id': self.immersion.id,
                'type': 'course',
                'translated_type': 'Course',
                'label': 'course 1',
                'establishment': 'Etablissement 1',
                'highschool': '',
                'highschool_address': '',
                'highschool_city': '',
                'highschool_zip_code': '',
                'structure': 'test structure',
                'meeting_place': 'room 1',
                'campus': 'Esplanade',
                'campus_city': 'Strasbourg',
                'building': 'Le portique',
                'room': 'room 1',
                'establishments': 'Etablissement 1',
                'course': {'label': 'course 1', 'training': 'test training', 'training_url': None, 'type': 'CM', 'type_full': ''},
                'event': {},
                'datetime': datetime.combine(self.immersion.slot.date, self.immersion.slot.start_time).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                'date': date_format(self.immersion.slot.date),
                'start_time': self.immersion.slot.start_time.strftime("%-Hh%M"),
                'end_time': self.immersion.slot.end_time.strftime("%-Hh%M"),
                'speakers': ['HER speak'],
                'info': 'Hello there!',
                'attendance': 'Not entered',
                'attendance_status': 0,
                'cancellable': True,
                'cancellation_limit_date': json.dumps(
                    self.immersion.slot.cancellation_limit_date.astimezone(datetime_timezone.utc), cls=DjangoJSONEncoder
                ).strip('"'),
                'cancellation_type': '',
                'slot_id': self.immersion.slot.id,
                'free_seats': 18,
                'can_register': False,
                'can_show_url': True,
                'place': Slot.FACE_TO_FACE,
                'url': None,
                'time_type': 'future',
                'registration_date': json.dumps(
                    self.immersion.registration_date.astimezone(datetime_timezone.utc), cls=DjangoJSONEncoder
                ).strip('"'),
                'cancellation_date': "",
                'allow_individual_registrations': self.immersion.slot.allow_individual_registrations,
                'n_places': self.immersion.slot.n_places,
                'n_registered': self.immersion.slot.registered_students(),
                'registration_limit_date': json.dumps(
                    self.immersion.slot.registration_limit_date.astimezone(datetime_timezone.utc), cls=DjangoJSONEncoder
                ).strip('"'),
            },
        )

        # {'id': 41, 'type': 'course', 'translated_type': 'Course', 'label': 'course 1', 'establishment': 'Etablissement 1', 'highschool': '', 'structure': 'test structure', 'meeting_place': 'Le portique <br> room 1', 'campus': 'Esplanade', 'building': 'Le portique', 'room': 'room 1', 'establishments': 'Etablissement 1', 'course': {'label': 'course 1', 'training': 'test training', 'training_url': None, 'type': 'CM', 'type_full': ''}, 'event': {}, 'datetime': datetime.datetime(2024, 7, 14, 12, 0), 'date': 'July 14, 2024', 'start_time': '12h00', 'end_time': '14h00', 'speakers': ['HER speak'], 'info': 'Hello there!', 'attendance': 'Not entered', 'attendance_status': 0, 'cancellable': True, 'cancellation_limit_date': datetime.datetime(2024, 7, 14, 10, 0, tzinfo=datetime.timezone.utc), 'cancellation_type': '', 'slot_id': 131, 'free_seats': 18, 'can_register': False, 'place': 0, 'registration_date': datetime.datetime(2024, 7, 12, 15, 34, 56, 129949, tzinfo=datetime.timezone.utc), 'cancellation_date': '', 'campus_city': 'STRASBOURG', 'allow_individual_registrations': True, 'n_places': 20, 'n_registered': 2, 'registration_limit_date': datetime.datetime(2024, 7, 14, 10, 0, tzinfo=datetime.timezone.utc), 'time_type': 'future'}

        # Get past immersions
        self.slot.date = self.today - timedelta(days=2)
        self.slot.save()

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            {'immersion_type': 'past'},
            **self.header
        )
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['course']['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course']['label'])
        self.assertEqual(self.immersion.slot.course_type.label, i['course']['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['course']['type_full'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.campus.city.title(), i['campus_city'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['room'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%-Hh%M"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%-Hh%M"), i['end_time'])
        self.assertEqual(self.immersion.slot.additional_information, i['info'])
        self.assertEqual(self.immersion.get_attendance_status_display(), i['attendance'])
        self.assertEqual(self.immersion.attendance_status, i['attendance_status'])
        self.assertEqual(self.today.date() < self.immersion.slot.date.date(), i['cancellable'])
        self.assertEqual(self.immersion.slot.id, i['slot_id'])

        # Get cancelled immersions
        self.immersion.cancellation_type = self.cancel_type
        self.immersion.save()

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            {'immersion_type': 'cancelled'},
            **self.header
        )

        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['course']['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course']['label'])
        self.assertEqual(self.immersion.slot.course_type.label, i['course']['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['course']['type_full'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.campus.city.title(), i['campus_city'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['room'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%-Hh%M"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%-Hh%M"), i['end_time'])
        self.assertEqual(self.immersion.slot.additional_information, i['info'])
        self.assertEqual(self.immersion.get_attendance_status_display(), i['attendance'])
        self.assertEqual(self.immersion.attendance_status, i['attendance_status'])
        self.assertEqual(self.today.date() < self.immersion.slot.date.date(), i['cancellable'])
        self.assertEqual(self.immersion.slot.id, i['slot_id'])

        ## Test High school manager user & hs student's allow hight school consultation  setting
        request.user = self.ref_lyc
        self.client.login(username='ref_lyc', password='pass')
        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            {'immersion_type': 'cancelled'},
            **self.header
        )
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Error : user don't share his immersions with his highschool")

        hs = self.highschool_user.get_high_school_student_record()
        hs.allow_high_school_consultation = True
        hs.save()

        response = self.client.get(
            reverse('get_immersions', kwargs={'user_id': self.highschool_user.id}),
            {'immersion_type': 'cancelled'},
            **self.header
        )
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "")
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['course']['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course']['label'])
        self.assertEqual(self.immersion.slot.course_type.label, i['course']['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['course']['type_full'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.campus.city.title(), i['campus_city'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['room'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%-Hh%M"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%-Hh%M"), i['end_time'])
        self.assertEqual(self.immersion.slot.additional_information, i['info'])
        self.assertEqual(self.immersion.get_attendance_status_display(), i['attendance'])
        self.assertEqual(self.immersion.attendance_status, i['attendance_status'])
        self.assertEqual(self.today.date() < self.immersion.slot.date.date(), i['cancellable'])
        self.assertEqual(self.immersion.slot.id, i['slot_id'])

        hs.allow_high_school_consultation = False
        hs.save()

    def test_API_get_other_registrants(self):
        client = Client()
        client.login(username='student', password='pass')
        request.user = self.student

        url = f"/api/get_other_registrants/{self.immersion2.id}"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(
            i['name'],
            f'{self.highschool_user.last_name} {self.highschool_user.first_name}'
        )
        self.assertEqual(i['email'], self.highschool_user.email)

        # Unknown immersion
        url = f"/api/get_other_registrants/9999999"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], 'Error : invalid user or immersion id')

    def test_API_ajax_get_slot_registrations(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        url = f"/api/get_slot_registrations/{self.slot.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 2)
        hs = content['data'][0]
        self.assertEqual(hs['id'], self.immersion.id)
        self.assertEqual(hs['lastname'], self.highschool_user.last_name)
        self.assertEqual(hs['firstname'], self.highschool_user.first_name)
        self.assertEqual(hs['profile'], 'High school student')
        self.assertEqual(hs['school'], self.hs_record.highschool.label)
        self.assertEqual(hs['level'], self.hs_record.level.label)
        self.assertEqual(hs['city'], self.hs_record.highschool.city)
        self.assertEqual(hs['attendance'], self.immersion.get_attendance_status_display())
        self.assertEqual(hs['attendance_status'], self.immersion.attendance_status)

        stu = content['data'][1]
        self.assertEqual(stu['profile'], 'Student')
        self.assertEqual(stu['level'], self.student_record.level.label)
        self.assertEqual(
            stu['school'],
            HigherEducationInstitution.objects.get(pk=self.student_record.uai_code).label
        )
        self.assertEqual(stu['city'], '')

        url = f"/api/get_slot_registrations/999999"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], 'Error : invalid slot id')

    def test_API_ajax_get_available_students(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        self.hs_record.validation = 2
        self.hs_record.save()
        self.hs_record2.validation = 2
        self.hs_record2.save()

        url = f"/api/get_available_students/{self.slot.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 2)

        # Careful with the results order (last_name, first_name)
        hs = content['data'][0]
        stu = content['data'][1]

        # High school student
        self.assertEqual(hs, {
            'id': self.highschool_user2.id,
            'last_name': self.highschool_user2.last_name,
            'first_name': self.highschool_user2.first_name,
            'record_highschool_label': self.hs_record2.highschool.label,
            'record_highschool_id': self.hs_record2.highschool.id,
            'institution_label': None,
            'institution_uai_code': None,
            'city': self.hs_record2.highschool.city,
            'class_name': self.hs_record2.class_name,
            'profile': pgettext('person type', 'High school student'),
            'profile_name': 'highschool',
            'level_id': self.hs_record2.level.id,
            'level': self.hs_record2.level.label,
            'post_bachelor_level_id': None,
            'post_bachelor_level': None,
            'bachelor_type_id': self.hs_record2.bachelor_type.id,
            'bachelor_type': self.hs_record2.bachelor_type.label,
            'bachelor_type_is_professional': self.hs_record2.bachelor_type.professional,
            'technological_bachelor_mention_id': None,
            'technological_bachelor_mention': None,
            'general_bachelor_teachings_ids': [None],
        })

        # Student
        self.assertEqual(stu, {
            'id': self.student2.id,
            'last_name': self.student2.last_name,
            'first_name': self.student2.first_name,
            'record_highschool_label': None,
            'record_highschool_id': None,
            'institution_label': HigherEducationInstitution.objects.get(pk=self.student_record2.uai_code).label,
            'institution_uai_code': HigherEducationInstitution.objects.get(pk=self.student_record2.uai_code).uai_code,
            'city': None,
            'class_name': None,
            'profile': pgettext('person type', 'Student'),
            'profile_name': 'student',
            'level_id': self.student_record2.level.id,
            'level': self.student_record2.level.label,
            'post_bachelor_level_id': None,
            'post_bachelor_level': None,
            'bachelor_type_id': None,
            'bachelor_type': None,
            'bachelor_type_is_professional': None,
            'technological_bachelor_mention_id': None,
            'technological_bachelor_mention': None,
            'general_bachelor_teachings_ids': [None],
        })

        # Unknown slot
        url = f"/api/get_available_students/99999"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], 'Error : slot not found')

    def test_API_ajax_get_highschool_students(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        # Add a validation_string to highschool_user3
        self.highschool_user3.validation_string = "123"
        self.highschool_user3.save()

        # No records
        url = "/api/get_highschool_students/no_account_activation"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 1)
        h = content['data'][0]
        self.assertEqual(self.highschool_user3.id, h['id'])
        self.assertEqual(self.highschool_user3.last_name, h['last_name'])
        self.assertEqual(self.highschool_user3.first_name, h['first_name'])
        empty_fields = ('birth_date', 'level', 'institution', 'bachelor', 'post_bachelor_level', 'class_name')

        for field in empty_fields:
            self.assertEqual(None, h[field])

        # As a high school manager
        url = "/api/get_highschool_students"
        request.user = self.ref_lyc
        client = Client()
        client.login(username='ref_lyc', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 5)

        # Students
        level = HighSchoolLevel.objects.filter(is_post_bachelor=True).first()
        post_bachelor_level = PostBachelorLevel.objects.first()
        self.hs_record.level = level
        self.hs_record.origin_bachelor_type = BachelorType.objects.get(label__iexact='général')
        self.hs_record.post_bachelor_level = post_bachelor_level
        self.hs_record.save()

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 5)

        one = False
        for h in content['data']:
            if h['level'] in [l.label for l in HighSchoolLevel.objects.filter(is_post_bachelor=True)]:
                self.assertEqual(
                    f"{self.hs_record.post_bachelor_level.label}",
                    h['post_bachelor_level']
                )
                self.assertEqual(self.hs_record.origin_bachelor_type.label, h['hs_origin_bachelor'])
                one = True
                break
        self.assertTrue(one)

        # Fail : as a high school manager with no high school
        """
        FIXME : this test will fail because the user will be redirected to the charter sign form

        self.ref_lyc.highschool = None
        self.ref_lyc.save()

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Invalid parameters")
        self.assertEqual(content['data'], [])
        """

    def test_API_validate_slot_date(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        # No date
        url = f"/api/validate_slot_date"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error: A date is required")
        self.assertEqual(content['data'], {})

        # Bad date format
        url = f"/api/validate_slot_date?date=failure"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error: bad date format")
        self.assertEqual(content['data'], {})

        # dmY format
        url = f"/api/validate_slot_date?date=01/01/2010"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIn('is_between', content['data'])
        self.assertIsInstance(content['data']['is_between'], bool)
        self.assertEqual(content['data']['is_between'], False)

        # Ymd format
        d = self.today
        if d.weekday() == 6:
            d = self.today + timedelta(days=1)
        dd = _date(d, 'Y/m/d')
        url = f"/api/validate_slot_date?date={dd}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIn('is_between', content['data'])
        self.assertIsInstance(content['data']['is_between'], bool)
        self.assertEqual(content['data']['is_between'], True)

        # TODO: add 'valid_period' test

    def test_API_ajax_delete_account(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/delete_account"

        # Fail : missing parameter
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual("Missing parameter", content['msg'])

        # Fail : can't delete a structure referent
        data = {'account_id': self.ref_str.id}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual("You can't delete this account (invalid group)", content['msg'])

        # Delete a student : success
        uid = self.highschool_user.id
        data = {
            'account_id': self.highschool_user.id,
            'send_email': 'true'
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertFalse(content['error'])
        self.assertEqual("Account deleted", content['msg'])

        with self.assertRaises(ImmersionUser.DoesNotExist):
            ImmersionUser.objects.get(pk=uid)

    def test_API_ajax_cancel_registration(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/cancel_registration"

        # No data
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid parameters")

        # Bad user id
        data = {
            'immersion_id': 0,
            'reason_id': 1
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "User not found")

        # Bad reason id
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_id': self.immersion.id,
            'reason_id': 0
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid cancellation reason #id")

        # Past immersion
        self.slot.date = self.today - timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_id': self.immersion.id,
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Past immersion cannot be cancelled")

        # Cancellation deadline has passed
        passed_test_immersion = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.passed_registration_date_slot,
        )

        data = {
            'immersion_id': passed_test_immersion.id,
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Slot cancellation deadline has passed")

        # Authenticated user has no rights
        data = {
            'immersion_id': self.immersion.id,
            'reason_id': self.cancel_type.id
        }

        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()

        self.client.login(username='ref_str2', password='pass')
        self.assertIsNone(self.immersion.cancellation_type)
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "You don't have enough privileges to cancel this registration")

        # Success
        self.client.login(username='ref_etab', password='pass')
        self.assertIsNone(self.immersion.cancellation_type)

        self.immersion.slot.date = self.today + timedelta(days=1)
        self.immersion.slot.registration_limit_delay = 48 # to check emails
        self.immersion.slot.save()

        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Immersion cancelled")

        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.cancellation_type.id, self.cancel_type.id)

        # 3 mails sent : student, structure manager (with notification) and speaker
        self.assertEqual(len(mail.outbox), 3)

        # TODO test as student

    def test_API_ajax_set_attendance(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/set_attendance"

        # No immersion id
        data = {
            'attendance_value': 1
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], "Error: missing immersion id parameter")

        # No attendance status
        data = {
            'immersion_id': self.immersion.id
        }

        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], "Error: no attendance status set in parameter")

        # Bad users
        data = {
            'immersion_id': self.immersion.id,
            'attendance_value': 1
        }
        self.client.login(username='ref_str2', password='pass')
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(
            f"{self.immersion.student} : you don't have enough privileges to set the attendance status",
            content['error']
        )
        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 0)

        self.client.login(username='ref_lyc', password='pass')
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(
            f"{self.immersion.student} : you don't have enough privileges to set the attendance status",
            content['error']
        )
        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 0)

        # Success
        # As a slot speaker
        self.client.login(username='speaker1', password='pass')
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(content['error'], '')
        self.assertEqual(content['success'], f"{self.immersion.student} : attendance status updated")
        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 1)

        # As the establishment manager
        # reset the immersion status
        self.immersion.attendance_status = 0
        self.immersion.save()
        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 0)

        self.client.login(username='ref_etab', password='pass')
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['error'], '')
        self.assertEqual(content['success'], f"{self.immersion.student} : attendance status updated")

        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 1)

        # Multiple immersions
        self.immersion.attendance_status = 0
        self.immersion.save()
        self.assertEqual(self.immersion.attendance_status, 0)
        self.assertEqual(self.immersion2.attendance_status, 0)

        data_immersion = json.dumps([self.immersion.id, self.immersion2.id])
        data = {
            'immersion_ids': data_immersion,
            'attendance_value': 1
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['error'], '')
        self.assertEqual(
            content['success'],
            f"""{self.immersion.student} : attendance status updated"""
            f"""<br>{self.immersion2.student} : attendance status updated"""
        )

        self.immersion.refresh_from_db()
        self.immersion2.refresh_from_db()
        self.assertEqual(self.immersion.attendance_status, 1)
        self.assertEqual(self.immersion2.attendance_status, 1)

        # Bad immersion ids
        data = {
            'immersion_ids': 0,
            'attendance_value': 1
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], "Error: missing immersion id parameter")

    def test_API_ajax_get_alerts(self):
        request.user = self.student
        client = Client()
        client.login(username='student', password='pass')

        url = "/api/course_alerts"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content), 1)
        alert = content[0]
        self.assertEqual(self.alert.id, alert['id'])
        self.assertEqual(self.alert.course.label, alert['course']['label'])
        self.assertEqual(self.alert.course.training.label, alert['course']['training']['label'])
        self.assertEqual(self.alert.email_sent, alert['email_sent'])

        # TODO : test with a visitor and a high school student

    def test_API_ajax_send_email(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/send_email"

        # No data
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "mode param ('group' or 'student') is required")

        # Success
        data = {
            'slot_id': self.slot.id,
            'send_copy': 'true',
            'subject': 'hello',
            'body': 'Hello world',
            'mode': 'student',
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertFalse(content['error'])
        self.assertEqual(len(content['msg']), 0)

    def test_API_ajax_batch_cancel_registration(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/batch_cancel_registration"

        # No data
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid parameters")

        # Invalid slot id
        data = {
            'immersion_ids': 'hello world',
            'reason_id': self.cancel_type.id,
            'slot_id': "hi"
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid slot id")

        data.update({
            "slot_id": self.immersion.slot_id
        })

        # Invalid json parameters
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid json decoding")

        # Past immersions
        self.slot.date = self.today - timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_ids': f'[{self.immersion.id}]',
            'reason_id': self.cancel_type.id,
            'slot_id': self.immersion.slot_id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Past immersion cannot be cancelled")

        # Authenticated user has no rights
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()

        self.client.login(username='ref_str2', password='pass')
        self.assertIsNone(self.immersion.cancellation_type)
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "You don't have enough privileges to cancel these registrations")

        # Success
        self.client.login(username='ref_etab', password='pass')
        self.assertIsNone(self.immersion.cancellation_type)

        self.immersion.slot.date = self.today + timedelta(days=1)
        self.immersion.slot.registration_limit_delay = 48
        self.immersion.slot.save()

        data = {
            'immersion_ids': json.dumps([self.immersion.id]),
            'reason_id': self.cancel_type.id,
            'slot_id': self.immersion.slot_id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        # The following test may fail if template syntax has errors
        self.assertIn("1 immersion(s) cancelled", content['msg'])
        self.assertFalse(content['error'])

        # 3 mails sent : student, structure manager (with notification) and speaker
        self.assertEqual(len(mail.outbox), 3)

    def test_API_ajax_send_email_us(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/send_email_contact_us"

        # No data
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid parameters")

        # Success
        data = {
            'subject': 'Unittest',
            'body': 'Hello world',
            'lastname': 'Hello',
            'firstname': 'World',
            'email': 'unittest@unittest.fr',
            'notify_user': True,
        }

        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "")

        # Invalid settings
        GeneralSettings.objects.get(setting='MAIL_CONTACT_REF_ETAB').delete()
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Config parameter not found")

    def test_API_ajax_get_students_presence(self):

        # ref_etab
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/get_students_presence"

        data = {}
        content = json.loads(self.client.get(url, data, **self.header).content.decode())

        if self.immersion.student.is_visitor():
            student_profile = _('Visitor')
        elif self.immersion.student.is_high_school_student():
            student_profile = _('High school student')
        else:
            student_profile = _('Student')

        # get_students_presence returns an unordered list, careful when testing
        # a specific immersion
        i = list(filter(lambda x:x['id'] == self.immersion.id, content['data']))[0]

        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.date.strftime("%Y-%m-%d"), i['date'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%H:%M:%S"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%H:%M:%S"), i['end_time'])
        self.assertEqual(self.highschool_user.first_name, i['first_name'])
        self.assertEqual(self.highschool_user.last_name, i['last_name'])
        self.assertEqual(self.hs_record.highschool.label, i['institution'])
        self.assertEqual(self.hs_record.phone, i['phone'])
        self.assertEqual(self.highschool_user.email, i['email'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['meeting_place'])
        self.assertEqual(student_profile, i['student_profile'])

        data = {
            'from_date': (self.today.date() - timedelta(days=90)).strftime("%Y-%m-%d"),
            'until_date': self.today.date().strftime("%Y-%m-%d"),
            'place': Slot.FACE_TO_FACE
        }

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode('utf-8'))

        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.date.strftime("%Y-%m-%d"), i['date'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%H:%M:%S"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%H:%M:%S"), i['end_time'])
        self.assertEqual(self.highschool_user.first_name, i['first_name'])
        self.assertEqual(self.highschool_user.last_name, i['last_name'])
        self.assertEqual(self.hs_record.highschool.label, i['institution'])
        self.assertEqual(self.hs_record.phone, i['phone'])
        self.assertEqual(self.highschool_user.email, i['email'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['meeting_place'])
        self.assertEqual(student_profile, i['student_profile'])

        # ref_lyc: allowed only if high school has postbac immersions
        request.user = self.ref_lyc
        self.client.login(username='ref_lyc', password='pass')
        url = "/api/get_students_presence"

        Immersion.objects.create(
            slot=self.highschool_slot,
            student=self.highschool_user
        )

        # remove the postbac immersions : won't return anything
        self.high_school.postbac_immersion = False
        self.high_school.save()

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content, {"data": [], "msg": ""})

        # postbac immersions back, should see the only registered student
        self.high_school.postbac_immersion = True
        self.high_school.save()
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(content["data"]), 1)

        self.assertEqual(content["data"][0]["student_id"], self.highschool_user.pk)
        self.assertEqual(content["data"][0]["slot_id"], self.highschool_slot.pk)



    def test_API_ajax_set_course_alert(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/set_course_alert"

        # Bad course id
        data = {
            'course_id': 0
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Invalid parameter : course not found")
        self.assertTrue(content['error'])

        # Invalid email
        data = {
            'course_id': self.course.id,
            'email': 'wrong_email_address'
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Invalid email format")
        self.assertTrue(content['error'])

        # Success
        data = {
            'course_id': self.course.id,
            'email': 'a@unittest.fr'
        }

        self.assertFalse(UserCourseAlert.objects.filter(course_id=data['course_id'], email=data['email']).exists())

        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Alert successfully set")

        self.assertTrue(UserCourseAlert.objects.filter(course_id=data['course_id'], email=data['email']).exists())

        # Alert already set (and not sent yet) for this student
        data = {
            'course_id': self.course.id,
            'email': self.student.email
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "You have already set an alert on this course")

        # Alert already sent : reset the 'sent' status
        self.alert.email_sent = True
        self.alert.save()

        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Alert successfully set")

    def test_API_ajax_cancel_alert(self):
        request.user = self.student
        client = Client()
        client.login(username='student', password='pass')
        url = "/api/cancel_alert"

        # Bad alert id
        data = {
            'alert_id': 0
        }
        response = client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "")

        # Success
        self.assertTrue(UserCourseAlert.objects.filter(pk=self.alert.id).exists())

        data = {
            'alert_id': self.alert.id
        }
        response = client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['error'], '')
        self.assertEqual(content['msg'], "Alert successfully cancelled")

        self.assertFalse(UserCourseAlert.objects.filter(pk=self.alert.id).exists())

    def test_ajax_slot_registration(self):
        self.hs_record.validation = 2
        self.hs_record.save()

        # Delete a previously created immersion
        self.immersion3.delete()

        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {
                self.past_period.pk: 1,
                self.period.pk: 1,
                self.period2.pk: 3
            }
        )

        client = Client()
        client.login(username=self.highschool_user.username, password='pass')

        # Should work
        data = {
            'slot_id': self.slot3.id,
            'student_id': self.highschool_user.id
        }

        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))

        # FIXME Careful, the following test may fail if the message template has syntax errors (use "assertIn" ?)
        self.assertEqual("Registration successfully added, confirmation email sent", content['msg'])
        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {
                self.past_period.pk: 1,
                self.period.pk: 0,
                self.period2.pk: 3
            }
        )
        self.assertTrue(Immersion.objects.filter(student=self.highschool_user, slot=self.slot3).exists())

        # Fail : already registered
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Already registered to this slot", content['msg'])

        # Fail : no more registration allowed
        data['slot_id'] = self.slot2.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("""You have no more remaining registration available for this period, """
                         """you should cancel an immersion or contact immersion service""", content['msg'])

        # As a structure manager
        client.login(username=self.ref_str.username, password='pass')
        data['slot_id'] = self.slot2.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("This student is over quota for this period", content['msg'])

        # reset immersions
        client.login(username=self.highschool_user.username, password='pass')
        Immersion.objects.filter(student=self.highschool_user).delete()

        # Fail with high school record validation
        self.highschool_user.high_school_student_record.set_status('TO_COMPLETE')
        self.highschool_user.high_school_student_record.save()
        data = {
            'slot_id': self.slot3.id,
            'student_id': self.highschool_user.id
        }
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to Highschool student record state", content['msg'])

        # Revalidate the record
        self.highschool_user.high_school_student_record.set_status('VALIDATED')
        self.highschool_user.high_school_student_record.save()

        # Test with a not-yet-valid student record
        self.student_record.set_status('TO_COMPLETE')
        self.student_record.save()

        data = {
            'slot_id': self.slot3.id,
            'student_id': self.student.id
        }
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to student record state", content['msg'])

        # Test with a not-yet-valid visitor record
        self.visitor_record.set_status('TO_COMPLETE')
        self.visitor_record.save()

        data = {
            'slot_id': self.slot3.id,
            'student_id': self.visitor.id
        }
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to visitor record state", content['msg'])

        # Fail with past slot registration
        data['student_id'] = self.highschool_user.id
        data['slot_id'] = self.past_slot.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Register to past slot is not possible", content['msg'])

        # Fail with full slot registration
        data['slot_id'] = self.full_slot.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("No seat available for selected slot", content['msg'])

        # Fail with unpublished slot
        data['slot_id'] = self.unpublished_slot.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Registering an unpublished slot is forbidden", content['msg'])

        # Fail with highschool level Restrictions
        response = client.post(
            "/api/register",
            {'slot_id': self.highschool_level_restricted_slot.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to slot's restrictions", content['msg'])

        # Fail with passed slot registration limit date
        data['slot_id'] = self.passed_registration_date_slot.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to passed registration date", content['msg'])

        # Fail with bachelor restrictions
        response = client.post(
            "/api/register",
            {'slot_id': self.bachelor_restricted_slot.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to slot's restrictions", content['msg'])

        # Fail with bachelor mentions restrictions
        # 1/ Update high school record
        self.hs_record.bachelor_type = BachelorType.objects.get(label__iexact='technologique')
        self.hs_record.technological_bachelor_mention = self.bachelor_mention
        self.hs_record.save()

        # 2/ Update slot restrictions (bachelor type + a different bachelor mention)
        self.bachelor_restricted_slot.allowed_bachelor_types.clear()
        self.bachelor_restricted_slot.allowed_bachelor_types.add(
            BachelorType.objects.get(label__iexact='technologique')
        )
        self.bachelor_restricted_slot.allowed_bachelor_mentions.add(self.bachelor_mention2)

        # retry
        response = client.post(
            "/api/register",
            {'slot_id': self.bachelor_restricted_slot.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to slot's restrictions", content['msg'])

        # Fail with general bachelor teachings restrictions
        # 1/ Update high school record
        self.hs_record.bachelor_type = BachelorType.objects.get(label__iexact='général')
        self.hs_record.technological_bachelor_mention = None
        self.hs_record.general_bachelor_teachings.add(self.bachelor_teaching)
        self.hs_record.save()

        # 2/ Update slot restrictions (bachelor type + a different bachelor mention)
        self.bachelor_restricted_slot.allowed_bachelor_types.remove()
        self.bachelor_restricted_slot.allowed_bachelor_types.add(
            BachelorType.objects.get(label__iexact='général')
        )
        self.bachelor_restricted_slot.allowed_bachelor_mentions.remove()
        self.bachelor_restricted_slot.allowed_bachelor_teachings.add(self.bachelor_teaching2)

        # retry
        response = client.post(
            "/api/register",
            {'slot_id': self.bachelor_restricted_slot.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to slot's restrictions", content['msg'])

        # Test training quotas (slot2 and slot3 have the same training in the same period)
        # reset immersions and raise period quota
        self.highschool_user.immersions.all().delete()
        HighSchoolStudentRecordQuota.objects.filter(
            period=self.period,
            record=self.hs_record
        ).update(allowed_immersions=3)

        immersion = Immersion.objects.create(student=self.highschool_user, slot=self.slot2)

        training_quotas = GeneralSettings.objects.get(setting="ACTIVATE_TRAINING_QUOTAS")
        training_quotas.parameters["value"] = {
            'activate': False,
            'default_quota': 1
        }
        training_quotas.save()

        # Quota off : success
        response = client.post(
            "/api/register",
            {'slot_id': self.slot3.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Registration successfully added, confirmation email sent", content['msg'])

        # Activate quota, delete slot3 registration and retry
        Immersion.objects.filter(student=self.highschool_user, slot=self.slot3).delete()
        training_quotas.parameters['value']['activate'] = True
        training_quotas.save()

        response = client.post(
            "/api/register",
            {'slot_id': self.slot3.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            """You have no more remaining registration available for this training and this period, """
            """you should cancel an immersion or contact immersion service""",
            content['msg']
        )

        # Cancel the immersion and retry
        immersion.cancellation_type = CancelType.objects.first()
        immersion.save()
        response = client.post(
            "/api/register",
            {'slot_id': self.slot3.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(
            content,
            {
                'error': False,
                'msg': 'Registration successfully added, confirmation email sent',
                'notify_disability': 'never'
            }
        )

        # Remove first immersion cancellation and latest immersion, raise single training quota and register again
        immersion.cancellation_type = None
        immersion.save()
        Immersion.objects.filter(student=self.highschool_user, slot=self.slot3).delete()

        self.training.allowed_immersions = 2
        self.training.save()

        response = client.post(
            "/api/register",
            {'slot_id': self.slot3.id},
            **self.header,
            follow=True
        )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            content,
            {
                'error': False,
                'msg': 'Registration successfully added, confirmation email sent',
                'notify_disability': 'never'
            }
        )

        # Todo : needs more tests with other users (ref-etab, ref-str, ...)

    def test_ajax_get_duplicates(self):
        self.hs_record.duplicates = "[%s]" % self.hs_record2.id
        self.hs_record.save()

        self.hs_record2.duplicates = "[%s]" % self.hs_record.id
        self.hs_record2.save()

        client = Client()

        for username in ['ref_master_etab', 'operator']:
            client.login(username=username, password='pass')

            response = client.get("/api/get_duplicates", **self.header, follow=True)
            content = json.loads(response.content.decode('utf-8'))

            self.assertEqual(content['data'], [
                {'id': 0,
                 'record_ids': [self.hs_record.id, self.hs_record2.id],
                 'account_ids': [self.hs_record.student.id, self.hs_record2.student.id],
                 'names': ['SCHOOL high', 'SCHOOL2 high2'],
                 'birthdates': [_date(self.hs_record.birth_date), _date(self.hs_record2.birth_date)],
                 'highschools': ['HS1, 1ere S 3', 'HS1, TS 3'],
                 'emails': ['hs@no-reply.com', 'hs2@no-reply.com'],
                 'record_links': [
                     f'/immersion/hs_record/{self.hs_record.id}',
                     f'/immersion/hs_record/{self.hs_record2.id}'
                 ],
                 'record_status': [self.hs_record.validation,self.hs_record2.validation],
                 'registrations': ['Yes', 'No']}
            ])

    def test_ajax_keep_entries_master_etab(self):
        self.hs_record.duplicates = "[%s]" % self.hs_record2.id
        self.hs_record.save()

        self.hs_record2.duplicates = "[%s]" % self.hs_record.id
        self.hs_record2.save()

        client = Client()
        client.login(username='ref_master_etab', password='pass')

        data = {
            "entries[]": [self.hs_record.id, self.hs_record2.id]
        }
        response = client.post("/api/keep_entries", data, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Duplicates data cleared", content['msg'])

        r1 = HighSchoolStudentRecord.objects.get(pk=self.hs_record.id)
        r2 = HighSchoolStudentRecord.objects.get(pk=self.hs_record2.id)

        self.assertEqual(r1.solved_duplicates, f"{self.hs_record2.id}")
        self.assertEqual(r2.solved_duplicates, f"{self.hs_record.id}")

    def test_ajax_keep_entries_operator(self):
        self.hs_record.duplicates = "[%s]" % self.hs_record2.id
        self.hs_record.save()

        self.hs_record2.duplicates = "[%s]" % self.hs_record.id
        self.hs_record2.save()

        client = Client()
        client.login(username='operator', password='pass')

        data = {
            "entries[]": [self.hs_record.id, self.hs_record2.id]
        }
        response = client.post("/api/keep_entries", data, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Duplicates data cleared", content['msg'])

        r1 = HighSchoolStudentRecord.objects.get(pk=self.hs_record.id)
        r2 = HighSchoolStudentRecord.objects.get(pk=self.hs_record2.id)

        self.assertEqual(r1.solved_duplicates, f"{self.hs_record2.id}")
        self.assertEqual(r2.solved_duplicates, f"{self.hs_record.id}")

    def test_campus_list(self):
        url = reverse("campus_list")
        view_permission = Permission.objects.get(codename='view_campus')
        add_permission = Permission.objects.get(codename='add_campus')

        campus = Campus.objects.create(label='Campus', establishment=self.establishment, active=True)

        # GET
        client = Client()
        client.login(username='ref_etab', password='pass')

        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content[0]['label'], campus.label)

        # with API user
        # List (GET)
        self.assertTrue(Campus.objects.exists())

        # Without permission
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all campuses are there
        for campus in Campus.objects.all():
            self.assertTrue(campus.id in [c['id'] for c in result])

        # Creation (POST)
        self.assertFalse(Campus.objects.filter(label='Campus Test').exists())
        establishment = Establishment.objects.first()
        data = {
            "label": "Campus Test",
            "active": True,
            "establishment": establishment.id,
            "department": '67',
            "zip_code": '67000',
            "city": 'STRASBOURG',
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('label'), "Campus Test")
        self.assertTrue(Campus.objects.filter(label='Campus Test').exists())

        # Duplicated label within the same establishment : error
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {
            'non_field_errors': ['A Campus object with the same establishment and label already exists']
        })

        # Create multiple campuses at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(Campus.objects.filter(label='Campus test A').exists())
        self.assertFalse(Campus.objects.filter(label='Campus test B').exists())
        data = [{
            "label": "Campus test A",
            "active": True,
            "establishment": establishment.id,
            "department": '67',
            "zip_code": '67000',
            "city": 'STRASBOURG',
        }, {
            "label": "Campus test B",
            "active": False,
            "establishment": establishment.id,
            "department": '33',
            "zip_code": '33000',
            "city": 'BORDEAUX',
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Campus.objects.filter(label='Campus test A', active=True).exists())
        self.assertTrue(Campus.objects.filter(label='Campus test B', active=False).exists())

    def test_building_list(self):
        url = reverse("building_list")
        view_permission = Permission.objects.get(codename='view_building')
        add_permission = Permission.objects.get(codename='add_building')

        building = Building.objects.create(
            label='Building', campus=self.campus, url='http://test.fr', active=True
        )

        # GET
        client = Client()
        client.login(username='ref_etab', password='pass')

        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(content[0]['label'], building.label)

        # with API user
        # List (GET)
        self.assertTrue(Building.objects.exists())

        # Without permission
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all buildings are there
        for building in Building.objects.all():
            self.assertTrue(building.id in [b['id'] for b in result])

        # Creation (POST)
        self.assertFalse(Building.objects.filter(label='Building Test').exists())
        data = {
            "label": "Building Test",
            "active": True,
            "url": "http://my-building.fr",
            "campus": self.campus.id
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('label'), "Building Test")
        self.assertTrue(Building.objects.filter(label='Building Test').exists())

        # Duplicated label with the same campus : error
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {
            'non_field_errors': ['A Building object with the same campus and label already exists']
        })

        # Create multiple buildings at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(Building.objects.filter(label='Building test A').exists())
        self.assertFalse(Building.objects.filter(label='Building test B').exists())
        data = [{
            "label": "Building test A",
            "active": True,
            "url": "https://url.test",
            "campus": self.campus.id
        }, {
            "label": "Building test B",
            "active": False,
            "url": "https://another.test",
            "campus": self.campus.id
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Building.objects.filter(label='Building test A', active=True).exists())
        self.assertTrue(Building.objects.filter(label='Building test B', active=False).exists())

    def test_speaker_list(self):
        url = reverse("speaker_list")
        view_permission = Permission.objects.get(codename='view_immersionuser')
        add_permission = Permission.objects.get(codename='add_immersionuser')

        # Without permission
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all speakers are there
        for speaker in ImmersionUser.objects.filter(groups__name='INTER'):
            self.assertTrue(speaker.id in [s['id'] for s in result])

        # Creation (POST)
        self.assertFalse(ImmersionUser.objects.filter(email='new_speaker@domain.tld').exists())
        data = {
            "establishment": self.establishment.pk,
            "email": "new_speaker@domain.tld",
            "first_name": "Jean-Jacques",
            "last_name": "Doe",
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)

        # missing establishment/high school
        data.pop("establishment")
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            result['error'],
            {'non_field_errors': ['Either an establishment or a high school is mandatory']}
        )

        # Non-existing establishment : Fail
        data["establishment"] = 999999
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            result['error'],
            {'establishment': ['Invalid pk "999999" - object does not exist.']}
        )

        # Retry: success
        data["establishment"] = self.establishment.pk
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result["data"].get('email'), "new_speaker@domain.tld")
        self.assertTrue(ImmersionUser.objects.filter(email='new_speaker@domain.tld', groups__name='INTER').exists())
        user = ImmersionUser.objects.get(email='new_speaker@domain.tld', groups__name='INTER')
        self.assertEqual(user.username, "new_speaker@domain.tld")

        # Duplicate
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            {'email': ['User with this Email already exists.']}
        )
        self.assertEqual(ImmersionUser.objects.filter(email='new_speaker@domain.tld').count(), 1)

    def test_get_course_speakers(self):
        url = f"/api/speakers/courses/{self.course.id}"
        speaker = self.course.speakers.first()

        # Check access for the following users
        for user in [self.operator_user, self.ref_master_etab_user, self.ref_etab_user, self.ref_str, self.ref_lyc]:
            self.client.login(username=user.username, password='pass')
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content.decode('utf-8'))

            self.assertEqual(content, [{
                "id": speaker.id,
                "last_name": speaker.last_name,
                "first_name": speaker.first_name,
                "email": speaker.email,
                "establishment": speaker.establishment.pk,
                "highschool": speaker.highschool,
                "is_active": speaker.is_active,
                "has_courses": speaker.courses.exists(),
                "can_delete": not speaker.courses.exists()
            }])

    def test_get_event_speakers(self):
        event_type = OffOfferEventType.objects.create(
            label="My event type",
            active=True
        )

        event = OffOfferEvent.objects.create(
            establishment=self.establishment,
            label="Whatever",
            description="",
            event_type=event_type,
            published=True
        )

        event.speakers.add(self.speaker1)

        url = f"/api/speakers/events/{event.id}"

        # Check access for the following users
        for user in [self.operator_user, self.ref_master_etab_user, self.ref_etab_user, self.ref_str, self.ref_lyc]:
            self.client.login(username=user.username, password='pass')
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content.decode('utf-8'))

            self.assertEqual(content, [{
                "id": self.speaker1.id,
                "last_name": self.speaker1.last_name,
                "first_name": self.speaker1.first_name,
                "email": self.speaker1.email,
                "establishment": self.speaker1.establishment.pk,
                "highschool": self.speaker1.highschool,
                "is_active": self.speaker1.is_active,
                "has_courses": self.speaker1.courses.exists(),
                "can_delete": not self.speaker1.courses.exists()
            }])

    def test_high_school_list(self):
        url = reverse("highschool_list")
        view_permission = Permission.objects.get(codename='view_highschool')
        add_permission = Permission.objects.get(codename='add_highschool')

        self.assertTrue(HighSchool.objects.count() > 0)

        # Unauthenticated GET
        self.client.logout()
        response = self.client.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'Authentication credentials were not provided.')

        # Agreed high schools : success
        response = self.client.get("/api/highschools?agreed=true")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result), 1)

        # Add view permission
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all high school are there
        for highschool in HighSchool.objects.all():
            self.assertTrue(highschool.id in [h['id'] for h in result])

        # Creation (POST)
        self.assertFalse(HighSchool.objects.filter(label='New High School').exists())
        data = {
            "label": "New High School",
            "country": "FR",
            "address": "First line",
            "address2": "Second line",
            "address3": "Third line",
            "department": "Deux-Sèvres",
            "city": "NIORT",
            "zip_code": "79000",
            "phone_number": "05 49 00 00 00",
            "fax": "05 48 00 00 00",
            "email": "nhs@domain.tld",
            "head_teacher_name": "Mme Louise DOE",
            "convention_start_date": "2023-01-01",
            "convention_end_date": "2023-07-31",
            "postbac_immersion": True,
            "mailing_list": "mailing_list@domain.tld",
            "badge_html_color": "#556677",
            "certificate_header": "My custom header",
            "certificate_footer": "My custom footer",
            "uses_student_federation": True,
        }

        # 0670081Z

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)

        # uses_student_federation True but missing UAI codes
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertFalse(HighSchool.objects.filter(label='New High School').exists())
        self.assertEqual(
            result['error'],
            {'non_field_errors': ['You have to add at least one UAI code when using student federation']}
        )

        # Add uai codes and retry
        data.update({
            "uai_codes": ['0670081Z', '0670082A']
        })
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(result.get('email'), "nhs@domain.tld")
        self.assertTrue(HighSchool.objects.filter(label='New High School').exists())

        new_high_school = HighSchool.objects.get(label='New High School')
        self.assertEqual(new_high_school.uai_codes.count(), 2)

        # Duplicate
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            {'non_field_errors': ['A high school object with the same label and city already exists']}
        )
        self.assertEqual(HighSchool.objects.filter(label='New High School').count(), 1)

        # Creation without student federation
        data.pop('uai_codes')
        data.update({
            'label': "Another High School",
            'uses_student_federation': False,
            'email': 'ahs@domain.tld',
        })
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('email'), "ahs@domain.tld")
        self.assertTrue(HighSchool.objects.filter(label='Another High School').exists())

    def test_high_school_update(self):
        view_permission = Permission.objects.get(codename='view_highschool')
        change_permission = Permission.objects.get(codename='change_highschool')

        # Add perms
        self.api_user.user_permissions.add(view_permission)

        # Create a high school
        high_school = HighSchool.objects.create(
            label='My Cool Label',
            address='x',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='mchs@domain.tld',
            mailing_list='list-mchs@domain.tld',
            head_teacher_name='M. A B',
            convention_start_date=self.today - timedelta(days=10),
            convention_end_date=self.today + timedelta(days=10),
            postbac_immersion=True,
            signed_charter=True,
        )

        url = reverse("highschool_detail", kwargs={"pk": high_school.pk})

        # Define new data for patch
        data = {
            "email": 'mchs2@domain.tld',
        }

        # Unauthenticated PATCH
        self.client.logout()
        response = self.client.patch(url, data=json.dumps(data), content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'Authentication credentials were not provided.')

        # Without rights
        response = self.api_client_token.patch(url, data=json.dumps(data), content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add change permission
        self.api_user.user_permissions.add(change_permission)
        response = self.api_client_token.patch(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        high_school.refresh_from_db()
        # self.assertEqual(high_school.label, "My New Cool Label")
        self.assertEqual(high_school.email, "mchs2@domain.tld")

        # Don't allow an existing (city, label)
        data = {
            "label": self.high_school.label,
            "city": self.high_school.city
        }
        response = self.api_client_token.patch(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(
            result['error'],
            {'non_field_errors': ['A high school object with the same label and city already exists']}
        )

    def test_high_school_delete(self):
        delete_permission = Permission.objects.get(codename='delete_highschool')

        # Create a high school
        high_school = HighSchool.objects.create(
            label='My Cool Label',
            address='x',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='mchs@domain.tld',
            mailing_list='list-mchs@domain.tld',
            head_teacher_name='M. A B',
            convention_start_date=self.today - timedelta(days=10),
            convention_end_date=self.today + timedelta(days=10),
            postbac_immersion=True,
            signed_charter=True,
        )

        # Link high school to related objects
        hs_user = get_user_model().objects.create_user(
            username='temp_hs_user',
            password='pass',
            email='hs@domain.tld',
            first_name='high',
            last_name='SCHOOL',
            highschool=high_school
        )

        url = reverse("highschool_detail", kwargs={"pk": high_school.pk})

        # Unauthenticated DELETE
        self.client.logout()
        response = self.client.delete(url, content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'Authentication credentials were not provided.')

        # Without rights
        response = self.api_client_token.delete(url, content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Add delete permission
        # Still not good : there are related objects
        self.api_user.user_permissions.add(delete_permission)
        response = self.api_client_token.delete(url, content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], ["Objects 'Users' are linked to this high school, it can't be deleted"])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Retry
        hs_user.delete()
        response = self.api_client_token.delete(url, content_type="application/json")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['msg'], "High school successfully deleted")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(HighSchool.objects.filter(label="My Cool Label").exists())

    def test_high_school_speakers(self):
        client = Client()

        # Success
        client.login(username='ref_lyc', password='pass')
        response = client.get(f"/api/speakers?highschool={self.high_school.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(content[0], {
            'id': self.highschool_speaker.id,
            'last_name': 'highschool_speaker',
            'first_name': 'highschool_speaker',
            'email': 'highschool_speaker@no-reply.com',
            'establishment': self.highschool_speaker.establishment,
            'is_active': True,
            'has_courses': True,
            'can_delete': False,
            'highschool': self.highschool_speaker.highschool.pk,
        })

    def test_off_offer_event(self):
        event = OffOfferEvent.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=None,
            event_type=self.event_type,
            label="Establishment event",
            description="Whatever",
            published=True
        )

        event2 = OffOfferEvent.objects.create(
            establishment=None,
            structure=None,
            highschool=self.high_school,
            event_type=self.event_type,
            label="High school event",
            description="Whatever",
            published=True
        )

        client = Client()
        client.login(username='ref_etab', password='pass')

        # List
        response = client.get(reverse("off_offer_event_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['label'], 'Establishment event')
        self.assertEqual(content[0]['establishment']['id'], self.establishment.id)
        self.assertEqual(content[0]['establishment']['code'], 'ETA1')
        self.assertEqual(content[0]['establishment']['label'], 'Etablissement 1')

        # As ref-lyc
        client.login(username='ref_lyc', password='pass')
        response = client.get(reverse("off_offer_event_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['label'], 'High school event')
        self.assertEqual(content[0]['highschool']["city"], self.high_school.city)
        self.assertEqual(content[0]['highschool']["label"], self.high_school.label)

        # As ref-str (with no structure) : empty
        self.ref_str.structures.remove(self.structure)
        client.login(username='ref_str', password='pass')
        response = client.get(reverse("off_offer_event_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(content), 0)

        # Deletion
        # as ref_str : fail (bad structure)
        response = client.delete(reverse("off_offer_event_detail", kwargs={'pk': event.id}))
        self.assertIn("Insufficient privileges", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(OffOfferEvent.objects.count(), 2)

        # as ref_etab : same establishment : success
        client.login(username='ref_etab', password='pass')
        response = client.delete(reverse("off_offer_event_detail", kwargs={'pk': event.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OffOfferEvent.objects.count(), 1)

        # as master_ref_etab : full access
        client.login(username='ref_master_etab', password='pass')
        response = client.delete(reverse("off_offer_event_detail", kwargs={'pk': event2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OffOfferEvent.objects.count(), 0)

        # as operator : full access
        event2 = OffOfferEvent.objects.create(
            establishment=None,
            structure=None,
            highschool=self.high_school,
            event_type=self.event_type,
            label="High school event",
            description="Whatever",
            published=True
        )

        client.login(username='operator', password='pass')
        response = client.delete(reverse("off_offer_event_detail", kwargs={'pk': event2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OffOfferEvent.objects.count(), 0)

    def test_API__get_visitor_records__bad_operation(self):
        url = "/api/visitor/records/wrong"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)
        self.assertIsNone(content["data"])
        self.assertEqual(
            content["msg"],
            "No operator given or wrong operator (to_validate, validated, rejected, to_revalidate)"
        )

    def test_API__get_visitor_records__to_validate(self):
        url = "/api/visitor/records/to_validate"

        # Add empty attestations to check 'invalid_dates'
        VisitorRecordDocument.objects.create(
            record=self.visitor_record,
            attestation=self.attestation_2,
            validity_date=None,
            for_minors=self.attestation_2.for_minors,
            mandatory=self.attestation_2.mandatory,
            requires_validity_date=self.attestation_2.requires_validity_date,
        )

        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertEqual(content["msg"], "")

        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["user_first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["user_last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["invalid_dates"], 1)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%Y-%m-%d"))

    def test_API__get_visitor_records__validated(self):
        self.visitor_record.validation = 2
        self.visitor_record.save()
        url = "/api/visitor/records/validated"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertEqual(content["msg"], "")

        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["user_first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["user_last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%Y-%m-%d"))

    def test_API__get_visitor_records__rejected(self):
        self.visitor_record.validation = 3
        self.visitor_record.save()
        url = "/api/visitor/records/rejected"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertEqual(content["msg"], "")
        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["user_first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["user_last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%Y-%m-%d"))

    def test_API_visitor_record_operation__wrong_operation(self):
        client = Client()
        client.login(username='ref_master_etab', password='pass')
        url = f"/api/visitor/record/{self.visitor_record.id}/wrong"
        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("msg", content)
        self.assertIn("data", content)
        self.assertIsNone(content["data"])
        self.assertEqual(content["msg"], "Error - Bad operation selected. Allowed: validate, reject")

        # no change
        record = VisitorRecord.objects.get(id=self.visitor_record.id)
        self.assertEqual(record.validation, self.visitor_record.validation)

    def test_API_visitor_record_operation__validate(self):
        client = Client()
        client.login(username='ref_master_etab', password='pass')
        url = f"/api/visitor/record/{self.visitor_record.id}/validate"

        record = VisitorRecord.objects.get(id=self.visitor_record.id)
        self.assertEqual(record.validation, 1)

        # Add 2 documents :
        # - first one has no validity date and will be deleted
        # - the second requires a validity date and should be kept upon record validation

        document = VisitorRecordDocument.objects.create(
            record=self.visitor_record,
            attestation=self.attestation_1,
            validity_date=None,
            for_minors=self.attestation_1.for_minors,
            mandatory=self.attestation_1.mandatory,
            requires_validity_date=False,
        )

        document_2 = VisitorRecordDocument.objects.create(
            record=self.visitor_record,
            attestation=self.attestation_2,
            validity_date=None,
            for_minors=self.attestation_2.for_minors,
            mandatory=self.attestation_2.mandatory,
            requires_validity_date=self.attestation_2.requires_validity_date,
        )

        # Fail : missing validity date on 'document_2'
        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Error: record has missing or invalid attestation dates")
        record.refresh_from_db()
        self.assertEqual(record.validation, 1)

        # Add a date and retry : Success
        document_2.validity_date = self.today + timedelta(days=2)
        document_2.save()

        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Record updated, notification sent")
        self.assertEqual(content["data"]["record_id"], self.visitor_record.id)

        # value changed
        record.refresh_from_db()
        self.assertEqual(record.validation, VisitorRecord.STATUSES["VALIDATED"])

        # Check documents
        self.assertTrue(
            VisitorRecordDocument.objects.filter(record=self.visitor_record, attestation=self.attestation_2).exists()
        )
        self.assertFalse(
            VisitorRecordDocument.objects.filter(record=self.visitor_record, attestation=self.attestation_1).exists()
        )

    def test_API_visitor_record_operation__reject(self):
        client = Client()
        client.login(username='ref_master_etab', password='pass')
        url = f"/api/visitor/record/{self.visitor_record.id}/reject"
        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("msg", content)
        self.assertIn("data", content)
        self.assertIsInstance(content["data"], dict)
        self.assertEqual(content["msg"], "Record updated, notification sent")

        self.assertEqual(content["data"]["record_id"], self.visitor_record.id)

        # value changed
        record = VisitorRecord.objects.get(id=self.visitor_record.id)
        self.assertEqual(record.validation, 3)

    def test_API_visitor_record_operation__bad_record_id(self):
        client = Client()
        client.login(username='ref_master_etab', password='pass')

        url = f"/api/visitor/record/99999999999/validate"
        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("msg", content)
        self.assertIn("data", content)
        self.assertIsNone(content["data"])
        self.assertGreater(len(content["msg"]), 0)

    def test_API_mailing_list_global__valid(self):
        self.hs_record.validation = 2
        self.visitor_record.validation = 2
        self.hs_record.save()
        self.visitor_record.save()

        url = "/api/mailing_list/global"
        response = self.client_token.get(url)
        content = json.loads(response.content.decode("utf-8"))

        email = get_general_setting("GLOBAL_MAILING_LIST")

        self.assertEqual(content["msg"], "")
        self.assertIsInstance(content["data"], dict)
        self.assertIn(email, content["data"])

        self.assertEqual(len(content["data"][email]), 4)
        self.assertIn(self.student.email, content["data"][email])
        self.assertIn(self.student2.email, content["data"][email])
        self.assertIn(self.highschool_user.email, content["data"][email])
        self.assertIn(self.visitor.email, content["data"][email])

        self.hs_record.validation = 0
        self.visitor_record.validation = 0
        self.hs_record.save()
        self.visitor_record.save()

    def test_API_mailing_list_global__wrong_global_setting(self):
        g = GeneralSettings.objects.get(setting="GLOBAL_MAILING_LIST")
        g.setting = "GLOBAL_MAILING_LIST_"
        g.save()

        url = "/api/mailing_list/global"
        response = self.client_token.get(url)

        content = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertGreater(len(content["msg"]), 0)
        self.assertIsNone(content["data"])

        g.setting = "GLOBAL_MAILING_LIST"
        g.save()

    def test_API_mailing_list_structure(self):
        url = "/api/mailing_list/structures"
        response = self.client_token.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["msg"], "")
        self.assertIsInstance(content["data"], dict)

        self.assertEqual(len(content["data"]), 1)

        self.assertIn(self.structure.mailing_list, content["data"])

        str_list = content["data"][self.structure.mailing_list]
        self.assertEqual(len(str_list), 2)
        self.assertIn(self.highschool_user.email, str_list)
        self.assertIn(self.student.email, str_list)

    def test_API_mailing_list_establishments(self):
        url = "/api/mailing_list/establishments"

        event = OffOfferEvent.objects.create(
            label="event_xxx", description="event_xxx",
            establishment=self.establishment, event_type=self.event_type
        )
        slot = Slot.objects.create(event=event, n_places=30)
        immersion = Immersion.objects.create(student=self.visitor, slot=slot)

        response = self.client_token.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["msg"], "")
        self.assertIsInstance(content["data"], dict)

        self.assertEqual(len(content["data"]), 1)
        self.assertIn(self.establishment.mailing_list, content["data"])

        str_list = content["data"][self.establishment.mailing_list]
        self.assertEqual(len(str_list), 3)
        self.assertIn(self.highschool_user.email, str_list)
        self.assertIn(self.student.email, str_list)
        self.assertIn(self.visitor.email, str_list)

    def test_API_mailing_list_high_schools(self):
        url = "/api/mailing_list/high_schools"

        event = OffOfferEvent.objects.create(
            label="event_xxx", description="event_xxx",
            highschool=self.high_school, event_type=self.event_type
        )
        slot = Slot.objects.create(event=event, n_places=30)
        immersion = Immersion.objects.create(student=self.highschool_user, slot=slot)

        response = self.client_token.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content["msg"], "")
        self.assertIsInstance(content["data"], dict)

        self.assertEqual(len(content["data"]), 1)
        self.assertIn(self.high_school.mailing_list, content["data"])

        str_list = content["data"][self.high_school.mailing_list]
        self.assertEqual(len(str_list), 1)
        self.assertIn(self.highschool_user.email, str_list)

    def test_structure_list(self):
        view_permission = Permission.objects.get(codename='view_structure')
        add_permission = Permission.objects.get(codename='add_structure')
        url = reverse("structure_list")

        # List (GET)
        self.assertTrue(Structure.objects.exists())

        # Without permission
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all structures are there
        for structure in Structure.objects.all():
            self.assertTrue(structure.id in [s['id'] for s in result])

        # Creation (POST)
        self.assertFalse(Structure.objects.filter(code='STR-TEST').exists())
        establishment = Establishment.objects.first()
        data = {
          "code": "STR-TEST",
          "label": "Structure test",
          "mailing_list": "str@example.com",
          "active": True,
          "establishment": establishment.id
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('code'), "STR-TEST")
        self.assertTrue(Structure.objects.filter(code='STR-TEST').exists())

        # Duplicated code : error
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'code': ['Structure with this Code already exists.']})

        # Duplicate label within the same establishment : error
        data["code"] = "ANOTHER-STR-CODE"
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            {'non_field_errors': ["A Structure object with the same establishment and label already exists"]}
        )

        # Create multiple structures at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(Structure.objects.filter(code='STR-TEST-A').exists())
        self.assertFalse(Structure.objects.filter(code='STR-TEST-B').exists())
        data = [{
            "code": "STR-TEST-A",
            "label": "Structure test A",
            "mailing_list": "str@example.com",
            "active": True,
            "establishment": establishment.id
        },{
            "code": "STR-TEST-B",
            "label": "Structure test B",
            "mailing_list": "str@example.com",
            "active": True,
            "establishment": establishment.id
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Structure.objects.filter(code='STR-TEST-A').exists())
        self.assertTrue(Structure.objects.filter(code='STR-TEST-B').exists())

    def test_training_domain_list(self):
        view_permission = Permission.objects.get(codename='view_trainingdomain')
        add_permission = Permission.objects.get(codename='add_trainingdomain')
        url = reverse("training_domain_list")

        # List
        self.assertTrue(TrainingDomain.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for training_domain in TrainingDomain.objects.all():
            self.assertTrue(training_domain.id in [td['id'] for td in result])

        # Creation (POST)
        self.assertFalse(TrainingDomain.objects.filter(label='Training domain test').exists())
        data = {
            "label": "Training domain test",
            "active": True
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('label'), "Training domain test")
        self.assertTrue(TrainingDomain.objects.filter(label='Training domain test').exists())
        self.assertEqual(TrainingDomain.objects.filter(label__iexact='Training domain test').count(), 1)

        # Unique label : fail
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'label': ['Training domain with this Label already exists.']})

        # Create multiple training domains at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(TrainingDomain.objects.filter(label='Training domain test A').exists())
        self.assertFalse(TrainingDomain.objects.filter(label='Training domain test B').exists())
        data = [{
            "label": "Training domain test A",
            "active": True,
        }, {
            "label": "Training domain test B",
            "active": True,
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(TrainingDomain.objects.filter(label='Training domain test A').exists())
        self.assertTrue(TrainingDomain.objects.filter(label='Training domain test B').exists())

    def test_course_type(self):
        view_permission = Permission.objects.get(codename='view_coursetype')
        add_permission = Permission.objects.get(codename='add_coursetype')
        url = reverse("course_type_list")

        # List
        self.assertTrue(CourseType.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for course_type in CourseType.objects.all():
            self.assertTrue(course_type.id in [ct['id'] for ct in result])

        # Creation (POST)
        self.assertFalse(CourseType.objects.filter(label='Course type test').exists())
        data = {
            "label": "Course type test",
            "full_label": "Course type full label",
            "active": True
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('label'), "Course type test")
        self.assertTrue(CourseType.objects.filter(label='Course type test').exists())
        self.assertEqual(CourseType.objects.filter(label__iexact='Course type test').count(), 1)

        # Unique label : fail
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {
            'label': ['Course type with this Short label already exists.'],
            'full_label': ['Course type with this Full label already exists.']
        })

        # Create multiple course types at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(CourseType.objects.filter(label='Course type test A').exists())
        self.assertFalse(CourseType.objects.filter(label='Course type test B').exists())
        data = [{
            "label": "Course type test A",
            "full_label": "Course type full test A",
            "active": True,
        }, {
            "label": "Course type test B",
            "full_label": "Course type full test B",
            "active": True,
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(CourseType.objects.filter(label='Course type test A').exists())
        self.assertTrue(CourseType.objects.filter(label='Course type test B').exists())

        c_type = CourseType.objects.get(label='Course type test A')

        # Detail
        url = reverse("course_type_detail", args=[c_type.id, ])
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result, {
            'id': c_type.id,
            'label': 'Course type test A',
            'full_label': 'Course type full test A',
            'active': True
        })

    def test_training_subdomain_list(self):
        view_permission = Permission.objects.get(codename='view_trainingsubdomain')
        add_permission = Permission.objects.get(codename='add_trainingsubdomain')
        url = reverse("training_subdomain_list")

        # List
        self.assertTrue(TrainingSubdomain.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for training_subdomain in TrainingSubdomain.objects.all():
            self.assertTrue(training_subdomain.id in [tsd['id'] for tsd in result])

        # Creation (POST)
        training_domain = TrainingDomain.objects.first()

        self.assertFalse(TrainingSubdomain.objects.filter(label='Training subdomain test').exists())
        data = {
            "label": "Training subdomain test",
            "active": True,
            "training_domain": training_domain.id
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result.get('label'), "Training subdomain test")
        self.assertTrue(TrainingSubdomain.objects.filter(label='Training subdomain test').exists())
        self.assertEqual(TrainingSubdomain.objects.filter(label__iexact='Training subdomain test').count(), 1)

        # Duplicated label : fail
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'label': ['Training sub domain with this Label already exists.']})

        # Missing training domain : fail
        data = {
            "label": "Another training subdomain test",
            "active": True
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'training_domain': ['This field is required.']})

        # Create multiple training sub domains at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(TrainingSubdomain.objects.filter(label='Training subdomain test A').exists())
        self.assertFalse(TrainingSubdomain.objects.filter(label='Training subdomain test B').exists())
        data = [{
            "label": "Training subdomain test A",
            "active": True,
            "training_domain": training_domain.id
        }, {
            "label": "Training subdomain test B",
            "active": True,
            "training_domain": training_domain.id
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(TrainingSubdomain.objects.filter(label='Training subdomain test A').exists())
        self.assertTrue(TrainingSubdomain.objects.filter(label='Training subdomain test B').exists())

    def test_training_list(self):
        url = reverse('training_list')

        # GET as users
        # Establishment manager
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = sorted(json.loads(response.content.decode()), key=lambda k:k['id'])

        self.assertEqual(content, [{
            'id': self.training.pk,
            'label': 'test training',
            'training_subdomains': [{
                'id': self.t_sub_domain.pk,
                'training_domain': {
                   "id": self.t_sub_domain.training_domain.pk,
                   "label": self.t_sub_domain.training_domain.label,
                   "active": self.t_sub_domain.training_domain.active
                },
                'label': 'test t_sub_domain',
                'active': True
            }],
            'nb_courses': 1,
            'active': True,
            'url': None,
            'structures': [self.structure.pk],
            'highschool': None,
            'allowed_immersions': None,
        }, {
            'id': self.training2.pk,
            'label': 'test training 2',
            'training_subdomains': [{
                'id': self.t_sub_domain.pk,
                'training_domain': {
                   "id": self.t_sub_domain.training_domain.pk,
                   "label": self.t_sub_domain.training_domain.label,
                   "active": self.t_sub_domain.training_domain.active
                },
                'label': 'test t_sub_domain',
                'active': True
            }],
            'nb_courses': 0,
            'active': True,
            'url': None,
            'structures': [self.structure.pk],
            'highschool': None,
            'allowed_immersions': None,
        }])

        # High school manager
        self.client.logout()
        self.client.login(username='ref_lyc', password='pass')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = sorted(json.loads(response.content.decode()), key=lambda k:k['id'])

        self.assertEqual(content, [{
            'id': self.highschool_training.pk,
            'label': 'test highschool training',
            'training_subdomains': [{
                'id': self.t_sub_domain.pk,
                'training_domain': {
                    "id": self.t_sub_domain.training_domain.pk,
                    "label": self.t_sub_domain.training_domain.label,
                    "active": self.t_sub_domain.training_domain.active
                },
                'label': 'test t_sub_domain',
                'active': True
            }],
            'active': True,
            'nb_courses': 1,
            'url': None,
            'structures': [],
            'highschool': self.high_school.pk,
            'allowed_immersions': None,
        }])

        # API with token
        view_permission = Permission.objects.get(codename='view_training')
        add_permission = Permission.objects.get(codename='add_training')
        url = reverse("training_list")
        # List
        self.assertTrue(Training.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for training in Training.objects.all():
            self.assertTrue(training.id in [t['id'] for t in result])

        # Creation (POST)
        structure = Structure.objects.first()
        training_subdomain = TrainingSubdomain.objects.first()

        self.assertFalse(Training.objects.filter(label='Training test').exists())
        data = {
            "label": "Training test",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id]
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(result.get('label'), "Training test")
        self.assertTrue(Training.objects.filter(label='Training test').exists())
        self.assertEqual(Training.objects.filter(label__iexact='Training test').count(), 1)

        # Missing training subdomains : fail
        data = {
            "label": "Another training test",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [],
            "structures": [structure.id]
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {
            'training_subdomains': ["'Another training test' : please provide at least one training subdomain"]
        })

        # Missing structure and highschool : fail
        data = {
            "label": "Another training test",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [training_subdomain.id],
            "structures": []
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            {'non_field_errors': ["'Another training test' : please provide a structure or a high school"]}
        )

        # Structure and highschool : fail (only one allowed)
        data = {
            "label": "Another training test",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id],
            "highschool": self.high_school.id
        }

        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            { 'non_field_errors':
                  ["'Another training test' : high school and structures can't be set together. Please choose one."]
            }
        )

        # Create multiple trainings at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(Training.objects.filter(label='Training test A').exists())
        self.assertFalse(Training.objects.filter(label='Training test B').exists())
        data = [{
            "label": "Training test A",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id]
        }, {
            "label": "Training test B",
            "url": "http://test.com",
            "active": True,
            "training_subdomains": [training_subdomain.id],
            "structures": [structure.id]
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Training.objects.filter(label='Training test A').exists())
        self.assertTrue(Training.objects.filter(label='Training test B').exists())

    def test_course_list(self):
        """
        Test CourseList called from a datatable with various options
        """
        self.client.login(username='ref_etab', password='pass')
        request.user = self.ref_etab_user

        url = f"/api/courses?training__structures={self.structure.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content), 1)
        c = content[0]
        self.assertEqual(c['id'], self.course.id)
        self.assertEqual(c['published'], self.course.published)
        self.assertEqual(c['training']['label'], self.course.training.label)
        self.assertEqual(c['label'], self.course.label)
        self.assertEqual(c['structure']['code'], self.course.structure.code)
        self.assertEqual(c['structure']['id'], self.course.structure.id)

        speakers = [{
            'last_name': sp.last_name,
            'first_name': sp.first_name,
            'email': sp.email,
            "establishment": sp.establishment.pk if sp.establishment else None,
            "id": sp.pk,
            "highschool": sp.highschool.pk if sp.highschool else None,
            'is_active': sp.is_active,
            'has_courses': sp.courses.exists(),
            'can_delete': not sp.courses.exists()
        } for sp in self.course.speakers.all()]

        for speaker in c['speakers']:
            self.assertIn(speaker, speakers)

        self.assertEqual(c['slots_count'], self.course.slots_count())
        self.assertEqual(c['n_places'], self.course.free_seats())
        self.assertEqual(c['published_slots_count'], self.course.published_slots_count())
        self.assertEqual(c['registered_students_count'], self.course.registrations_count())
        self.assertEqual(c['alerts_count'], self.course.get_alerts_count())
        self.assertEqual(c['can_delete'], not self.course.slots.exists())

        """
        # Is this still an error ?

        url = "/api/courses"
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], 'Error : a valid structure or high school must be selected')
        """

        self.client.login(username='cons_str', password='pass')
        request.user = self.cons_str

        url = f"/api/courses?training__structures={self.structure.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content), 1)
        c = content[0]
        self.assertEqual(c['id'], self.course.id)
        self.assertEqual(c['published'], self.course.published)
        self.assertEqual(c['training']['label'], self.course.training.label)
        self.assertEqual(c['label'], self.course.label)
        self.assertEqual(c['structure']['code'], self.course.structure.code)
        self.assertEqual(c['structure']['id'], self.course.structure.id)


    @patch('ldap3.Connection.__init__', side_effect=mocked_ldap_connection)
    @patch('ldap3.Connection.bind', side_effect=mocked_ldap_bind)
    @patch('immersionlyceens.libs.api.accounts.ldap.AccountAPI.search_user', side_effect=mocked_search_user)
    def test_course_creation(self, mocked_search_user, mocked_account_api, mocked_ldap_connection):
        view_permission = Permission.objects.get(codename='view_course')
        add_permission = Permission.objects.get(codename='add_course')
        url = reverse("course_list")

        # List
        self.assertTrue(Course.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission and try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for course in Course.objects.all():
            self.assertTrue(course.id in [c['id'] for c in result])

        # =======================================================
        # Creation (POST)
        # =======================================================
        structure = self.structure
        training = Training.objects.first()

        # Speakers are optional when the course is not published
        self.assertFalse(Course.objects.filter(label='Course test').exists())
        data = {
            "label": "Course test",
            "published": False,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": []
        }

        # Without permission
        response = self.api_client_token.post(url, data)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add add permission and try again
        self.api_user.user_permissions.add(add_permission)
        response = self.api_client_token.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result["data"].get('label'), "Course test")
        self.assertTrue(Course.objects.filter(label='Course test').exists())
        self.assertEqual(Course.objects.filter(label__iexact='Course test').count(), 1)

        # Missing training id : fail
        data = {
            "label": "Course test",
            "published": False,
            "url": "http://test.com",
            "training": "",
            "structure": structure.id,
            "speakers": []
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'training': ['This field may not be null.']})

        # Missing structure and highschool : fail
        data = {
            "label": "Course test",
            "published": False,
            "url": "http://test.com",
            "training": training.id,
            "structure": "",
            "speakers": []
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'non_field_errors': ["Please provide a structure or a high school"]})

        # Both structure and highschool : fail
        data = {
            "label": "Course test",
            "published": False,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "highschool": self.high_school.id,
            "speakers": []
        }
        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'],
            {'non_field_errors': ["High school and structures can't be set together. Please choose one."]}
        )

        # Published course : speakers required
        data = {
            "label": "Course test",
            "published": True,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": []
        }

        response = self.api_client_token.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], {'non_field_errors': ["A published course requires at least one speaker"]})

        # Create multiple courses at once
        # Mind the content_type, as test Client expects a dict and not a list
        self.assertFalse(Course.objects.filter(label='Course test A').exists())
        self.assertFalse(Course.objects.filter(label='Course test B').exists())
        data = [{
            "label": "Course test A",
            "published": False,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": []
        }, {
            "label": "Course test B",
            "published": False,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": []
        }]

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Course.objects.filter(label='Course test A').exists())
        self.assertTrue(Course.objects.filter(label='Course test B').exists())

        # Create a published course with a new speaker (email)
        self.assertFalse(Course.objects.filter(label='Course test C').exists())

        # Establishment has no account provider plugin
        data = {
            "label": "Course test C",
            "published": True,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": [],
            "emails": ["new_user@domain.tld"]
        }

        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(
            result['error'], [
                """Course 'Course test C' : speaker 'new_user@domain.tld' has to be """
                """manually created before using it in a course"""
            ]
        )
        self.assertFalse(Course.objects.filter(label='Course test C').exists())
        self.assertFalse(ImmersionUser.objects.filter(email='new_user@domain.tld').exists())

        # With an establishment with account provider plugin
        self.establishment3.data_source_settings = {
            "DN": "cn=app",
            "HOST": "127.0.0.1",
            "PORT": "389",
            "BASE_DN": "ou=base",
            "PASSWORD": "whatever",
            "EMAIL_ATTR": "udsCanonicalAddress",
            "SEARCH_ATTR": "sn",
            "DISPLAY_ATTR": "udsDisplayName",
            "LASTNAME_ATTR": "sn",
            "FIRSTNAME_ATTR": "givenName",
            "ACCOUNTS_FILTER": "eduPersonPrimaryAffiliation=employee"
        }
        self.establishment3.save()

        data["structure"] = self.structure3.id
        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Course.objects.filter(label='Course test C').exists())

        course = Course.objects.get(label='Course test C')
        new_user = ImmersionUser.objects.get(email='new_user@domain.tld')
        self.assertIn(new_user, course.speakers.all())

        self.assertEqual(result, {
            'data': {
                'id': course.pk,
                'label': 'Course test C',
                'training': {
                    'id': training.id,
                    'label': 'test highschool training',
                    'training_subdomains': [{
                        'id': training.training_subdomains.first().pk,
                        'training_domain': {
                            "id": training.training_subdomains.first().training_domain.pk,
                            "label": training.training_subdomains.first().training_domain.label,
                            "active": training.training_subdomains.first().training_domain.active,
                        },
                        'label': 'test t_sub_domain',
                        'active': True
                    }],
                    'active': True,
                    'url': None,
                    'structures': [],
                    'highschool': training.highschool.id,
                    'allowed_immersions': None,
                },
                'structure': {
                    'id': self.structure3.id,
                    'code': 'STR3',
                    'label': 'test structure 3',
                    'mailing_list': None,
                    'active': True,
                    'establishment': self.structure3.establishment.id
                },
                'highschool': None,
                'published': True,
                'speakers': [{
                    'last_name': 'Dubois',
                    'first_name': 'Martine',
                    'email': 'new_user@domain.tld',
                    'establishment': self.structure3.establishment.id,
                    'id': new_user.pk,
                    'highschool': None,
                    'is_active': new_user.is_active,
                    'has_courses': new_user.courses.exists(),
                    'can_delete': not new_user.courses.exists()
                }],
                'url': 'http://test.com',
                'managed_by': 'ETA3 - STR3',
                'start_date': None,
                'end_date': None
            },
            'status': 'success',
            'msg': ''
        })

        # New course with an existing speaker
        self.assertFalse(Course.objects.filter(label='Course test D').exists())

        data = {
            "label": "Course test D",
            "published": True,
            "url": "http://test.com",
            "training": training.id,
            "structure": structure.id,
            "speakers": [],
            "emails": [self.speaker1.email]
        }
        response = self.api_client_token.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(Course.objects.filter(label='Course test D').exists())

        course = Course.objects.get(label='Course test D')
        self.assertIn(self.speaker1, course.speakers.all())

    def test_course_delete(self):
        self.client.login(username='ref_etab', password='pass')

        # Course doesn't exists
        data = { 'pk': 0 }
        response = self.client.delete(reverse("course_detail", kwargs=data))
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(content['error'], "A valid course must be selected")

        # With linked slots
        data = { 'pk': self.course.id }
        response = self.client.delete(reverse("course_detail", kwargs=data))
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(content['error'], "Slots are linked to this course, it can't be deleted")
        self.assertGreater(Slot.objects.filter(course=self.course).count(), 0)
        self.assertEqual(Course.objects.filter(id=self.course.id).count(), 1)

        # Without any slot
        self.slot.delete()
        self.slot2.delete()
        self.slot3.delete()
        self.full_slot.delete()
        self.past_slot.delete()
        self.unpublished_slot.delete()
        self.passed_registration_date_slot.delete()

        response = self.client.delete(reverse("course_detail", kwargs=data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Course successfully deleted")
        self.assertEqual(Slot.objects.filter(course=self.course).count(), 0)

        with self.assertRaises(Course.DoesNotExist):
            Course.objects.get(id=self.course.id)

    def test_mail_template_preview(self):
        self.client.login(username=self.ref_master_etab_user.username, password="pass")

        template = MailTemplate.objects.get(code="CPT_MIN_CREATE")

        data = {
            "user_group": "estetudiant",
            "slot_type": "estuncours",
            "local_account": True,
            "remote": False,
        }

        url = reverse("mail_template_preview", args=[template.id])

        # No body
        response = self.client.post(url, data)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "No body for this template provided")

        # with body
        data["body"] = template.body
        response = self.client.post(url, data)
        content = json.loads(response.content.decode("utf-8"))
        self.assertIn(
            "Connectez vous avec vos identifiants ENT de votre \u00e9tablissement d'origine.",
            content["data"]
        )

        # Template does not exist
        url = reverse("mail_template_preview", args=[9999])
        response = self.client.post(url, data)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Template #9999 can't be found")

    def test_sign_charter(self):
        establishment = self.ref_etab3_user.establishment
        establishment.signed_charter = False
        establishment.save()

        self.client.login(username=self.ref_etab3_user.username, password="pass")
        url = reverse("sign_charter")
        response = self.client.post(url, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['msg'], "Charter successfully signed")

        establishment.refresh_from_db()
        self.assertTrue(establishment.signed_charter)

    def test_ajax_update_structures_notifications(self):
        self.client.login(username=self.ref_str.username, password="pass")
        url = reverse("update_structures_notifications")
        response = self.client.post(url, **self.header)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Settings updated")

        response = self.client.post(url, { 'ids': []}, **self.header)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["msg"], "Settings updated")

        # FIXME: \O/
        # response = self.client.post(url, { 'ids': self.establishment.pk}, **self.header)
        # content = json.loads(response.content.decode("utf-8"))
        # self.assertEqual(content["msg"], "Settings updated")

    @patch('immersionlyceens.libs.api.accounts.rest.AccountAPI.search_user', side_effect=mocked_search_user)
    def test_rest_plugin(self, mocked_search_user):
        data_source_settings = {
            'HOST': 'https://localhost',
            'PATH': '/api/search',
            'PORT': '443',
            'HEADERS': {'Authorization': 'Token dummy'},
            'EMAIL_ATTR': 'email',
            'SEARCH_ATTR': 'last_name',
            'DISPLAY_ATTR': 'displayName',
            'LASTNAME_ATTR': 'last_name',
            'FIRSTNAME_ATTR': 'first_name'
        }

        establishment4 = Establishment.objects.create(
            code='ETA4',
            label='Etablissement 4',
            short_label='Eta 4',
            active=True,
            master=False,
            email='test4@test.com',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.get(pk='0660437S'),
            data_source_plugin="REST",
            data_source_settings=data_source_settings
        )

        # Only test class instantiation (should not raise exception)
        AccountAPI(establishment=establishment4)

        # TODO : test check_settings with missing or incorrect values

