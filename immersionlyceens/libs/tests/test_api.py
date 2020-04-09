"""
Django API tests suite
"""
import csv
import json
import unittest
from datetime import datetime, time, timedelta

from django.utils.translation import pgettext, ugettext_lazy as _
from django.template.defaultfilters import date as _date
from compat.templatetags.compat import url
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, Building, Campus, Component, Course, CourseType, HighSchool, Slot,
    Training, TrainingDomain,
    TrainingSubdomain,
    Immersion, MailTemplateVars, MailTemplate, Calendar, CancelType, ImmersionUser, Vacation,
    UserCourseAlert, GeneralSettings)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, StudentRecord
from immersionlyceens.libs.api.views import ajax_check_course_publication

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.defaultfilters import date as _date
from django.test import Client, RequestFactory, TestCase

request_factory = RequestFactory()
request = request_factory.get('/admin')


class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group']

    def setUp(self):
        GeneralSettings.objects.create(setting='MAIL_CONTACT_SCUIO_IP', value='unittest@unittest.fr')
        self.scuio_user = get_user_model().objects.create_user(
            username='scuio', password='pass', email='immersion@no-reply.com', first_name='scuio', last_name='scuio',
        )
        self.highschool_user = get_user_model().objects.create_user(
            username='hs', password='pass', email='hs@no-reply.com', first_name='high', last_name='SCHOOL',
        )
        self.highschool_user2 = get_user_model().objects.create_user(
            username='hs2', password='pass', email='hs2@no-reply.com', first_name='high2', last_name='SCHOOL2',
        )
        self.highschool_user3 = get_user_model().objects.create_user(
            username='hs3', password='pass', email='hs3@no-reply.com', first_name='high3', last_name='SCHOOL3',
        )
        self.ref_comp = get_user_model().objects.create_user(
            username='refcomp',
            password='pass',
            email='refcomp@no-reply.com',
            first_name='refcomp',
            last_name='refcomp',
        )
        self.teacher1 = get_user_model().objects.create_user(
            username='teacher1',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='teach',
            last_name='HER',
        )
        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
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
        self.client.login(username='scuio', password='pass')

        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_comp)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user2)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user3)
        Group.objects.get(name='ETU').user_set.add(self.student)
        Group.objects.get(name='ETU').user_set.add(self.student2)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

        self.today = datetime.today()
        self.calendar = Calendar.objects.create(
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
        self.component = Component.objects.create(label="test component")
        self.t_domain = TrainingDomain.objects.create(label="test t_domain")
        self.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=self.t_domain)
        self.training = Training.objects.create(label="test training")
        self.training2 = Training.objects.create(label="test training 2")
        self.training.training_subdomains.add(self.t_sub_domain)
        self.training2.training_subdomains.add(self.t_sub_domain)
        self.training.components.add(self.component)
        self.training2.components.add(self.component)
        self.course = Course.objects.create(label="course 1", training=self.training, component=self.component)
        self.course.teachers.add(self.teacher1)
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
            date=self.today,
            start_time=time(12, 0),
            end_time=time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        self.slot.teachers.add(self.teacher1),
        self.slot2.teachers.add(self.teacher1),
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
        )
        self.hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=datetime.today(),
            civility=1,
            phone='0123456789',
            level=1,
            class_name='1ere S 3',
            bachelor_type=3,
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
        )
        self.hs_record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school,
            birth_date=datetime.today(),
            civility=2,
            phone='0123456789',
            level=2,
            class_name='TS 3',
            bachelor_type=3,
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
        )
        self.student_record = StudentRecord.objects.create(
            student=self.student,
            home_institution='Université de Strasbourg',
            civility=StudentRecord.CIVS[0][0],
            birth_date=datetime.today(),
            level=StudentRecord.LEVELS[0][0],
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0]
        )
        self.student_record2 = StudentRecord.objects.create(
            student=self.student2,
            home_institution='Université de Lille',
            civility=StudentRecord.CIVS[0][0],
            birth_date=datetime.today(),
            level=StudentRecord.LEVELS[0][0],
            origin_bachelor_type=StudentRecord.BACHELOR_TYPES[0][0]
        )
        self.lyc_ref.highschool = self.high_school
        self.lyc_ref.save()
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


    def test_API_get_documents__ok(self):
        request.user = self.scuio_user

        url = "/api/get_available_documents/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        ajax_request = self.client.get(url, request, **header)

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

    def test_API_ajax_check_course_publication__false(self):
        self.course.published = False
        self.course.save()

        request.user = self.scuio_user
        url = "/api/check_course_publication/1"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        content = json.loads(self.client.post(url, {}, **header).content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], dict)
        self.assertIsInstance(content['msg'], str)
        self.assertFalse(content['data']['published'])

    def test_API_ajax_check_course_publication__true(self):
        self.course.published = True
        self.course.save()
        request.user = self.scuio_user
        url = "/api/check_course_publication/1"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        content = json.loads(self.client.post(url, {}, **header).content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], dict)
        self.assertIsInstance(content['msg'], str)
        self.assertTrue(content['data']['published'])

    def test_API_ajax_check_course_publication__true(self):
        self.course.published = True
        self.course.save()
        request.user = self.scuio_user
        url = "/api/check_course_publication/1"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        content = json.loads(self.client.post(url, {}, **header).content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], dict)
        self.assertIsInstance(content['msg'], str)
        self.assertTrue(content['data']['published'])

    def test_API_ajax_check_course_publication__404(self):
        request.user = self.scuio_user
        url = "/api/check_course_publication/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        response = self.client.post(url, {}, **header)
        self.assertEqual(response.status_code, 404)

    def test_API_ajax_get_course_teachers__404(self):
        request.user = self.scuio_user
        url = "/api/check_course_teachers/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, {}, **header)
        self.assertEqual(response.status_code, 404)

    def test_API_ajax_get_course_teachers__ok(self):
        request.user = self.scuio_user
        url = "/api/get_course_teachers/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, {}, **header)
        self.assertEqual(response.status_code, 404)

    def test_API_ajax_get_course_teachers__ok(self):
        request.user = self.scuio_user
        url = f"/api/get_course_teachers/{self.course.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, {}, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 1)
        self.assertIsInstance(content['data'][0], dict)
        self.assertEqual(content['data'][0]['id'], self.teacher1.id)
        self.assertEqual(content['data'][0]['first_name'], self.teacher1.first_name)
        self.assertEqual(content['data'][0]['last_name'], self.teacher1.last_name)

    def test_API_ajax_get_buildings__ok(self):
        request.user = self.scuio_user
        url = f"/api/get_buildings/{self.campus.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, {}, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 1)
        self.assertIsInstance(content['data'][0], dict)
        self.assertEqual(content['data'][0]['id'], self.building.id)
        self.assertEqual(content['data'][0]['label'], self.building.label)

    def test_API_ajax_get_courses_by_training(self):
        request.user = self.scuio_user
        url = f"/api/get_courses_by_training/{self.component.id}/{self.training.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, {}, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 1)
        self.assertIsInstance(content['data'][0], dict)
        self.assertEqual(content['data'][0]['key'], self.course.id)
        self.assertEqual(content['data'][0]['label'], self.course.label)
        self.assertEqual(content['data'][0]['url'], self.course.url)
        self.assertEqual(content['data'][0]['slots'], Slot.objects.filter(course__training=self.training).count())

    def test_API_get_ajax_slots_ok(self):
        request.user = self.scuio_user
        url = f"/api/get_slots"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'component_id': self.component.id, 'training_id': self.training.id}
        response = self.client.get(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 2)
        self.assertIsInstance(content['data'][0], dict)
        slot = content['data'][0]
        self.assertEqual(slot['id'], self.slot.id)
        self.assertEqual(slot['published'], self.slot.published)
        self.assertEqual(slot['course_label'], self.slot.course.label)
        self.assertEqual(slot['component']['code'], self.slot.course.component.code)
        self.assertTrue(slot['component']['managed_by_me'])
        self.assertEqual(slot['course_type'], self.slot.course_type.label)
        self.assertEqual(slot['date'], _date(self.today, 'l d/m/Y'))
        self.assertEqual(slot['time']['start'], '12h00')
        self.assertEqual(slot['time']['end'], '14h00')
        self.assertEqual(slot['location']['campus'], self.slot.campus.label)
        self.assertEqual(slot['location']['building'], self.slot.building.label)
        self.assertEqual(slot['room'], self.slot.room)
        self.assertEqual(slot['n_register'], self.slot.registered_students())
        self.assertEqual(slot['n_places'], self.slot.n_places)

    def test_API_get_ajax_slots_ok__no_training_id(self):
        request.user = self.scuio_user
        url = f"/api/get_slots"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'component_id': self.component.id}
        response = self.client.get(url, data, **header)
        content = json.loads(response.content.decode())
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 2)
        self.assertIsInstance(content['data'][0], dict)
        slot = content['data'][0]
        self.assertEqual(slot['id'], self.slot.id)
        self.assertEqual(slot['published'], self.slot.published)
        self.assertEqual(slot['course_label'], self.slot.course.label)
        self.assertEqual(slot['component']['code'], self.slot.course.component.code)
        self.assertTrue(slot['component']['managed_by_me'])
        self.assertEqual(slot['course_type'], self.slot.course_type.label)
        self.assertEqual(slot['date'], _date(self.today, 'l d/m/Y'))
        self.assertEqual(slot['time']['start'], '12h00')
        self.assertEqual(slot['time']['end'], '14h00')
        self.assertEqual(slot['location']['campus'], self.slot.campus.label)
        self.assertEqual(slot['location']['building'], self.slot.building.label)
        self.assertEqual(slot['room'], self.slot.room)
        self.assertEqual(slot['n_register'], self.slot.registered_students())
        self.assertEqual(slot['n_places'], self.slot.n_places)

    def test_API_get_ajax_slots_ref_cmp(self):
        client = Client()
        client.login(username='refcomp', password='pass')

        url = f"/api/get_slots"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'component_id': self.component.id, 'training_id': self.training.id}
        response = client.get(url, data, **header)
        self.assertGreaterEqual(response.status_code, 200)
        self.assertLess(response.status_code, 300)

    def test_API_get_trainings(self):
        request.user = self.scuio_user
        url = f"/api/get_trainings"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'component_id': self.component.id}

        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 2)
        self.assertIsInstance(content['data'][0], dict)
        t1 = content['data'][0]
        self.assertEqual(t1['label'], self.training.label)
        self.assertEqual(t1['subdomain'], [s.label for s in self.training.training_subdomains.filter(active=True)])

        t2 = content['data'][1]
        self.assertEqual(t2['label'], self.training2.label)
        self.assertEqual(t2['subdomain'], [s.label for s in self.training2.training_subdomains.filter(active=True)])

    def test_API_get_trainings__empty(self):
        request.user = self.scuio_user
        url = f"/api/get_trainings"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 0)

    def test_API_get_student_records__no_action(self):
        request.user = self.scuio_user
        url = "/api/get_student_records/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 0)
        self.assertGreater(len(content['msg']), 0)

    def test_API_get_student_records__no_student_hs_id(self):
        request.user = self.scuio_user
        url = "/api/get_student_records/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'action': 'TO_VALIDATE'}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 0)
        self.assertGreater(len(content['msg']), 0)

    def test_API_get_student_records__TO_VALIDATE(self):
        request.user = self.scuio_user
        self.hs_record.validation = 1  # to validate
        self.hs_record.save()
        url = "/api/get_student_records/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'action': 'TO_VALIDATE', 'high_school_id': self.hs_record.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 2)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)
        self.assertEqual(hs_record['first_name'], self.hs_record.student.first_name)
        self.assertEqual(hs_record['last_name'], self.hs_record.student.last_name)
        self.assertEqual(hs_record['level'], HighSchoolStudentRecord.LEVELS[self.hs_record.level - 1][1])
        self.assertEqual(hs_record['class_name'], self.hs_record.class_name)

    def test_API_get_student_records__VALIDget_available_documentsATED(self):
        request.user = self.scuio_user
        self.hs_record.validation = 2  # validate
        self.hs_record.save()
        url = "/api/get_student_records/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'action': 'VALIDATED', 'high_school_id': self.hs_record.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)

    def test_API_get_student_records__REJECTED(self):
        request.user = self.scuio_user
        self.hs_record.validation = 3  # rejected
        self.hs_record.save()
        url = "/api/get_student_records/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'action': 'REJECTED', 'high_school_id': self.hs_record.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['data'], list)
        self.assertIsInstance(content['msg'], str)
        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)

    def test_API_ajax_get_reject_student__no_high_school_student_id(self):
        request.user = self.scuio_user
        url = "/api/reject_student/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsNone(content['data'])
        self.assertIsInstance(content['msg'], str)
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_get_reject_student__no_high_school_student_id(self):
        request.user = self.scuio_user
        url = "/api/reject_student/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_record_id': 0}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsNone(content['data'])
        self.assertIsInstance(content['msg'], str)
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_get_reject_student__ok(self):
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()
        request.user = self.scuio_user
        url = "/api/reject_student/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_record_id': self.hs_record.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['msg'], str)
        self.assertIsInstance(content['data'], dict)
        self.assertTrue(content['data']['ok'])
        h = HighSchoolStudentRecord.objects.get(id=self.hs_record.id)
        self.assertEqual(h.validation, 3)  # rejected

    def test_API_ajax_get_reject_student__LYC_REF(self):
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()

        client = Client()
        client.login(username='lycref', password='pass')

        url = "/api/reject_student/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_record_id': self.hs_record.id}
        response = client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['msg'], str)
        self.assertIsInstance(content['data'], dict)
        self.assertTrue(content['data']['ok'])
        h = HighSchoolStudentRecord.objects.get(id=self.hs_record.id)
        self.assertEqual(h.validation, 3)  # rejected

    def test_API_ajax_get_validate_student__ok(self):
        self.hs_record.validation = 1  # TO_VALIDATE
        self.hs_record.save()
        request.user = self.scuio_user
        url = "/api/validate_student/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_record_id': self.hs_record.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertIsInstance(content['msg'], str)
        self.assertIsInstance(content['data'], dict)
        self.assertTrue(content['data']['ok'])
        h = HighSchoolStudentRecord.objects.get(id=self.hs_record.id)
        self.assertEqual(h.validation, 2)  # validated

    def test_API_get_csv_anonymous_immersion(self):
        url = f'/api/get_csv_anonymous_immersion/'
        response = self.client.get(url, request)

        content = csv.reader(response.content.decode().split('\n'))

        headers = [
            _('component'),
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
                self.assertEqual(self.component.label, row[0])
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
                self.assertEqual(self.student_record.home_institution, row[15])
                self.assertEqual(StudentRecord.LEVELS[self.student_record.level - 1][1], row[16])
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



    def test_API_get_csv_components(self):
        url = f'/api/get_csv_components/{self.high_school.id}'
        client = Client()
        client.login(username='refcomp', password='pass')

        request.user = self.ref_comp
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
            _('teachers'),
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
                    f'{self.teacher1.first_name} {self.teacher1.last_name}',
                    row[11].split('|')
                ),
                self.assertEqual(str(self.slot.registered_students()), row[12])
                self.assertEqual(str(self.slot.n_places), row[13])
                self.assertEqual(self.slot.additional_information, row[14])

            n += 1

    def test_API_ajax_get_available_vars(self):
        request.user = self.scuio_user

        url = f"/api/get_available_vars/{self.mail_t.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('data', content)
        self.assertIn('msg', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 1)
        var = content['data'][0]
        self.assertIsInstance(var, dict)
        self.assertEqual(var['id'], self.var.id)
        self.assertEqual(var['code'], self.var.code)
        self.assertEqual(var['description'], self.var.description)

    def test_API_ajax_get_available_vars__empty(self):
        request.user = self.scuio_user

        url = f"/api/get_available_vars/0"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('data', content)
        self.assertIn('msg', content)
        self.assertGreater(len(content['msg']), 0)
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 0)

    def test_API_get_person__no_data(self):
        request.user = self.scuio_user

        url = f"/api/get_person"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('data', content)
        self.assertIn('msg', content)
        self.assertGreater(len(content['msg']), 0)
        self.assertIsInstance(content['data'], list)
        self.assertEqual(content['data'], [])

    def test_API_get_courses__no_data(self):
        request.user = self.scuio_user

        url = f"/api/get_courses/{self.component.id}/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('data', content)
        self.assertIn('msg', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 1)
        c = content['data'][0]
        self.assertIsInstance(c, dict)
        self.assertEqual(c['id'], self.course.id)
        self.assertEqual(c['published'], self.course.published)
        self.assertEqual(c['training_label'], self.course.training.label)
        self.assertEqual(c['label'], self.course.label)
        self.assertEqual(c['component_code'], self.course.component.code)
        self.assertEqual(c['component_id'], self.course.component.id)

        teachers_naming = [f'{t.last_name} {t.first_name}' for t in self.course.teachers.all()]
        for t in c['teachers']:
            self.assertIn(t, teachers_naming)

        self.assertEqual(c['slots_count'], self.course.slots_count())
        self.assertEqual(c['n_places'], self.course.free_seats())
        self.assertEqual(c['published_slots_count'], self.course.published_slots_count())
        self.assertEqual(c['registered_students_count'], self.course.registrations_count())
        self.assertEqual(c['alerts_count'], 0)  # TODO:
        self.assertEqual(c['can_delete'], not self.course.slots.exists())

    def test_API_ajax_delete_course__no_data(self):
        request.user = self.scuio_user

        url = f"/api/delete_course"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('error', content)
        self.assertIn('msg', content)
        self.assertGreater(len(content['error']), 0)
        self.assertEqual(content['msg'], '')

    def test_API_ajax_delete_course__not_exists(self):
        request.user = self.scuio_user

        url = f"/api/delete_course"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': 0}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('error', content)
        self.assertIn('msg', content)
        self.assertEqual(len(content['error']), 0)
        self.assertEqual(content['msg'], '')

    def test_API_ajax_delete_course__no_slot_attach(self):
        request.user = self.scuio_user
        course_id = self.course.id

        self.slot.delete()
        self.slot2.delete()

        url = f"/api/delete_course"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('error', content)
        self.assertIn('msg', content)
        self.assertEqual(len(content['error']), 0)
        self.assertGreater(len(content['msg']), 0)
        self.assertEqual(Slot.objects.filter(course=self.course).count(), 0)

        with self.assertRaises(Course.DoesNotExist):
            Course.objects.get(id=self.course.id)

    def test_API_ajax_delete_course__slot_attach(self):
        request.user = self.scuio_user
        course_id = self.course.id

        url = f"/api/delete_course"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id}
        response = self.client.post(url, data, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('error', content)
        self.assertIn('msg', content)
        self.assertGreater(len(content['error']), 0)
        self.assertEqual(content['msg'], '')
        self.assertGreater(Slot.objects.filter(course=self.course).count(), 0)

        not_raised = True
        try:
            Course.objects.get(id=self.course.id)
        except Course.DoesNotExist:
            not_raised = False
        self.assertTrue(not_raised)

    def test_API_ajax_get_my_courses(self):
        request.user = self.teacher1
        client = Client()
        client.login(username='teacher1', password='pass')

        url = f"/api/get_my_courses/{self.teacher1.id}/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        c = content['data'][0]
        self.assertEqual(self.course.id, c['id'])
        self.assertEqual(self.course.published, c['published'])
        self.assertEqual(self.course.component.code, c['component'])
        self.assertEqual(self.course.training.label, c['training_label'])
        self.assertEqual(self.course.label, c['label'])
        # teachers
        self.assertEqual(self.course.slots_count(teacher_id=self.teacher1.id), c['slots_count'])
        self.assertEqual(self.course.free_seats(teacher_id=self.teacher1.id), c['n_places'])
        self.assertEqual(
            self.course.published_slots_count(teacher_id=self.teacher1.id),
            c['published_slots_count']
        )
        self.assertEqual(0, c['alerts_count'])

    def test_API_ajax_get_my_slots(self):
        request.user = self.teacher1
        client = Client()
        client.login(username='teacher1', password='pass')

        url = f"/api/get_my_slots/{self.teacher1.id}/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.slot.id, s['id'])
        self.assertEqual(self.slot.published, s['published'])
        self.assertEqual(self.slot.course.component.code, s['component'])
        self.assertEqual(
            f'{self.slot.course.training.label} ({self.slot.course_type.label})',
            s['training_label']
        )
        self.assertEqual(
            f'{self.slot.course.training.label} ({self.slot.course_type.full_label})',
            s['training_label_full']
        )
        self.assertIsInstance(s['location'], dict)
        self.assertEqual(
            f'{self.slot.campus.label} - {self.slot.building.label}',
            s['location']['campus']
        )
        self.assertEqual(self.slot.room, s['location']['room'])

        sch = s['schedules']
        self.assertIsInstance(sch, dict)
        self.assertEqual(
            _date(self.slot.date, 'l d/m/Y'),
            sch['date']
        )
        self.assertEqual(
            f'{self.slot.start_time.strftime("%H:%M")} - {self.slot.end_time.strftime("%H:%M")}',
            sch['time']
        )
        # self.assertEqual(
        #     datetime.strptime(
        #         "%s:%s:%s %s:%s"
        #         % (self.slot.date.year, self.slot.date.month, self.slot.date.day, self.slot.start_time.hour, self.slot.start_time.minute,),
        #         "%Y:%m:%d %H:%M",
        #     ),
        #     s['datetime']
        # )
        # TODO: fix
        self.assertEqual(self.slot.start_time.strftime("%H:%M"), s['start_time'])
        self.assertEqual(self.slot.end_time.strftime("%H:%M"), s['end_time'])
        self.assertEqual(self.slot.course.label, s['label'])
        # TODO: teachers
        self.assertEqual(self.slot.n_places, s['n_places'])
        capa = s['registered_students_count']
        self.assertIsInstance(capa, dict)
        self.assertEqual(self.slot.n_places, capa['capacity'])
        self.assertEqual(self.slot.registered_students(), capa['students_count'])
        self.assertEqual(self.slot.additional_information, s['additional_information'])

    def test_API_ajax_get_my_slots_all__past(self):
        self.slot.date = self.today - timedelta(days=10)
        self.slot.save()
        request.user = self.teacher1
        client = Client()
        client.login(username='teacher1', password='pass')

        url = f"/api/get_my_slots/all/{self.teacher1.id}/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.slot.id, s['id'])

    def test_API_ajax_get_my_slots_all__no_immersions(self):
        self.slot.date = self.today - timedelta(days=10)
        self.slot.save()
        self.immersion.delete()
        self.immersion2.delete()
        request.user = self.teacher1
        client = Client()
        client.login(username='teacher1', password='pass')

        url = f"/api/get_my_slots/all/{self.teacher1.id}/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertIsInstance(content, dict)
        self.assertIn('msg', content)
        self.assertIn('data', content)
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)

    def test_API_ajax_get_agreed_highschools(self):
        request.user = self.scuio_user

        url = f"/api/get_agreed_highschools"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        self.assertIsInstance(content['data'][0], list)
        self.assertIsInstance(content['data'][0][0], dict)
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


    def test_API_ajax_get_immersions__no_user(self):
        request.user = self.scuio_user
        self.immersion.delete()
        self.immersion2.delete()
        url = f"/api/get_immersions/0"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content['msg']), 0)
        self.assertIsInstance(content['data'], list)

    def test_API_ajax_get_immersions__wrong_user(self):
        request.user = self.student
        client = Client()
        client.login(username='student', password='pass')

        url = f"/api/get_immersions/{self.teacher1.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())
        self.assertGreater(len(content['msg']), 0)
        self.assertIsInstance(content['data'], list)

    def test_API_ajax_get_immersions__user_not_found(self):
        request.user = self.scuio_user

        url = f"/api/get_immersions/999"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)

        content = json.loads(response.content.decode())

        self.assertEqual(content['data'], [])
        self.assertIsInstance(content['msg'], str)
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_get_immersions__future(self):
        request.user = self.scuio_user
        self.slot.date = self.today + timedelta(days=2)
        self.slot.save()
        url = f"/api/get_immersions/{self.highschool_user.id}/future"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)

        content = json.loads(response.content.decode())

        self.assertIsInstance(content['data'], list)
        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertIsInstance(i, dict)
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


    def test_API_ajax_get_immersions__past(self):
        request.user = self.scuio_user
        self.slot.date = self.today - timedelta(days=2)
        self.slot.save()
        url = f"/api/get_immersions/{self.highschool_user.id}/past"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)

        content = json.loads(response.content.decode())

        self.assertIsInstance(content['data'], list)
        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertIsInstance(i, dict)
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

    def test_API_ajax_get_immersions__cancelled(self):
        request.user = self.scuio_user
        self.slot.date = self.today - timedelta(days=2)
        self.slot.save()
        self.immersion.cancellation_type=self.cancel_type
        self.immersion.save()
        url = f"/api/get_immersions/{self.highschool_user.id}/cancelled"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)

        content = json.loads(response.content.decode())

        self.assertIsInstance(content['data'], list)
        self.assertEqual(content['msg'], '')
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertIsInstance(i, dict)
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
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        i = content['data'][0]
        self.assertIsInstance(i, dict)
        self.assertEqual(
            i['name'],
            f'{self.highschool_user.last_name} {self.highschool_user.first_name}'
        )
        self.assertEqual(i['email'], self.highschool_user.email)

    def test_API_ajax_get_slot_registrations(self):
        request.user = self.scuio_user

        url = f"/api/get_slot_registrations/{self.slot.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 2)
        hs = content['data'][0]
        self.assertIsInstance(hs, dict)
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
        self.assertEqual(stu['school'], self.student_record.home_institution)
        self.assertEqual(stu['city'], '')

    def test_API_ajax_get_available_students(self):
        request.user = self.scuio_user

        self.hs_record.validation = 2
        self.hs_record.save()
        self.hs_record2.validation = 2
        self.hs_record2.save()

        url = f"/api/get_available_students/%s" % self.slot.id
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 2)
        stu = content['data'][0]
        hs = content['data'][1]

        self.assertEqual(self.student2.id, stu['id'])
        self.assertEqual(self.student2.first_name, stu['firstname'])
        self.assertEqual(self.student2.last_name, stu['lastname'])
        self.assertEqual(pgettext('person type', 'Student'), stu['profile'])
        self.assertEqual(self.student_record2.home_institution, stu['school'])
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

    def test_API_ajax_get_highschool_students__no_record(self):
        request.user = self.scuio_user

        url = f"/api/get_highschool_students/no_record"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
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

    def test_API_ajax_get_highschool_students__no_highschool(self):
        self.lyc_ref.highschool = None
        self.lyc_ref.save()
        request.user = self.lyc_ref
        client = Client()
        client.login(username='lycref', password='pass')

        url = f"/api/get_highschool_students/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content['msg']), 0)
        self.assertEqual(content['data'], [])

    def test_API_ajax_get_highschool_students(self):
        request.user = self.lyc_ref
        client = Client()
        client.login(username='lycref', password='pass')

        url = f"/api/get_highschool_students/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 2)

    def test_API_ajax_get_highschool_students__student(self):
        self.hs_record.level = 3
        self.hs_record.origin_bachelor_type = 1
        self.hs_record.post_bachelor_level = 1
        self.hs_record.save()
        request.user = self.lyc_ref
        client = Client()
        client.login(username='lycref', password='pass')

        url = f"/api/get_highschool_students/"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertEqual(len(content['data']), 2)

        one = False
        for h in content['data']:
            if h['level'] == HighSchoolStudentRecord.LEVELS[2][1]:
                self.assertEqual(self.hs_record.get_post_bachelor_level_display(), h['post_bachelor_level'])
                self.assertEqual(self.hs_record.get_origin_bachelor_type_display(), h['bachelor'])
                one = True
                break
        self.assertTrue(one)

    def test_API_ajax_check_date_between_vacation__no_date(self):
        request.user = self.scuio_user

        url = f"/api/check_vacations"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content['msg']), 0)
        self.assertEqual(content['data'], {})

    def test_API_ajax_check_date_between_vacation__date_format_failure(self):
        request.user = self.scuio_user

        url = f"/api/check_vacations?date=failure"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertGreater(len(content['msg']), 0)
        self.assertEqual(content['data'], {})

    def test_API_ajax_check_date_between_vacation__dmY_format(self):
        request.user = self.scuio_user

        url = f"/api/check_vacations?date=01/01/2010"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], dict)
        self.assertIn('is_between', content['data'])
        self.assertIsInstance(content['data']['is_between'], bool)
        self.assertEqual(content['data']['is_between'], False)

    def test_API_ajax_check_date_between_vacation__Ymd_format(self):
        request.user = self.scuio_user
        d = self.today
        if d.weekday() == 6:
            d = self.today + timedelta(days=1)
        dd = _date(d, 'Y/m/d')
        url = f"/api/check_vacations?date={dd}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], dict)
        self.assertIn('is_between', content['data'])
        self.assertIsInstance(content['data']['is_between'], bool)
        self.assertEqual(content['data']['is_between'], True)



    def test_API_ajax_get_slots_by_course(self):
        request.user = self.scuio_user
        url = f"/api/get_slots_by_course/{self.slot.course.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        s = content['data'][0]
        self.assertEqual(self.slot.id, s['id'])
        self.assertEqual(self.slot.published, s['published'])
        self.assertEqual(self.slot.course.label, s['course_label'])
        self.assertEqual(self.slot.course_type.label, s['course_type'])
        self.assertEqual(self.slot.course_type.full_label, s['course_type_full'])
        self.assertEqual(_date(self.slot.date, 'l j F Y'), s['date'])
        self.assertEqual(
            f'{self.slot.start_time.strftime("%Hh%M")} - {self.slot.end_time.strftime("%Hh%M")}',
            s['time']
        )
        self.assertEqual(f'{self.slot.building.label} - {self.slot.campus.label}', s['building'])
        self.assertEqual(self.slot.room, s['room'])
        self.assertEqual(
            ', '.join([f'{t.first_name} {t.last_name.upper()}' for t in self.slot.teachers.all()]),
            s['teachers']
        )
        self.assertEqual(self.slot.registered_students(), s['n_register'])
        self.assertEqual(self.slot.n_places, s['n_places'])
        self.assertEqual(self.slot.additional_information, s['additional_information'])


    def test_API_ajax_get_slots_by_course__semester(self):
        self.calendar.calendar_mode = "SEMESTER"
        self.calendar.semester1_start_date = self.today - timedelta(days=10)
        self.calendar.semester1_end_date = self.today + timedelta(days=10)
        self.calendar.save()

        request.user = self.scuio_user
        url = f"/api/get_slots_by_course/{self.slot.course.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')

    def test_API_ajax_get_slots_by_course__semester_2(self):
        self.calendar.calendar_mode = "SEMESTER"
        self.calendar.semester1_start_date = self.today - timedelta(days=10)
        self.calendar.semester1_end_date = self.today - timedelta(days=9)
        self.calendar.semester2_start_date = self.today - timedelta(days=8)
        self.calendar.semester2_end_date = self.today + timedelta(days=10)
        self.calendar.save()

        request.user = self.scuio_user
        url = f"/api/get_slots_by_course/{self.slot.course.id}"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')


    def test_API_ajax_delete_account__not_student_id(self):
        request.user = self.scuio_user
        url = "/api/delete_account"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_delete_account__wrong_user_group(self):
        request.user = self.scuio_user
        url = "/api/delete_account"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_id': self.ref_comp.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_delete_account(self):
        request.user = self.scuio_user
        url = "/api/delete_account"
        uid = self.highschool_user.id
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'student_id': self.highschool_user.id, 'send_email': 'true'}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertFalse(content['error'])
        self.assertGreater(len(content['msg']), 0)
        with self.assertRaises(ImmersionUser.DoesNotExist):
            ImmersionUser.objects.get(pk=uid)

    def test_API_ajax_cancel_registration__no_post_param(self):
        request.user = self.scuio_user
        url = "/api/cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_cancel_registration__bad_user_id(self):
        request.user = self.scuio_user
        url = "/api/cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': 0, 'reason_id': 1}
        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_cancel_registration__bad_reason_id(self):
        request.user = self.scuio_user
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        url = "/api/cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': self.highschool_user.id, 'reason_id': 0}
        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_cancel_registration__past_immersion(self):
        request.user = self.scuio_user
        self.slot.date = self.today - timedelta(days=1)
        self.slot.save()
        url = "/api/cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': self.highschool_user.id, 'reason_id': 0}
        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_cancel_registration(self):
        request.user = self.scuio_user
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        self.assertIsNone(self.immersion.cancellation_type)
        url = "/api/cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': self.immersion.id, 'reason_id': self.cancel_type.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertFalse(content['error'])
        self.assertGreater(len(content['msg']), 0)
        i = Immersion.objects.get(pk=self.immersion.id)
        self.assertEqual(i.cancellation_type.id, self.cancel_type.id)

    def test_API_ajax_set_attendance(self):
        request.user = self.scuio_user
        url = "/api/set_attendance"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertGreater(len(content['error']), 0)

    def test_API_ajax_set_attendance__no_attendance_status(self):
        request.user = self.scuio_user
        url = "/api/set_attendance"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': self.immersion.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertGreater(len(content['error']), 0)

    def test_API_ajax_set_attendance__immersion_id(self):
        self.assertEqual(self.immersion.attendance_status, 0)

        request.user = self.scuio_user
        url = "/api/set_attendance"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_id': self.immersion.id, 'attendance_value': 1}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], '')
        self.assertGreater(len(content['msg']), 0)

        i = Immersion.objects.get(pk=self.immersion.id)
        self.assertEqual(i.attendance_status, 1)

    def test_API_ajax_set_attendance__immersion_idx(self):
        self.assertEqual(self.immersion.attendance_status, 0)
        self.assertEqual(self.immersion2.attendance_status, 0)

        request.user = self.scuio_user
        url = "/api/set_attendance"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data_immersion = json.dumps([self.immersion.id, self.immersion2.id])
        data = {'immersion_ids': data_immersion, 'attendance_value': 1}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['success'], '')
        self.assertEqual(content['error'], '')
        self.assertGreater(len(content['msg']), 0)

        i = Immersion.objects.get(pk=self.immersion.id)
        self.assertEqual(i.attendance_status, 1)
        i = Immersion.objects.get(pk=self.immersion2.id)
        self.assertEqual(i.attendance_status, 1)

    def test_API_ajax_set_attendance__wrong_immersion_id(self):
        request.user = self.scuio_user
        url = "/api/set_attendance"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_ids': 0, 'attendance_value': 1}
        content = json.loads(self.client.post(url, data, **header).content.decode())


        self.assertEqual(content['success'], '')
        self.assertGreater(len(content['error']), 0)

    def test_API_ajax_get_alerts(self):
        request.user = self.student
        client = Client()
        client.login(username='student', password='pass')

        url = "/api/get_alerts"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = client.get(url, request, **header)
        content = json.loads(response.content.decode())

        self.assertEqual(content['msg'], '')
        self.assertIsInstance(content['data'], list)
        self.assertGreater(len(content['data']), 0)
        a = content['data'][0]
        self.assertIsInstance(a, dict)
        self.assertEqual(self.alert.id, a['id'])
        self.assertEqual(self.alert.course.label, a['course'])
        self.assertEqual(self.alert.course.training.label, a['training'])
        self.assertEqual([s.label for s in self.alert.course.training.training_subdomains.all()], a['subdomains'])
        self.assertEqual([s.training_domain.label for s in self.alert.course.training.training_subdomains.all()], a['domains'])
        self.assertEqual(self.alert.email_sent, a['email_sent'])



    def test_API_ajax_send_email__no_params(self):
        request.user = self.scuio_user
        url = "/api/send_email"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_send_email(self):
        request.user = self.scuio_user
        url = "/api/send_email"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'slot_id': self.slot.id, 'send_copy': 'true', 'subject': 'hello',
                'body': 'Hello world'}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertFalse(content['error'])
        self.assertEqual(len(content['msg']), 0)

    def test_API_ajax_batch_cancel_registration__no_param(self):
        request.user = self.scuio_user
        url = "/api/batch_cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_batch_cancel_registration__invalid_json_param(self):
        request.user = self.scuio_user
        url = "/api/batch_cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_ids': 'hello world', 'reason_id': self.cancel_type.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_batch_cancel_registration__past_immersion(self):
        request.user = self.scuio_user
        url = "/api/batch_cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_ids': f'[{self.immersion.id}]', 'reason_id': self.cancel_type.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_batch_cancel_registration(self):
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        request.user = self.scuio_user
        url = "/api/batch_cancel_registration"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'immersion_ids': json.dumps([self.immersion.id]), 'reason_id': self.cancel_type.id}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertFalse(content['error'])
        self.assertGreater(len(content['msg']), 0)
        self.assertIsNone(content['err_msg'])

    def test_API_ajax_send_email_us__no_param(self):
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        request.user = self.scuio_user
        url = "/api/send_email_contact_us"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_send_email_us__no_general_settings(self):
        GeneralSettings.objects.get(setting='MAIL_CONTACT_SCUIO_IP').delete()
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        request.user = self.scuio_user
        url = "/api/send_email_contact_us"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_send_email_us(self):
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        request.user = self.scuio_user
        url = "/api/send_email_contact_us"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {
            'subject': 'Unittest',
            'body': 'Hello world',
            'lastname': 'Hello',
            'firstname': 'World',
            'email': 'unittest@unittest.fr',
            'notify_user': True,
        }

        content = json.loads(self.client.post(url, data, **header).content.decode())
        self.assertFalse(content['error'])

    def test_API_ajax_get_students_presence(self):
        self.slot.date = self.today + timedelta(days=1)
        self.slot.save()
        request.user = self.scuio_user
        url = "/api/get_students_presence"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {}
        content = json.loads(self.client.post(url, data, **header).content.decode())

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

    def test_API_ajax_set_course_alert__wrong_course_id(self):
        request.user = self.scuio_user
        url = "/api/set_course_alert"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': 0}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertGreater(len(content['msg']), 0)
        self.assertTrue(content['error'])

        print(content)

    def test_API_ajax_set_course_alert__email_not_valid(self):
        request.user = self.scuio_user
        url = "/api/set_course_alert"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id, 'email': 'wrong_email_address'}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertGreater(len(content['msg']), 0)
        self.assertTrue(content['error'])

    def test_API_ajax_set_course_alert__no_alert(self):
        self.alert.delete()
        request.user = self.scuio_user
        url = "/api/set_course_alert"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id, 'email': 'a@unittest.fr'}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertFalse(content['error'])
        self.assertGreater(len(content['msg']), 0)

        raises = False
        try:
            UserCourseAlert.objects.get(course_id=data['course_id'], email=data['email'])
        except UserCourseAlert.DoesNotExist:
            raises = True
        self.assertFalse(raises)

    def test_API_ajax_set_course_alert__alert_but_not_send(self):
        request.user = self.scuio_user
        url = "/api/set_course_alert"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id, 'email': self.student.email}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertTrue(content['error'])
        self.assertGreater(len(content['msg']), 0)

    def test_API_ajax_set_course_alert__alert_sent(self):
        self.alert.email_sent = True
        self.alert.save()
        request.user = self.scuio_user
        url = "/api/set_course_alert"
        header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        data = {'course_id': self.course.id, 'email': self.student.email}
        content = json.loads(self.client.post(url, data, **header).content.decode())

        self.assertEqual(content['data'], [])
        self.assertFalse(content['error'])
        self.assertGreater(len(content['msg']), 0)
