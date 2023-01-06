"""
Django API tests suite
"""
import csv
import json
import unittest
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, pgettext
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Building, Calendar, Campus, CancelType, Course,
    CourseType, Establishment, GeneralSettings, HigherEducationInstitution,
    HighSchool, HighSchoolLevel, Immersion, ImmersionUser, MailTemplate,
    MailTemplateVars, OffOfferEvent, OffOfferEventType, PostBachelorLevel,
    Slot, Structure, StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UserCourseAlert, Vacation, Visit,
)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord, VisitorRecord,
)
from immersionlyceens.libs.utils import get_general_setting
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

request_factory = RequestFactory()
request = request_factory.get('/admin')


class APITestCase(TestCase):
    """Tests for API"""

    fixtures = [
        'group', 'group_permissions', 'generalsettings', 'high_school_levels', 'student_levels', 'post_bachelor_levels',
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
            data_source_plugin="LDAP",
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
            last_name="De Monmiraille",
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

        cls.ref_str.structures.add(cls.structure)
        cls.ref_str2.structures.add(cls.structure2)

        cls.cancel_type = CancelType.objects.create(label='Hello world')

        cls.calendar = Calendar.objects.create(
            label="Calendrier1",
            calendar_mode=Calendar.CALENDAR_MODE[0][0],
            year_start_date=cls.today - timedelta(days=10),
            year_end_date=cls.today + timedelta(days=10),
            year_nb_authorized_immersion=4,
            year_registration_start_date=cls.today - timedelta(days=9)
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

        cls.campus = Campus.objects.create(label='Esplanade')
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')

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
            date=self.today + timedelta(days=1),
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
            date=self.today + timedelta(days=2),
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
            date=self.today + timedelta(days=1),
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
        self.unpublished_slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 2',
            date=self.today + timedelta(days=1),
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
            date=self.today,
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="High school additional information",
            levels_restrictions=True
        )

        self.highschool_level_restricted_slot.allowed_highschool_levels.add(
            self.highschool_restricted_level
        )

        self.hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=2),
            class_name='1ere S 3',
            bachelor_type=3,
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
            allowed_global_registrations=2,
            allowed_first_semester_registrations=2,
            allowed_second_semester_registrations=2,
        )
        self.hs_record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school,
            birth_date=datetime.today(),
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=3),
            class_name='TS 3',
            bachelor_type=3,
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
            allowed_global_registrations=2,
            allowed_first_semester_registrations=0,
            allowed_second_semester_registrations=0,
        )
        self.student_record = StudentRecord.objects.create(
            student=self.student,
            uai_code='0673021V',  # Université de Strasbourg
            birth_date=datetime.today(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0],
            allowed_global_registrations=2,
            allowed_first_semester_registrations=0,
            allowed_second_semester_registrations=0,
        )
        self.student_record2 = StudentRecord.objects.create(
            student=self.student2,
            uai_code='0597065J',  # Université de Lille
            birth_date=datetime.today(),
            level=StudentLevel.objects.get(pk=1),
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0],
            allowed_global_registrations=2,
            allowed_first_semester_registrations=0,
            allowed_second_semester_registrations=0,
        )
        self.visitor_record = VisitorRecord.objects.create(
            visitor=self.visitor,
            birth_date=datetime.today(),
            allowed_first_semester_registrations=2,
            allowed_second_semester_registrations=2,
            allowed_global_registrations=4,
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

    def test_API_ajax_check_course_publication(self):
        self.client.login(username='ref_etab', password='pass')
        url = f"/api/check_course_publication/{self.course.id}"

        # True
        self.course.published = True
        self.course.save()
        content = json.loads(self.client.get(url, **self.header).content.decode())
        self.assertTrue(content['data']['published'])

        # False
        self.course.published = False
        self.course.save()
        content = json.loads(self.client.get(url, **self.header).content.decode())
        self.assertFalse(content['data']['published'])

        # 404
        url = "/api/check_course_publication/"
        response = self.client.get(url, {}, **self.header)
        self.assertEqual(response.status_code, 404)

    def test_API_ajax_get_course_speakers(self):
        self.client.login(username='ref_etab', password='pass')
        url = f"/api/get_course_speakers/{self.course.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], self.speaker1.id)
        self.assertEqual(content['data'][0]['first_name'], self.speaker1.first_name)
        self.assertEqual(content['data'][0]['last_name'], self.speaker1.last_name)

        # 404
        url = "/api/check_course_speakers/"
        response = self.client.post(url, {}, **self.header)
        self.assertEqual(response.status_code, 404)

    def test_API_ajax_get_buildings(self):
        self.client.login(username='ref_etab', password='pass')
        url = f"/api/get_buildings/{self.campus.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], self.building.id)
        self.assertEqual(content['data'][0]['label'], self.building.label)

    def test_API_ajax_get_courses_by_training(self):
        self.client.login(username='ref_etab', password='pass')

        # structure id & training
        url = f"/api/get_courses_by_training/{self.structure.id}/{self.training.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['key'], self.course.id)
        self.assertEqual(content['data'][0]['label'], self.course.label)
        self.assertEqual(content['data'][0]['url'], self.course.url)
        self.assertEqual(content['data'][0]['slots'], Slot.objects.filter(course__training=self.training).count())

    def test_API_get_ajax_slots(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/slots"
        data = {
            'training_id': self.training.id,
            'past': "true",
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 6)
        slot = content['data'][0]
        self.assertEqual(slot['id'], self.past_slot.id)
        self.assertEqual(slot['published'], self.past_slot.published)
        self.assertEqual(slot['course']['label'], self.past_slot.course.label)
        self.assertEqual(slot['structure']['code'], self.past_slot.course.structure.code)
        self.assertTrue(slot['structure']['managed_by_me'])
        self.assertEqual(slot['course_type'], self.past_slot.course_type.label)
        self.assertEqual(slot['date'], _date(self.today - timedelta(days=1), 'l d/m/Y'))
        self.assertEqual(slot['time']['start'], '12h00')
        self.assertEqual(slot['time']['end'], '14h00')
        self.assertEqual(slot['location']['campus'], self.past_slot.campus.label)
        self.assertEqual(slot['location']['building'], self.past_slot.building.label)
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
        self.assertEqual(len(content['data']), 6)

        # Logged as highschool manager
        client = Client()
        client.login(username='ref_lyc', password='pass')
        data = {'training_id': self.training.id}
        response = client.get(url, data, **self.header)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 6)


    def test_API_get_visits_slots(self):
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
        response = self.client.get(reverse('slots_list'), {'visits': 'true'}, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], slot.id)


    def test_API_get_events_slots(self):
        event = OffOfferEvent.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            event_type=self.event_type,
            label="Whatever",
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
        response = self.client.get(reverse('slots_list'), {'events': 'true'}, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], slot.id)



    def test_API_get_trainings(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/get_trainings"

        data = {
            'type': 'structure',
            'object_id': self.structure.id
        }

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 2)
        t1 = content['data'][0]
        self.assertEqual(t1['label'], self.training.label)
        self.assertEqual(t1['subdomain'], [s.label for s in self.training.training_subdomains.filter(active=True)])

        t2 = content['data'][1]
        self.assertEqual(t2['label'], self.training2.label)
        self.assertEqual(t2['subdomain'], [s.label for s in self.training2.training_subdomains.filter(active=True)])

        # No data : empty results
        data = {}
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])

        # No object id & bad type parameter
        data = {
            'type': 'badtype',
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Error : invalid parameter 'object_type' value")

        # Highschool type
        data = {
            'type': 'highschool',
            'object_id': self.high_school.id
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 1)
        t1 = content['data'][0]
        self.assertEqual(t1['label'], self.highschool_training.label)
        self.assertEqual(t1['subdomain'], [s.label for s in self.training.training_subdomains.filter(active=True)])

        # Bad object_id value
        data = {
            'type': 'highschool',
            'object_id': '',
        }

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Error : a valid structure or high school must be selected")



    def test_API_get_student_records(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/get_student_records/"

        # No action
        data = {}
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])
        self.assertEqual("Error: No action selected for AJAX request", content['msg'])

        # To validate - No student high school id
        data = {
            'action': 'TO_VALIDATE'
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Error: No high school selected")

        # To validate - With high school id
        self.hs_record.validation = 1  # to validate
        self.hs_record.save()
        data = {
            'action': 'TO_VALIDATE',
            'high_school_id': self.high_school.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 2)

        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)
        self.assertEqual(hs_record['first_name'], self.hs_record.student.first_name)
        self.assertEqual(hs_record['last_name'], self.hs_record.student.last_name)
        self.assertEqual(hs_record['level'], self.hs_record.level.label)
        self.assertEqual(hs_record['class_name'], self.hs_record.class_name)

        # Validated
        self.hs_record.validation = 2  # validate
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
        self.client.login(username='ref_etab', password='pass')
        url = "/api/validate_student/"

        data = {
            'student_record_id': self.hs_record.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 2)  # validated


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
        content = csv.reader(response.content.decode().split('\n'))

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
            _('registrant profile'),
            _('origin institution'),
            _('student level'),
            _('attendance status'),
        ]
        n = 0


        for row in content:
            # header check
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(str(self.establishment), row[0])
                self.assertEqual(self.structure.label, row[1])
                self.assertIn(self.t_domain.label, row[2].split('|'))
                self.assertIn(self.t_sub_domain.label, row[3].split('|'))
                self.assertEqual(self.training.label, row[4])
                self.assertEqual(self.course.label, row[5])
                self.assertEqual(self.course_type.label, row[6])
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[7])
                self.assertIn(self.slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.slot.end_time.strftime("%H:%M"), row[9])
                self.assertEqual(self.campus.label, row[10])
                self.assertEqual(self.building.label, row[11])
                self.assertEqual(self.slot.room, row[12])
                self.assertEqual(str(self.speaker1), row[13])
                self.assertEqual(str(self.slot.registered_students()), row[14])
                self.assertEqual(str(self.slot.n_places), row[15])
                self.assertEqual(self.slot.additional_information, row[16])
                self.assertEqual(_('High school student'), row[17])
                self.assertEqual(self.high_school.label, row[18])
                self.assertEqual(self.hs_record.level.label, row[19])
                self.assertEqual(self.immersion.get_attendance_status(), row[20])
            elif n == 2:
                self.assertEqual(
                    HigherEducationInstitution.objects.get(pk=self.student_record.uai_code).label,
                    row[18]
                )
                self.assertEqual(self.student_record.level.label, row[19])
            elif n == 5:  # high school slot
                self.assertEqual(f"{self.high_school.label} - {self.high_school.city}", row[0])
                self.assertEqual(self.highschool_training.label, row[4])
                self.assertEqual(self.highschool_course.label, row[5])
                self.assertIn(self.highschool_slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.highschool_slot.end_time.strftime("%H:%M"), row[9])
                self.assertEqual("", row[10])
                self.assertEqual("", row[11])
                self.assertEqual(self.highschool_slot.room, row[12])
                self.assertEqual(str(self.highschool_slot.registered_students()), row[14])
                self.assertEqual(self.highschool_slot.additional_information, row[16])

            n += 1


        # ref etab
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode().split('\n'))

        headers = [
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
            _('registrant profile'),
            _('origin institution'),
            _('student level'),
            _('attendance status'),
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
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[6])
                self.assertIn(self.slot.start_time.strftime("%H:%M"), row[7])
                self.assertIn(self.slot.end_time.strftime("%H:%M"), row[8])
                self.assertEqual(self.campus.label, row[9])
                self.assertEqual(self.building.label, row[10])
                self.assertEqual(self.slot.room, row[11])
                self.assertEqual(str(self.speaker1), row[12])
                self.assertEqual(str(self.slot.registered_students()), row[13])
                self.assertEqual(str(self.slot.n_places), row[14])
                self.assertEqual(self.slot.additional_information, row[15])
                self.assertEqual(_('High school student'), row[16])
                self.assertEqual(self.high_school.label, row[17])
                self.assertEqual(self.hs_record.level.label, row[18])
                self.assertEqual(self.immersion.get_attendance_status(), row[19])
            elif n == 2:
                self.assertEqual(
                    HigherEducationInstitution.objects.get(pk=self.student_record.uai_code).label,
                    row[17]
                )
                self.assertEqual(self.student_record.level.label, row[18])
            elif n == 5:  # high school slot
                self.assertEqual(self.structure.label, row[0])
                self.assertEqual(self.training.label, row[3])
                self.assertEqual(self.highschool_course.label, row[4])
                self.assertIn(self.slot2.start_time.strftime("%H:%M"), row[7])
                self.assertIn(self.slot2.end_time.strftime("%H:%M"), row[8])
                self.assertEqual(self.slot2.room, row[11])
                self.assertEqual(str(self.highschool_slot.registered_students()), row[13])
                self.assertEqual(self.slot2.additional_information, row[15])

            n += 1

        # # type=visit
        # url = '/api/get_csv_anonymous/?type=visit'
        # response = self.client.get(url, request)
        # content = csv.reader(response.content.decode().split('\n'))

        # headers = [
        #     _('establishment'),
        #     _('structure'),
        #     _('highschool'),
        #     _('purpose'),
        #     _('meeting place'),
        #     _('date'),
        #     _('start_time'),
        #     _('end_time'),
        #     _('speakers'),
        #     _('registration number'),
        #     _('place number'),
        #     _('additional information'),
        #     _('student level'),
        #     _('attendance status'),
        # ]
        # n = 0


        # for row in content:
        #     # header check
        #     if n == 0:
        #         for h in headers:
        #             self.assertIn(h, row)
        #     elif n == 1:
        #         self.assertEqual(str(self.establishment), row[0])
        #         self.assertEqual(self.structure.label, row[1])
        #         self.assertIn(self.highschool.label, row[2].split('|'))
        #         self.assertIn(self.t_sub_domain.label, row[3].split('|'))
        #         self.assertEqual(self.training.label, row[4])
        #         self.assertEqual(self.course.label, row[5])
        #         self.assertEqual(self.course_type.label, row[6])
        #         self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[7])
        #         self.assertIn(self.slot.start_time.strftime("%H:%M"), row[8])
        #         self.assertIn(self.slot.end_time.strftime("%H:%M"), row[9])
        #         self.assertEqual(self.campus.label, row[10])
        #         self.assertEqual(self.building.label, row[11])
        #         self.assertEqual(self.slot.room, row[12])
        #         self.assertEqual(str(self.speaker1), row[13])
        #         self.assertEqual(str(self.slot.registered_students()), row[14])
        #         self.assertEqual(str(self.slot.n_places), row[15])
        #         self.assertEqual(self.slot.additional_information, row[16])
        #         self.assertEqual(_('High school student'), row[17])
        #         self.assertEqual(self.high_school.label, row[18])
        #         self.assertEqual(self.hs_record.level.label, row[19])
        #         self.assertEqual(self.immersion.get_attendance_status(), row[20])
        #     elif n == 2:
        #         self.assertEqual(
        #             HigherEducationInstitution.objects.get(pk=self.student_record.uai_code).label,
        #             row[18]
        #         )
        #         self.assertEqual(self.student_record.level.label, row[19])
        #     elif n == 5:  # high school slot
        #         self.assertEqual(f"{self.high_school.label} - {self.high_school.city}", row[0])
        #         self.assertEqual(self.highschool_training.label, row[4])
        #         self.assertEqual(self.highschool_course.label, row[5])
        #         self.assertIn(self.highschool_slot.start_time.strftime("%H:%M"), row[8])
        #         self.assertIn(self.highschool_slot.end_time.strftime("%H:%M"), row[9])
        #         self.assertEqual("", row[10])
        #         self.assertEqual("", row[11])
        #         self.assertEqual(self.highschool_slot.room, row[12])
        #         self.assertEqual(str(self.highschool_slot.registered_students()), row[14])
        #         self.assertEqual(self.highschool_slot.additional_information, row[16])

        #     n += 1


    def test_API_get_csv_highschool(self):
        # Ref highschool
        self.client.login(username='ref_lyc', password='pass')
        url = '/api/get_csv_highschool/'
        response = self.client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))
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
            _('course/event/visit label'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('meeting place'),
            _('attendance status'),
        ]

        n = 0
        for row in content:
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(self.hs_record.student.last_name, row[0])
                self.assertEqual(self.hs_record.student.first_name, row[1])
                self.assertEqual(_date(self.hs_record.birth_date, 'd/m/Y'), row[2])
                self.assertEqual(self.hs_record.level.label, row[3])
                self.assertEqual(self.hs_record.class_name, row[4])
                self.assertEqual(HighSchoolStudentRecord.BACHELOR_TYPES[self.hs_record.bachelor_type - 1][1], row[5])
                self.assertIn('', row[6])
                self.assertIn('', row[7])
                self.assertIn(self.t_domain.label, row[8].split('|'))
                self.assertIn(self.t_sub_domain.label, row[9].split('|'))
                self.assertIn(self.training.label, row[10])
                self.assertIn(self.course.label, row[11])
                self.assertIn('', row[12])
                self.assertIn('', row[13])
                self.assertIn('', row[14])

            n += 1


    def test_API_get_csv_structures(self):
        # No type specified
        url = '/api/get_csv_structures/'
        response = self.client.get(url, request)
        self.assertEqual(response.status_code, 404)

        url = '/api/get_csv_structures/?type=course'
        # Ref structure
        self.client.login(username='ref_str', password='pass')
        response = self.client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))
        headers = [
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
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertIn(str(self.structure), row[0].split('|'))
                self.assertIn(self.t_domain.label, row[1].split('|'))
                self.assertIn(self.t_sub_domain.label, row[2].split('|'))
                self.assertIn(self.training.label, row[3])
                self.assertIn(self.course.label, row[4])
                self.assertIn(self.course_type.label, row[5])
                self.assertIn(_date(self.today - timedelta(days=1), 'd/m/Y'), row[6])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[7])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[8])
                self.assertIn(self.past_slot.campus.label, row[9])
                self.assertIn(self.past_slot.building.label, row[10])
                self.assertEqual(self.past_slot.room, row[11])
                self.assertIn(
                    f'{self.speaker1.first_name} {self.speaker1.last_name}',
                    row[12].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[13])
                self.assertEqual(str(self.past_slot.n_places), row[14])
                self.assertEqual(self.past_slot.additional_information, row[15])

            n += 1

        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode().split('\n'))
        headers = [
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
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(str(self.structure), row[0])
                self.assertIn(self.t_domain.label, row[1].split('|'))
                self.assertIn(self.t_sub_domain.label, row[2].split('|'))
                self.assertIn(self.training.label, row[3])
                self.assertIn(self.course.label, row[4])
                self.assertIn(self.course_type.label, row[5])
                self.assertIn(_date(self.today - timedelta(days=1), 'd/m/Y'), row[6])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[7])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[8])
                self.assertIn(self.past_slot.campus.label, row[9])
                self.assertIn(self.past_slot.building.label, row[10])
                self.assertEqual(self.past_slot.room, row[11])
                self.assertIn(
                    f'{self.speaker1.first_name} {self.speaker1.last_name}',
                    row[12].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[13])
                self.assertEqual(str(self.past_slot.n_places), row[14])
                self.assertEqual(self.past_slot.additional_information, row[15])

            n += 1

        self.client.login(username='ref_master_etab', password='pass')
        response = self.client.get(url, request)
        content = csv.reader(response.content.decode().split('\n'))
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
            if n == 0:
                for h in headers:
                    self.assertIn(h, row)
            elif n == 1:
                self.assertEqual(str(self.establishment), row[0])
                self.assertEqual(str(self.structure), row[1])
                self.assertIn(self.t_domain.label, row[2].split('|'))
                self.assertIn(self.t_sub_domain.label, row[3].split('|'))
                self.assertIn(self.training.label, row[4])
                self.assertIn(self.course.label, row[5])
                self.assertIn(self.course_type.label, row[6])
                self.assertIn(_date(self.today - timedelta(days=1), 'd/m/Y'), row[7])
                self.assertIn(self.past_slot.start_time.strftime("%H:%M"), row[8])
                self.assertIn(self.past_slot.end_time.strftime("%H:%M"), row[9])
                self.assertIn(self.past_slot.campus.label, row[10])
                self.assertIn(self.past_slot.building.label, row[11])
                self.assertEqual(self.past_slot.room, row[12])
                self.assertIn(
                    f'{self.speaker1.first_name} {self.speaker1.last_name}',
                    row[13].split('|')
                ),
                self.assertEqual(str(self.past_slot.registered_students()), row[14])
                self.assertEqual(str(self.past_slot.n_places), row[15])
                self.assertEqual(self.past_slot.additional_information, row[16])

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

        # local plugin
        data = {
            'username': 'ref_etab3',
            'establishment_id': self.establishment3.id
        }
        self.client.login(username='ref_etab3', password='pass')
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Error : Please check establishment LDAP plugin settings : LDAP plugin settings are empty")
        self.assertEqual(content['data'], [])


    def test_API_get_courses(self):
        self.client.login(username='ref_etab', password='pass')
        request.user = self.ref_etab_user

        url = f"/api/get_courses/?structure={self.structure.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 1)
        c = content['data'][0]
        self.assertEqual(c['id'], self.course.id)
        self.assertEqual(c['published'], self.course.published)
        self.assertEqual(c['training_label'], self.course.training.label)
        self.assertEqual(c['label'], self.course.label)
        self.assertEqual(c['structure_code'], self.course.structure.code)
        self.assertEqual(c['structure_id'], self.course.structure.id)

        speakers = [{
            'name': f'{t.last_name} {t.first_name}',
            'email': t.email
        } for t in self.course.speakers.all()]

        for speaker in c['speakers']:
            self.assertIn(speaker, speakers)

        self.assertEqual(c['slots_count'], self.course.slots_count())
        self.assertEqual(c['n_places'], self.course.free_seats())
        self.assertEqual(c['published_slots_count'], self.course.published_slots_count())
        self.assertEqual(c['registered_students_count'], self.course.registrations_count())
        self.assertEqual(c['alerts_count'], self.course.get_alerts_count())
        self.assertEqual(c['can_delete'], not self.course.slots.exists())

        url = "/api/get_courses/"
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], 'Error : a valid structure or high school must be selected')


    def test_API_ajax_delete_course(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/delete_course"

        # No data
        data = {}
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['error'], "Error : a valid course must be selected")
        self.assertEqual(content['msg'], '')

        # Course doesn't exists
        data = {
            'course_id': 0
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['error'], "Error : a valid course must be selected")
        self.assertEqual(content['msg'], '')

        # With linked slots
        data = {
            'course_id': self.course.id
        }

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['error'], "Error : slots are linked to this course")
        self.assertEqual(content['msg'], '')
        self.assertGreater(Slot.objects.filter(course=self.course).count(), 0)
        self.assertEqual(Course.objects.filter(id=self.course.id).count(), 1)

        # Without any slot
        self.slot.delete()
        self.slot2.delete()
        self.slot3.delete()
        self.full_slot.delete()
        self.past_slot.delete()
        self.unpublished_slot.delete()

        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['error']), 0)
        self.assertGreater(len(content['msg']), 0)
        self.assertEqual(content['msg'], "Course successfully deleted")
        self.assertEqual(Slot.objects.filter(course=self.course).count(), 0)

        with self.assertRaises(Course.DoesNotExist):
            Course.objects.get(id=self.course.id)


    def test_API_ajax_get_speaker_courses(self):
        # As a 'structure' speaker
        request.user = self.speaker1
        client = Client()
        client.login(username='speaker1', password='pass')

        url = "/api/get_courses/"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        c = content['data'][0]
        self.assertEqual(self.course.id, c['id'])
        self.assertEqual(self.course.published, c['published'])
        self.assertEqual(
            f"{self.course.structure.establishment.code} - {self.course.structure.code}",
            c['managed_by']
        )
        self.assertEqual(self.course.training.label, c['training_label'])
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

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        c = content['data'][0]
        self.assertEqual(self.highschool_course.id, c['id'])
        self.assertEqual(self.highschool_course.published, c['published'])
        self.assertEqual(f"{self.high_school.city} - {self.high_school.label}", c['managed_by'])
        self.assertEqual(self.highschool_course.training.label, c['training_label'])
        self.assertEqual(self.highschool_course.label, c['label'])
        # speakers
        self.assertEqual(self.highschool_course.slots_count(speakers=self.highschool_speaker.id), c['slots_count'])
        self.assertEqual(self.highschool_course.free_seats(speakers=self.highschool_speaker.id), c['n_places'])
        self.assertEqual(
            self.highschool_course.published_slots_count(speakers=self.highschool_speaker.id),
            c['published_slots_count']
        )

    def test_API_get_my_slots(self):
        client = Client()
        url = f"/api/slots?visits=false"
        # as a high school speaker
        client.login(username='highschool_speaker', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.highschool_slot.id, s['id'])
        self.assertEqual(self.highschool_slot.published, s['published'])
        self.assertEqual(self.high_school.city, s['highschool']['city'])
        self.assertEqual(self.high_school.label, s['highschool']['label'])
        self.assertEqual(
            f'{self.highschool_slot.course.training.label} ({self.highschool_slot.course_type.label})',
            s['training_label']
        )
        self.assertEqual(
            f'{self.highschool_slot.course.training.label} ({self.highschool_slot.course_type.full_label})',
            s['training_label_full']
        )
        self.assertEqual("", s['location']['campus'])
        self.assertEqual(self.highschool_slot.room, s['room'])

        self.assertEqual(_date(self.highschool_slot.date, 'l d/m/Y'), s['date'])
        self.assertEqual(self.highschool_slot.start_time.strftime("%Hh%M"), s['time']['start'])
        self.assertEqual(self.highschool_slot.end_time.strftime("%Hh%M"), s['time']['end'])

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
        self.assertEqual(self.past_slot.course.structure.code, s['structure']['code'])
        self.assertEqual(
            f'{self.past_slot.course.training.label} ({self.past_slot.course_type.label})',
            s['training_label']
        )
        self.assertEqual(
            f'{self.past_slot.course.training.label} ({self.past_slot.course_type.full_label})',
            s['training_label_full']
        )
        self.assertEqual(self.past_slot.campus.label, s['location']['campus'])
        self.assertEqual(self.past_slot.building.label, s['location']['building'])

        self.assertEqual(self.past_slot.room, s['room'])

        self.assertEqual(_date(self.past_slot.date, 'l d/m/Y'), s['date'])
        self.assertEqual(self.past_slot.start_time.strftime("%Hh%M"), s['time']['start'])
        self.assertEqual(self.past_slot.end_time.strftime("%Hh%M"), s['time']['end'])

        self.assertEqual(self.past_slot.course.label, s['course']['label'])
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


    def test_API_ajax_get_agreed_highschools(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        url = "/api/get_agreed_highschools"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        hs = content['data'][0][0]
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
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['course']['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course']['label'])
        self.assertEqual(self.immersion.slot.course_type.label, i['course']['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['course']['type_full'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['room'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%-Hh%M"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%-Hh%M"), i['end_time'])
        self.assertEqual(self.immersion.slot.additional_information, i['info'])
        self.assertEqual(self.immersion.get_attendance_status_display(), i['attendance'])
        self.assertEqual(self.immersion.attendance_status, i['attendance_status'])
        self.assertEqual(self.today.date() < self.immersion.slot.date.date(), i['cancellable'])
        self.assertEqual(self.immersion.slot.id, i['slot_id'])

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
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['room'])
        self.assertEqual(self.immersion.slot.start_time.strftime("%-Hh%M"), i['start_time'])
        self.assertEqual(self.immersion.slot.end_time.strftime("%-Hh%M"), i['end_time'])
        self.assertEqual(self.immersion.slot.additional_information, i['info'])
        self.assertEqual(self.immersion.get_attendance_status_display(), i['attendance'])
        self.assertEqual(self.immersion.attendance_status, i['attendance_status'])
        self.assertEqual(self.today.date() < self.immersion.slot.date.date(), i['cancellable'])
        self.assertEqual(self.immersion.slot.id, i['slot_id'])


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
        self.assertEqual(self.highschool_user2.id, hs['id'])
        self.assertEqual(self.highschool_user2.first_name, hs['firstname'])
        self.assertEqual(self.highschool_user2.last_name, hs['lastname'])
        self.assertEqual(pgettext('person type', 'High school student'), hs['profile'])
        self.assertEqual(self.hs_record2.highschool.label, hs['school'])
        self.assertEqual('Terminale', hs['level'])
        self.assertEqual(self.hs_record2.highschool.city, hs['city'])
        self.assertEqual(self.hs_record2.class_name, hs['class'])
        self.assertEqual(True, hs['can_register'])
        self.assertEqual([], hs['reasons'])

        # Student
        self.assertEqual(self.student2.id, stu['id'])
        self.assertEqual(self.student2.first_name, stu['firstname'])
        self.assertEqual(self.student2.last_name, stu['lastname'])
        self.assertEqual(pgettext('person type', 'Student'), stu['profile'])
        self.assertEqual(
            HigherEducationInstitution.objects.get(pk=self.student_record2.uai_code).label,
            stu['school']
        )

        self.assertEqual('Licence 1', stu['level'])
        self.assertEqual('', stu['city'])
        self.assertEqual('', stu['class'])
        self.assertEqual(True, stu['can_register'])
        self.assertEqual([], stu['reasons'])

        # Unknown slot
        url = f"/api/get_available_students/99999"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], 'Error : slot not found')


    def test_API_ajax_get_available_students_with_restrictions(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        self.hs_record.validation = 2
        self.hs_record.save()
        self.hs_record2.validation = 2
        self.hs_record2.save()

        # Add a highschool restriction on self.slot
        self.slot.establishments_restrictions = True
        self.slot.allowed_highschools.add(self.high_school)
        self.slot.levels_restrictions = True
        h_levels = HighSchoolLevel.objects.all()
        s_levels = StudentLevel.objects.all()
        p_levels = PostBachelorLevel.objects.all()
        self.slot.allowed_highschool_levels.add(*h_levels)
        self.slot.allowed_student_levels.add(*s_levels)
        self.slot.allowed_post_bachelor_levels.add(*p_levels)
        self.slot.save()

        url = f"/api/get_available_students/{self.slot.id}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 2)

        # Careful with the results order (last_name, first_name)
        hs = content['data'][0]
        stu = content['data'][1]

        # =========================
        # As a ref_etab_user, both students will be there, but with a reason for the university student
        # =========================

        # High school student
        self.assertEqual(self.highschool_user2.id, hs['id'])
        self.assertEqual(True, hs['can_register'])
        self.assertEqual([], hs['reasons'])

        # Student
        self.assertEqual(self.student2.id, stu['id'])
        self.assertEqual(False, stu['can_register'])
        self.assertEqual(['Establishments restrictions in effect'], stu['reasons'])

        # =========================
        # As a structure referent, the university student won't be there
        # =========================
        request.user = self.ref_str
        self.client.login(username='ref_str', password='pass')

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 1)
        hs = content['data'][0]
        self.assertEqual(self.highschool_user2.id, hs['id'])
        self.assertEqual(True, hs['can_register'])
        self.assertEqual([], hs['reasons'])


    def test_API_ajax_get_highschool_students(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        # No records
        url = "/api/get_highschool_students/no_record"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 1)
        h = content['data'][0]
        self.assertEqual(self.highschool_user3.id, h['id'])
        self.assertEqual(
            f'{self.highschool_user3.last_name} {self.highschool_user3.first_name}',
            h['name']
        )
        fields = ('birthdate', 'level')
        empty_fields = ('institution', 'bachelor', 'post_bachelor_level', 'class')
        for field in fields:
            self.assertEqual('-', h[field])
        for field in empty_fields:
            self.assertEqual('', h[field])

        # As a high school manager
        url = "/api/get_highschool_students/"
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
        self.hs_record.origin_bachelor_type = 1
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
                    f"{self.hs_record.level} - {self.hs_record.post_bachelor_level.label}",
                    h['post_bachelor_level']
                )
                self.assertEqual(self.hs_record.get_origin_bachelor_type_display(), h['bachelor'])
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


    def test_API_ajax_check_date_between_vacation(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')

        # No date
        url = f"/api/check_vacations"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error: A date is required")
        self.assertEqual(content['data'], {})

        # Bad date format
        url = f"/api/check_vacations?date=failure"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error: bad date format")
        self.assertEqual(content['data'], {})

        # dmY format
        url = f"/api/check_vacations?date=01/01/2010"

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
        url = f"/api/check_vacations?date={dd}"

        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIn('is_between', content['data'])
        self.assertIsInstance(content['data']['is_between'], bool)
        self.assertEqual(content['data']['is_between'], True)


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

        # Authenticated user has no rights
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

        # Success
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Immersion cancelled")

        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.cancellation_type.id, self.cancel_type.id)


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

        url = "/api/get_alerts"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        a = content['data'][0]
        self.assertEqual(self.alert.id, a['id'])
        self.assertEqual(self.alert.course.label, a['course'])
        self.assertEqual(self.alert.course.training.label, a['training'])
        self.assertEqual([s.label for s in self.alert.course.training.training_subdomains.all()], a['subdomains'])
        self.assertEqual(
            [s.training_domain.label for s in self.alert.course.training.training_subdomains.all()],
            a['domains'])
        self.assertEqual(self.alert.email_sent, a['email_sent'])


    def test_API_ajax_send_email(self):
        request.user = self.ref_etab_user
        self.client.login(username='ref_etab', password='pass')
        url = "/api/send_email"

        # No data
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid parameters")

        # Success
        data = {
            'slot_id': self.slot.id,
            'send_copy': 'true',
            'subject': 'hello',
            'body': 'Hello world'
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

        # Invalid json parameters
        data = {
            'immersion_ids': 'hello world',
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertTrue(content['error'])
        self.assertEqual(content['msg'], "Invalid json decoding")

        # Past immersions
        self.slot.date = self.today - timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_ids': f'[{self.immersion.id}]',
            'reason_id': self.cancel_type.id
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
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_ids': json.dumps([self.immersion.id]),
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        # The following test may fail if template syntax has errors
        self.assertEqual("Immersion(s) cancelled", content['msg'])
        self.assertIsNone(content['err_msg'])



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
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        if self.immersion.student.is_visitor():
            student_profile = _('Visitor')
        elif self.immersion.student.is_high_school_student():
            student_profile = _('High school student')
        else:
            student_profile = _('Student')

        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(_date(self.immersion.slot.date, 'l d/m/Y'), i['date'])
        self.assertEqual(self.immersion.slot.start_time.strftime('%Hh%M'), i['time']['start'])
        self.assertEqual(self.immersion.slot.end_time.strftime('%Hh%M'), i['time']['end'])
        self.assertEqual(f'{self.highschool_user.last_name} {self.highschool_user.first_name}', i['name'])
        self.assertEqual(self.hs_record.highschool.label, i['institution'])
        self.assertEqual(self.hs_record.phone, i['phone'])
        self.assertEqual(self.highschool_user.email, i['email'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['meeting_place'])
        self.assertEqual(student_profile, i['student_profile'])


        url2 = f'/api/get_students_presence/{self.today.date()- timedelta(days=90)}/{self.today.date()}'
        content = json.loads(self.client.post(url2, data, **self.header).content.decode())
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(_date(self.immersion.slot.date, 'l d/m/Y'), i['date'])
        self.assertEqual(self.immersion.slot.start_time.strftime('%Hh%M'), i['time']['start'])
        self.assertEqual(self.immersion.slot.end_time.strftime('%Hh%M'), i['time']['end'])
        self.assertEqual(f'{self.highschool_user.last_name} {self.highschool_user.first_name}', i['name'])
        self.assertEqual(self.hs_record.highschool.label, i['institution'])
        self.assertEqual(self.hs_record.phone, i['phone'])
        self.assertEqual(self.highschool_user.email, i['email'])
        self.assertEqual(self.immersion.slot.campus.label, i['campus'])
        self.assertEqual(self.immersion.slot.building.label, i['building'])
        self.assertEqual(self.immersion.slot.room, i['meeting_place'])
        self.assertEqual(student_profile, i['student_profile'])

        # ref_lyc
        request.user = self.ref_lyc
        self.client.login(username='ref_lyc', password='pass')
        url = "/api/get_students_presence"

        # No data
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertEqual(content['msg'], "")


    def test_API_ajax_get_trainings(self):
        self.client.login(username='ref_etab', password='pass')
        url = "/api/get_trainings"

        # No data
        data = {}
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Error : invalid parameter 'object_type' value")

        # No object_id value
        data = {
            'type': 'structure'
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Error : a valid structure or high school must be selected")



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

        self.immersion3.delete()

        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {'semester1': 2, 'semester2': 2, 'annually': 1}
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
            {'semester1': 2, 'semester2': 2, 'annually': 0}
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
        self.assertEqual("""You have no more remaining registration available, """
                         """you should cancel an immersion or contact immersion service""", content['msg'])

        # As a structure manager
        client.login(username=self.ref_str.username, password='pass')
        data['slot_id'] = self.slot2.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("This student has no more remaining slots to register to", content['msg'])

        # reset immersions
        client.login(username=self.highschool_user.username, password='pass')

        Immersion.objects.filter(student=self.highschool_user).delete()

        # Fail with past slot registration
        data['slot_id'] = self.past_slot.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Register to past slot is not available", content['msg'])

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
        response = client.post("/api/register",
                               {'slot_id': self.highschool_level_restricted_slot.id},
                               **self.header,
                               follow=True
                               )
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Cannot register slot due to slot's restrictions", content['msg'])

        # Todo : needs more tests with other users (ref-etab, ref-str, ...)


    def test_ajax_slot_registration_semester_mode(self):
        self.hs_record.validation = 2
        self.hs_record.save()

        # Recreate a calendar in semester mode
        Calendar.objects.all().delete()

        calendar = Calendar.objects.create(
            label="Calendrier2",
            calendar_mode=Calendar.CALENDAR_MODE[1][0],
            semester1_start_date=self.today - timedelta(days=10),
            semester1_end_date=self.today + timedelta(days=10),
            semester1_registration_start_date=self.today - timedelta(days=9),
            semester2_start_date=self.today + timedelta(days=11),
            semester2_end_date=self.today + timedelta(days=31),
            semester2_registration_start_date=self.today + timedelta(days=11),
            nb_authorized_immersion_per_semester=3,
        )

        self.hs_record.allowed_first_semester_registrations = 3
        self.hs_record.allowed_second_semester_registrations = 3
        self.hs_record.save()

        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {'semester1': 1, 'semester2': 3, 'annually': 2}
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
        self.assertEqual("Registration successfully added, confirmation email sent", content['msg'])
        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {'semester1': 0, 'semester2': 3, 'annually': 2}
        )
        self.assertTrue(Immersion.objects.filter(student=self.highschool_user, slot=self.slot3).exists())

        # Fail : no more registration allowed
        data['slot_id'] = self.slot2.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("""You have no more remaining registration available, """
                         """you should cancel an immersion or contact immersion service""", content['msg'])

        # As a structure manager
        client.login(username=self.ref_str.username, password='pass')
        data['slot_id'] = self.slot2.id
        response = client.post("/api/register", data, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("This student has no more remaining slots to register to", content['msg'])

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


    def test_campus(self):
        campus = Campus.objects.create(label='Campus', establishment=self.establishment, active=True)

        client = Client()
        client.login(username='ref_etab', password='pass')

        response = client.get(reverse("campus_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content[0]['label'], campus.label)


    def test_high_school_speakers(self):
        client = Client()

        # Success
        client.login(username='ref_lyc', password='pass')
        response = client.get(
            reverse("get_highschool_speakers", kwargs={'highschool_id': self.high_school.id}),
            **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['data'], [{
            'id': self.highschool_speaker.id,
            'last_name': 'highschool_speaker',
            'first_name': 'highschool_speaker',
            'email': 'highschool_speaker@no-reply.com',
            'is_active': 'Yes',
            'has_courses': 'Yes',
            'can_delete': False
        }])


    def test_visit(self):
        visit = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever",
            published=True
        )

        visit2 = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever 2",
            published=True
        )

        client = Client()
        client.login(username='ref_etab', password='pass')

        # List
        response = client.get(reverse("visit_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual(content[0]['purpose'], 'Whatever')
        self.assertEqual(content[0]['establishment']['code'], "ETA1")
        self.assertEqual(content[0]['establishment']['label'], "Etablissement 1")

        # As ref-str (with no structure) : empty
        self.ref_str.structures.remove(self.structure)
        client.login(username='ref_str', password='pass')
        response = client.get(reverse("visit_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(content), 0)

        # Deletion
        # as ref_str : fail (bad structure)
        response = client.delete(reverse("visit_detail", kwargs={'pk': visit.id}))
        self.assertIn("Insufficient privileges", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Visit.objects.count(), 2)

        # as ref_etab
        client.login(username='ref_etab', password='pass')
        response = client.delete(reverse("visit_detail", kwargs={'pk': visit.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Visit.objects.count(), 1)

        # as master_ref_etab
        client.login(username='ref_master_etab', password='pass')
        response = client.delete(reverse("visit_detail", kwargs={'pk': visit2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Visit.objects.count(), 0)

        # as operator
        visit2 = Visit.objects.create(
            establishment=self.establishment,
            structure=self.structure,
            highschool=self.high_school,
            purpose="Whatever 2",
            published=True
        )

        client.login(username='operator', password='pass')
        response = client.delete(reverse("visit_detail", kwargs={'pk': visit2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Visit.objects.count(), 0)


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
        self.assertIsInstance(content["msg"], str)
        self.assertGreater(len(content["msg"]), 0)

    def test_API__get_visitor_records__to_validate(self):
        url = "/api/visitor/records/to_validate"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertIsInstance(content["msg"], str)
        self.assertEqual(len(content["msg"]), 0)

        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], dict)
        for field_name in ("id", "first_name", "last_name", "birth_date"):
            self.assertIn(field_name, data[0])

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%d/%m/%Y"))

    def test_API__get_visitor_records__validated(self):
        self.visitor_record.validation = 2
        self.visitor_record.save()
        url = "/api/visitor/records/validated"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertIsInstance(content["msg"], str)
        self.assertEqual(len(content["msg"]), 0)

        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], dict)
        for field_name in ("id", "first_name", "last_name", "birth_date"):
            self.assertIn(field_name, data[0])

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%d/%m/%Y"))

    def test_API__get_visitor_records__rejected(self):
        self.visitor_record.validation = 3
        self.visitor_record.save()
        url = "/api/visitor/records/rejected"
        response = self.client.get(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("data", content)
        self.assertIn("msg", content)

        self.assertIsInstance(content["msg"], str)
        self.assertEqual(len(content["msg"]), 0)

        self.assertIsInstance(content["data"], list)
        data = content["data"]
        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], dict)
        for field_name in ("id", "first_name", "last_name", "birth_date"):
            self.assertIn(field_name, data[0])

        self.assertEqual(data[0]["id"], self.visitor_record.id)
        self.assertEqual(data[0]["first_name"], self.visitor.first_name)
        self.assertEqual(data[0]["last_name"], self.visitor.last_name)
        self.assertEqual(data[0]["birth_date"], self.visitor_record.birth_date.strftime("%d/%m/%Y"))

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
        self.assertGreater(len(content["msg"]), 0)

        # no change
        record = VisitorRecord.objects.get(id=self.visitor_record.id)
        self.assertEqual(record.validation, self.visitor_record.validation)

    def test_API_visitor_record_operation__validate(self):
        client = Client()
        client.login(username='ref_master_etab', password='pass')
        url = f"/api/visitor/record/{self.visitor_record.id}/validate"
        response = client.post(url)
        content = json.loads(response.content.decode("utf-8"))

        self.assertIsInstance(content, dict)
        self.assertIn("msg", content)
        self.assertIn("data", content)
        self.assertIsInstance(content["data"], dict)
        self.assertEqual(len(content["msg"]), 0)

        self.assertIn("record_id", content["data"])
        self.assertEqual(content["data"]["record_id"], self.visitor_record.id)

        # value changed
        record = VisitorRecord.objects.get(id=self.visitor_record.id)
        self.assertEqual(record.validation, 2)

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
        self.assertEqual(len(content["msg"]), 0)

        self.assertIn("record_id", content["data"])
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

        # Add view permission an try again
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

        # Add view permission an try again
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


    def test_training_subdomain_list(self):
        view_permission = Permission.objects.get(codename='view_trainingsubdomain')
        add_permission = Permission.objects.get(codename='add_trainingsubdomain')
        url = reverse("training_subdomain_list")

        # List
        self.assertTrue(TrainingSubdomain.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission an try again
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
        view_permission = Permission.objects.get(codename='view_training')
        add_permission = Permission.objects.get(codename='add_training')
        url = reverse("training_list")
        # List
        self.assertTrue(Training.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission an try again
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))
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
        self.assertEqual(result['error'], {'training_subdomains': ['This list may not be empty.']})

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
        view_permission = Permission.objects.get(codename='view_course')
        add_permission = Permission.objects.get(codename='add_course')
        url = reverse("course_list")

        # List
        self.assertTrue(Course.objects.exists())

        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['error'], 'You do not have permission to perform this action.')

        # Add view permission an try again
        self.api_user.user_permissions.add(view_permission)
        response = self.api_client_token.get(url)
        result = json.loads(response.content.decode('utf-8'))

        # Make sure all training domains are there
        for course in Course.objects.all():
            self.assertTrue(course.id in [c['id'] for c in result])

        # Creation (POST)
        structure = Structure.objects.first()
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
        self.assertEqual(result.get('label'), "Course test")
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