"""
Django API tests suite
"""
import csv
import json
import unittest
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils.translation import pgettext
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from immersionlyceens.apps.core.models import (AccompanyingDocument, Building, Calendar, Campus, CancelType,
    Structure, Course, CourseType, Establishment, GeneralSettings, HighSchool, Immersion, ImmersionUser, MailTemplate,
    MailTemplateVars, Slot, Training, TrainingDomain, TrainingSubdomain, UserCourseAlert, Vacation, Visit,
    OffOfferEvent, OffOfferEventType
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.libs.api.views import ajax_check_course_publication
from immersionlyceens.libs.utils import get_general_setting

request_factory = RequestFactory()
request = request_factory.get('/admin')


class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group', 'generalsettings']

    def setUp(self):
        """
        GeneralSettings.objects.create(
            setting='MAIL_CONTACT_REF_ETAB',
            value='unittest@unittest.fr',
            description='REF-ETAB email'
        )
        """
        self.today = datetime.today()
        self.header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        
        # TODO : put all these objects in test fixtures

        self.establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test@test.com'
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
            convention_start_date=self.today - timedelta(days=10),
            convention_end_date=self.today + timedelta(days=10),
            postbac_immersion=True
        )

        self.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='ref_etab@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=self.establishment
        )
        self.ref_etab_user.set_password('pass')
        self.ref_etab_user.save()

        self.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='ref_master_etab@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=self.establishment
        )
        self.ref_master_etab_user.set_password('pass')
        self.ref_master_etab_user.save()

        self.highschool_user = get_user_model().objects.create_user(
            username='@EXTERNAL@_hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )
        self.highschool_user.set_password('pass')
        self.highschool_user.save()

        self.highschool_user2 = get_user_model().objects.create_user(
            username='@EXTERNAL@_hs2',
            password='pass',
            email='hs2@no-reply.com',
            first_name='high2',
            last_name='SCHOOL2',
        )
        self.highschool_user2.set_password('pass')
        self.highschool_user2.save()

        self.highschool_user3 = get_user_model().objects.create_user(
            username='@EXTERNAL@_hs3', password='pass',
            email='hs3@no-reply.com',
            first_name='high3',
            last_name='SCHOOL3',
        )
        self.highschool_user3.set_password('pass')
        self.highschool_user3.save()

        self.ref_str = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
        )
        self.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
        )
        self.highschool_speaker = get_user_model().objects.create_user(
            username='highschool_speaker',
            password='pass',
            email='highschool_speaker@no-reply.com',
            first_name='highschool_speaker',
            last_name='highschool_speaker',
            highschool=self.high_school
        )
        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='lycref-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
            highschool=self.high_school
        )
        self.student = get_user_model().objects.create_user(
            username='student',
            password='pass',
            email='student@no-reply.com',
            first_name='student',
            last_name='STUDENT',
        )
        self.student2 = get_user_model().objects.create_user(
            username='student2',
            password='pass',
            email='student2@no-reply.com',
            first_name='student2',
            last_name='STUDENT2',
        )
        self.cancel_type = CancelType.objects.create(label='Hello world')
        self.client = Client()
        self.client.login(username='ref_etab', password='pass')

        Group.objects.get(name='REF-ETAB').user_set.add(self.ref_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(self.ref_master_etab_user)
        Group.objects.get(name='INTER').user_set.add(self.speaker1)
        Group.objects.get(name='INTER').user_set.add(self.highschool_speaker)
        Group.objects.get(name='REF-STR').user_set.add(self.ref_str)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user2)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user3)
        Group.objects.get(name='ETU').user_set.add(self.student)
        Group.objects.get(name='ETU').user_set.add(self.student2)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

        self.calendar = Calendar.objects.create(
            label="Calendrier1",
            calendar_mode=Calendar.CALENDAR_MODE[0][0],
            year_start_date=self.today - timedelta(days=10),
            year_end_date=self.today + timedelta(days=10),
            year_nb_authorized_immersion=4,
            year_registration_start_date=self.today - timedelta(days=9)
        )

        self.vac = Vacation.objects.create(
            label="vac",
            start_date=self.today - timedelta(days=2),
            end_date=self.today + timedelta(days=2)
        )
        self.structure = Structure.objects.create(
            label="test structure",
            code="STR",
            establishment=self.establishment
        )
        self.t_domain = TrainingDomain.objects.create(label="test t_domain")
        self.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=self.t_domain)
        self.training = Training.objects.create(label="test training")
        self.training2 = Training.objects.create(label="test training 2")
        self.highschool_training = Training.objects.create(
            label="test highschool training",
            highschool=self.high_school
        )
        self.training.training_subdomains.add(self.t_sub_domain)
        self.training2.training_subdomains.add(self.t_sub_domain)
        self.highschool_training.training_subdomains.add(self.t_sub_domain)
        self.training.structures.add(self.structure)
        self.training2.structures.add(self.structure)
        self.ref_str.structures.add(self.structure)

        self.course = Course.objects.create(
            label="course 1",
            training=self.training,
            structure=self.structure
        )
        self.course.speakers.add(self.speaker1)
        self.highschool_course = Course.objects.create(
            label="course 1",
            training=self.highschool_training,
            highschool=self.high_school
        )
        self.highschool_course.speakers.add(self.highschool_speaker)
        self.campus = Campus.objects.create(label='Esplanade')
        self.building = Building.objects.create(label='Le portique', campus=self.campus)
        self.course_type = CourseType.objects.create(label='CM')
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
        self.slot2.speakers.add(self.speaker1),
        self.highschool_slot.speakers.add(self.highschool_speaker),

        self.hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=datetime.today(),
            civility=1,
            phone='0123456789',
            level=2,
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
            civility=2,
            phone='0123456789',
            level=3,
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
            civility=StudentRecord.CIVS[0][0],
            birth_date=datetime.today(),
            level=StudentRecord.LEVELS[0][0],
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0],
            allowed_global_registrations=2,
            allowed_first_semester_registrations=0,
            allowed_second_semester_registrations=0,
        )
        self.student_record2 = StudentRecord.objects.create(
            student=self.student2,
            uai_code='0597065J',  # Université de Lille
            civility=StudentRecord.CIVS[0][0],
            birth_date=datetime.today(),
            level=StudentRecord.LEVELS[0][0],
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0],
            allowed_global_registrations=2,
            allowed_first_semester_registrations=0,
            allowed_second_semester_registrations=0,
        )

        self.immersion = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.slot,
        )
        self.immersion2 = Immersion.objects.create(
            student=self.student,
            slot=self.slot
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


    def test_API_get_documents__ok(self):
        request.user = self.ref_etab_user

        url = "/api/get_available_documents/"
        ajax_request = self.client.get(url, request, **self.header)
        content = ajax_request.content.decode()

        json_content = json.loads(content)
        self.assertIn('msg', json_content)
        self.assertIn('data', json_content)
        self.assertIsInstance(json_content['data'], list)
        self.assertIsInstance(json_content['msg'], str)

        docs = AccompanyingDocument.objects.filter(active=True)
        self.assertEqual(len(json_content['data']), docs.count())


    def test_API_get_documents__wrong_request(self):
        """No access"""
        request = self.client.get('/api/get_available_documents/')
        self.assertEqual(request.status_code, 403)  # forbidden


    def test_API_ajax_check_course_publication(self):
        request.user = self.ref_etab_user
        url = "/api/check_course_publication/1"

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
        request.user = self.ref_etab_user
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
        request.user = self.ref_etab_user
        url = f"/api/get_buildings/{self.campus.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['id'], self.building.id)
        self.assertEqual(content['data'][0]['label'], self.building.label)


    def test_API_ajax_get_courses_by_training(self):
        request.user = self.ref_etab_user
        url = f"/api/get_courses_by_training/{self.structure.id}/{self.training.id}"
        response = self.client.post(url, {}, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['key'], self.course.id)
        self.assertEqual(content['data'][0]['label'], self.course.label)
        self.assertEqual(content['data'][0]['url'], self.course.url)
        self.assertEqual(content['data'][0]['slots'], Slot.objects.filter(course__training=self.training).count())


    def test_API_get_ajax_slots(self):
        request.user = self.ref_etab_user
        url = "/api/get_slots"
        data = {
            'training_id': self.training.id
        }
        response = self.client.get(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 6)
        slot = content['data'][0]
        self.assertEqual(slot['id'], self.slot.id)
        self.assertEqual(slot['published'], self.slot.published)
        self.assertEqual(slot['course']['label'], self.slot.course.label)
        self.assertEqual(slot['structure']['code'], self.slot.course.structure.code)
        self.assertTrue(slot['structure']['managed_by_me'])
        self.assertEqual(slot['course_type'], self.slot.course_type.label)
        self.assertEqual(slot['date'], _date(self.today, 'l d/m/Y'))
        self.assertEqual(slot['time']['start'], '12h00')
        self.assertEqual(slot['time']['end'], '14h00')
        self.assertEqual(slot['location']['campus'], self.slot.campus.label)
        self.assertEqual(slot['location']['building'], self.slot.building.label)
        self.assertEqual(slot['room'], self.slot.room)
        self.assertEqual(slot['n_register'], self.slot.registered_students())
        self.assertEqual(slot['n_places'], self.slot.n_places)


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
        self.assertEqual(len(content['data']), 5)


    def test_API_get_trainings(self):
        request.user = self.ref_etab_user
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


    def test_API_get_student_records(self):
        request.user = self.ref_etab_user
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
        self.assertGreater(len(content['msg']), 0)

        # To validate - With high school id
        self.hs_record.validation = 1  # to validate
        self.hs_record.save()
        data = {
            'action': 'TO_VALIDATE',
            'high_school_id': self.hs_record.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content['data']), 2)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)
        self.assertEqual(hs_record['first_name'], self.hs_record.student.first_name)
        self.assertEqual(hs_record['last_name'], self.hs_record.student.last_name)
        self.assertEqual(hs_record['level'], HighSchoolStudentRecord.LEVELS[self.hs_record.level - 1][1])
        self.assertEqual(hs_record['class_name'], self.hs_record.class_name)

        # Validated
        self.hs_record.validation = 2  # validate
        self.hs_record.save()
        data = {
            'action': 'VALIDATED',
            'high_school_id': self.hs_record.id
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
            'high_school_id': self.hs_record.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)


    def test_API_ajax_get_reject_student(self):
        request.user = self.ref_etab_user
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
        client.login(username='lycref', password='pass')
        response = client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 3)  # rejected


    def test_API_ajax_get_validate_student__ok(self):
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()
        request.user = self.ref_etab_user
        url = "/api/validate_student/"
        
        data = {
            'student_record_id': self.hs_record.id
        }
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertTrue(content['data']['ok'])
        self.hs_record.refresh_from_db()
        self.assertEqual(self.hs_record.validation, 2)  # validated


    def test_API_get_csv_anonymous_immersion(self):
        url = f'/api/get_csv_anonymous_immersion/'
        response = self.client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))

        headers = [
            _('structure') + " / " + _('highschool'),
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
            _('room'),
            _('registration number'),
            _('place number'),
            _('additional information'),
            _('origin institution'),
            _('student level'),
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
                self.assertEqual(str(self.slot.registered_students()), row[12])
                self.assertEqual(str(self.slot.n_places), row[13])
                self.assertEqual(self.slot.additional_information, row[14])
                self.assertEqual(self.high_school.label, row[15])
                self.assertEqual(HighSchoolStudentRecord.LEVELS[self.hs_record.level - 1][1], row[16])
            elif n == 2:
                self.assertEqual(self.student_record.uai_code, row[15])
                self.assertEqual(StudentRecord.LEVELS[self.student_record.level - 1][1], row[16])
            elif n == 5: # high school slot
                self.assertEqual(f"{self.high_school.city} - {self.high_school.label}", row[0])
                self.assertEqual(self.highschool_training.label, row[3])
                self.assertEqual(self.highschool_course.label, row[4])
                self.assertIn(self.highschool_slot.start_time.strftime("%H:%M"), row[7])
                self.assertIn(self.highschool_slot.end_time.strftime("%H:%M"), row[8])
                self.assertEqual("", row[9])
                self.assertEqual("", row[10])
                self.assertEqual(self.highschool_slot.room, row[11])
                self.assertEqual(str(self.highschool_slot.registered_students()), row[12])
                self.assertEqual(self.highschool_slot.additional_information, row[14])

            n += 1


    def test_API_get_csv_highschool(self):
        url = f'/api/get_csv_highschool/{self.high_school.id}'
        client = Client()
        client.login(username='lycref', password='pass')

        request.user = self.lyc_ref
        response = client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))
        headers = [
            _('last name'),
            _('first name'),
            _('birthdate'),
            _('level'),
            _('class name'),
            _('bachelor type'),
            _('training domain'),
            _('training subdomain'),
            _('training'),
            _('course'),
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
                self.assertEqual(HighSchoolStudentRecord.LEVELS[self.hs_record.level - 1][1], row[3])
                self.assertEqual(self.hs_record.class_name, row[4])
                self.assertEqual(HighSchoolStudentRecord.BACHELOR_TYPES[self.hs_record.bachelor_type - 1][1], row[5])
                self.assertIn(self.t_domain.label, row[6].split('|'))
                self.assertIn(self.t_sub_domain.label, row[7].split('|'))
                self.assertIn(self.training.label, row[8])
                self.assertIn(self.course.label, row[9])

            n += 1


    def test_API_get_csv_structures(self):
        url = f'/api/get_csv_structures/{self.high_school.id}'
        client = Client()
        client.login(username='ref_str', password='pass')

        request.user = self.ref_str
        response = client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))
        headers = [
            _('domain'),
            _('subdomain'),
            _('training'),
            _('course'),
            _('course type'),
            _('date'),
            _('start_time'),
            _('end_time'),
            _('campus'),
            _('building'),
            _('room'),
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
                self.assertIn(self.t_domain.label, row[0].split('|'))
                self.assertIn(self.t_sub_domain.label, row[1].split('|'))
                self.assertIn(self.training.label, row[2])
                self.assertIn(self.course.label, row[3])
                self.assertIn(self.course_type.label, row[4])
                self.assertIn(_date(self.today, 'd/m/Y'), row[5])
                self.assertIn(self.slot.start_time.strftime("%H:%M"), row[6])
                self.assertIn(self.slot.end_time.strftime("%H:%M"), row[7])
                self.assertIn(self.slot.campus.label, row[8])
                self.assertIn(self.slot.building.label, row[9])
                self.assertEqual(self.slot.room, row[10])
                self.assertIn(
                    f'{self.speaker1.first_name} {self.speaker1.last_name}',
                    row[11].split('|')
                ),
                self.assertEqual(str(self.slot.registered_students()), row[12])
                self.assertEqual(str(self.slot.n_places), row[13])
                self.assertEqual(self.slot.additional_information, row[14])

            n += 1

    def test_API_ajax_get_available_vars(self):
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


    def test_API_get_person__no_data(self):
        request.user = self.ref_etab_user

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
        data["username"] = "whatever"
        response = self.client.post(url, data, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "")
        self.assertEqual(content['data'], [])


    def test_API_get_courses(self):
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


    def test_API_ajax_delete_course(self):
        request.user = self.ref_etab_user
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
            f"{self.course.structure.code} ({self.course.structure.establishment.short_label})",
            c['managed_by']
        )
        self.assertEqual(self.course.training.label, c['training_label'])
        self.assertEqual(self.course.label, c['label'])
        # speakers
        self.assertEqual(self.course.slots_count(speaker_id=self.speaker1.id), c['slots_count'])
        self.assertEqual(self.course.free_seats(speaker_id=self.speaker1.id), c['n_places'])
        self.assertEqual(
            self.course.published_slots_count(speaker_id=self.speaker1.id),
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
        self.assertEqual(self.highschool_course.slots_count(speaker_id=self.highschool_speaker.id), c['slots_count'])
        self.assertEqual(self.highschool_course.free_seats(speaker_id=self.highschool_speaker.id), c['n_places'])
        self.assertEqual(
            self.highschool_course.published_slots_count(speaker_id=self.highschool_speaker.id),
            c['published_slots_count']
        )

    def test_API_get_my_slots(self):
        client = Client()
        url = f"/api/get_slots?visits=false"
        # as a high school speaker
        client.login(username='highschool_speaker', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.highschool_slot.id, s['id'])
        self.assertEqual(self.highschool_slot.published, s['published'])
        self.assertEqual(f"{self.high_school.city} - {self.high_school.label}", s['highschool']['label'])
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
        self.assertEqual(self.slot.id, s['id'])
        self.assertEqual(self.slot.published, s['published'])
        self.assertEqual(self.slot.course.structure.code, s['structure']['code'])
        self.assertEqual(
            f'{self.slot.course.training.label} ({self.slot.course_type.label})',
            s['training_label']
        )
        self.assertEqual(
            f'{self.slot.course.training.label} ({self.slot.course_type.full_label})',
            s['training_label_full']
        )
        self.assertEqual(self.slot.campus.label, s['location']['campus'])
        self.assertEqual(self.slot.building.label, s['location']['building'])

        self.assertEqual(self.slot.room, s['room'])

        self.assertEqual(_date(self.slot.date, 'l d/m/Y'), s['date'])
        self.assertEqual(self.slot.start_time.strftime("%Hh%M"), s['time']['start'])
        self.assertEqual(self.slot.end_time.strftime("%Hh%M"), s['time']['end'])

        self.assertEqual(self.slot.course.label, s['course']['label'])
        # TODO: speakers
        self.assertEqual(self.slot.n_places, s['n_places'])
        self.assertEqual(self.slot.registered_students(), s['n_register'])
        self.assertEqual(self.slot.additional_information, s['additional_information'])

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
        client = Client()
        client.login(username='student', password='pass')

        url = f"/api/get_immersions/{self.speaker1.id}"

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error : invalid user id")
        self.assertEqual(content['data'], [])

        # User not found
        request.user = self.ref_etab_user

        url = f"/api/get_immersions/999"
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['data'], [])
        self.assertEqual(content['msg'], "Error : no such user")

        # No user
        url = "/api/get_immersions/0"
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())
        self.assertEqual(content['msg'], "Error : missing user id")
        self.assertEqual(content['data'], [])

        # Get future immersions
        self.slot.date = self.today + timedelta(days=2)
        self.slot.save()
        url = f"/api/get_immersions/{self.highschool_user.id}/future"
        
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course'])
        self.assertEqual(self.immersion.slot.course_type.label, i['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['type_full'])
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
        url = f"/api/get_immersions/{self.highschool_user.id}/past"
        
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course'])
        self.assertEqual(self.immersion.slot.course_type.label, i['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['type_full'])
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
        url = f"/api/get_immersions/{self.highschool_user.id}/cancelled"
        
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertEqual(self.immersion.id, i['id'])
        self.assertEqual(self.immersion.slot.course.training.label, i['training'])
        self.assertEqual(self.immersion.slot.course.label, i['course'])
        self.assertEqual(self.immersion.slot.course_type.label, i['type'])
        self.assertEqual(self.immersion.slot.course_type.full_label, i['type_full'])
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


    def test_API_ajax_get_slot_registrations(self):
        request.user = self.ref_etab_user

        url = f"/api/get_slot_registrations/{self.slot.id}"
        
        response = self.client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 2)
        hs = content['data'][0]
        self.assertEqual(hs['id'], self.immersion.id)
        self.assertEqual(hs['lastname'], self.highschool_user.last_name)
        self.assertEqual(hs['firstname'], self.highschool_user.first_name)
        self.assertEqual(hs['profile'], _('High-school student'))
        self.assertEqual(hs['school'], self.hs_record.highschool.label)
        self.assertEqual(hs['level'], self.hs_record.get_level_display())
        self.assertEqual(hs['city'], self.hs_record.highschool.city)
        self.assertEqual(hs['attendance'], self.immersion.get_attendance_status_display())
        self.assertEqual(hs['attendance_status'], self.immersion.attendance_status)

        stu = content['data'][1]
        self.assertEqual(stu['profile'], _('Student'))
        self.assertEqual(stu['level'], self.student_record.get_level_display())
        self.assertEqual(stu['school'], self.student_record.uai_code)
        self.assertEqual(stu['city'], '')


    def test_API_ajax_get_available_students(self):
        request.user = self.ref_etab_user

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

        self.assertEqual(self.student2.id, stu['id'])
        self.assertEqual(self.student2.first_name, stu['firstname'])
        self.assertEqual(self.student2.last_name, stu['lastname'])
        self.assertEqual(pgettext('person type', 'Student'), stu['profile'])
        self.assertEqual(self.student_record2.uai_code, stu['school'])
        self.assertEqual('', stu['level'])
        self.assertEqual('', stu['city'])
        self.assertEqual('', stu['class'])
        self.assertEqual(self.highschool_user2.id, hs['id'])
        self.assertEqual(self.highschool_user2.first_name, hs['firstname'])
        self.assertEqual(self.highschool_user2.last_name, hs['lastname'])
        self.assertEqual(pgettext('person type', 'High school student'), hs['profile'])
        self.assertEqual(self.hs_record2.highschool.label, hs['school'])
        self.assertEqual('', hs['level'])
        self.assertEqual(self.hs_record2.highschool.city, hs['city'])
        self.assertEqual(self.hs_record2.class_name, hs['class'])


    def test_API_ajax_get_highschool_students(self):
        request.user = self.ref_etab_user

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
        request.user = self.lyc_ref
        client = Client()
        client.login(username='lycref', password='pass')

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 2)

        # Students
        self.hs_record.level = 3
        self.hs_record.origin_bachelor_type = 1
        self.hs_record.post_bachelor_level = 1
        self.hs_record.save()

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(len(content['data']), 2)

        one = False
        for h in content['data']:
            if h['level'] == HighSchoolStudentRecord.LEVELS[2][1]:
                self.assertEqual(self.hs_record.get_post_bachelor_level_display(), h['post_bachelor_level'])
                self.assertEqual(self.hs_record.get_origin_bachelor_type_display(), h['bachelor'])
                one = True
                break
        self.assertTrue(one)

        # Fail : as a high school manager with no high school
        self.lyc_ref.highschool = None
        self.lyc_ref.save()

        response = client.get(url, request, **self.header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], "Invalid parameters")
        self.assertEqual(content['data'], [])


    def test_API_ajax_check_date_between_vacation(self):
        request.user = self.ref_etab_user

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


        # Success
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        self.assertIsNone(self.immersion.cancellation_type)

        data = {
            'immersion_id': self.immersion.id,
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())
        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Immersion cancelled")

        self.immersion.refresh_from_db()
        self.assertEqual(self.immersion.cancellation_type.id, self.cancel_type.id)


    def test_API_ajax_set_attendance(self):
        request.user = self.ref_etab_user
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

        # Success
        self.assertEqual(self.immersion.attendance_status, 0)
        data = {
            'immersion_id': self.immersion.id,
            'attendance_value': 1
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], '')
        self.assertEqual(content['msg'], "Attendance status updated")

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

        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], '')
        self.assertEqual(content['msg'], "Attendance status updated")

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
        self.assertGreater(len(content['error']), 0)
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
        request.user = self.ref_etab_user
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

        # Success
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()

        data = {
            'immersion_ids': json.dumps([self.immersion.id]),
            'reason_id': self.cancel_type.id
        }
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

        self.assertFalse(content['error'])
        self.assertEqual(content['msg'], "Immersion(s) cancelled")
        self.assertIsNone(content['err_msg'])


    def test_API_ajax_send_email_us(self):
        request.user = self.ref_etab_user
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
        request.user = self.ref_etab_user
        url = "/api/get_students_presence"
        
        data = {}
        content = json.loads(self.client.post(url, data, **self.header).content.decode())

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
        self.assertEqual(self.immersion.slot.room, i['room'])


    def test_API_ajax_set_course_alert(self):
        request.user = self.ref_etab_user
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

        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {'semester1': 2, 'semester2': 2, 'annually': 1}
        )

        client = Client()
        client.login(username='@EXTERNAL@_hs', password='pass')

        # Should work
        response = client.post("/api/register", {'slot_id': self.slot3.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))

        self.assertEqual("Registration successfully added", content['msg'])
        self.assertEqual(
            self.highschool_user.remaining_registrations_count(),
            {'semester1': 2, 'semester2': 2, 'annually': 0}
        )
        self.assertTrue(Immersion.objects.filter(student=self.highschool_user, slot=self.slot3).exists())

        # Fail : already registered
        response = client.post("/api/register", {'slot_id': self.slot3.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Already registered to this slot", content['msg'])

        # Fail : no more registration allowed
        response = client.post("/api/register", {'slot_id': self.slot2.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("""You have no more remaining registration available, """
                         """you should cancel an immersion or contact immersion service""", content['msg'])

        # reset immersions
        Immersion.objects.filter(student=self.highschool_user).delete()

        # Fail with past slot registration
        response = client.post("/api/register", {'slot_id': self.past_slot.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Register to past slot is not available", content['msg'])

        # Fail with full slot registration
        response = client.post("/api/register", {'slot_id': self.full_slot.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("No seat available for selected slot", content['msg'])

        # Fail with unpublished slot
        response = client.post("/api/register", {'slot_id': self.unpublished_slot.id}, **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Registering an unpublished slot is forbidden", content['msg'])

        # Todo : needs more tests with other users (ref-etab, ref-str, ...)
        # Todo : needs tests with a calendar in semester mode

    def test_ajax_get_duplicates(self):
        self.hs_record.duplicates = "[%s]" % self.hs_record2.id
        self.hs_record.save()

        self.hs_record2.duplicates = "[%s]" % self.hs_record.id
        self.hs_record2.save()

        client = Client()
        client.login(username='ref_etab', password='pass')
        
        response = client.get("/api/get_duplicates", **self.header, follow=True)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['data'], [
            {'id': 0, 'record_ids': [1, 2],
             'names': ['SCHOOL high', 'SCHOOL2 high2'],
             'birthdates': [_date(self.hs_record.birth_date), _date(self.hs_record2.birth_date)],
             'highschools': ['HS1, 1ere S 3', 'HS1, TS 3'],
             'emails': ['hs@no-reply.com', 'hs2@no-reply.com'],
             'record_links': ['/immersion/hs_record/1', '/immersion/hs_record/2']}]
        )

    def test_ajax_keep_entries(self):
        self.hs_record.duplicates = "[%s]" % self.hs_record2.id
        self.hs_record.save()

        self.hs_record2.duplicates = "[%s]" % self.hs_record.id
        self.hs_record2.save()

        client = Client()
        client.login(username='ref_etab', password='pass')

        data = {
            "entries[]": [self.hs_record.id, self.hs_record2.id]
        }
        response = client.post("/api/keep_entries", data, **self.header)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual("Duplicates data cleared", content['msg'])

        r1 = HighSchoolStudentRecord.objects.get(pk=self.hs_record.id)
        r2 = HighSchoolStudentRecord.objects.get(pk=self.hs_record2.id)

        self.assertEqual(r1.solved_duplicates, '2')
        self.assertEqual(r2.solved_duplicates, '1')


    def test_campus(self):
        campus = Campus.objects.create(label='Campus', establishment=self.establishment, active=True)

        client = Client()
        client.login(username='ref_etab', password='pass')

        response = client.get(reverse("campus_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content[0]['label'], 'Campus')


    def test_high_school_speakers(self):
        client = Client()

        # Success
        client.login(username='lycref', password='pass')
        response = client.get(
            reverse("get_highschool_speakers", kwargs={'highschool_id': self.high_school.id}), 
            **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['data'], [{
            'id': 8,
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
        self.assertEqual(content[0]['establishment'], "ETA1 : Etablissement 1 (master)")

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
        self.assertEqual(content[0]['establishment']['id'], 1)
        self.assertEqual(content[0]['establishment']['code'], 'ETA1')
        self.assertEqual(content[0]['establishment']['label'], 'Etablissement 1')

        # As ref-lyc
        client.login(username='lycref', password='pass')
        response = client.get(reverse("off_offer_event_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]['label'], 'High school event')
        self.assertEqual(content[0]['highschool'], f"{self.high_school.city} - {self.high_school.label}")

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

        # as master_ref_etab : no access to high school events
        client.login(username='ref_master_etab', password='pass')
        response = client.delete(reverse("off_offer_event_detail", kwargs={'pk': event2.id}))
        self.assertIn("Insufficient privileges", response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(OffOfferEvent.objects.count(), 1)