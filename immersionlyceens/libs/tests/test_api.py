"""
Django API tests suite
"""
import json
import unittest
from datetime import datetime, time
from django.template.defaultfilters import date as _date

from django.conf import settings
from compat.templatetags.compat import url
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from immersionlyceens.apps.core.models import (AccompanyingDocument, Component, TrainingDomain,
                                               TrainingSubdomain, Training, Course, Campus,
                                               Building, Slot, CourseType, HighSchool)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord
from immersionlyceens.libs.api.views import ajax_check_course_publication

request_factory = RequestFactory()
request = request_factory.get('/admin')

class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group']

    def setUp(self):
        self.scuio_user = get_user_model().objects.create_user(
            username='scuio',
            password='pass',
            email='immersion@no-reply.com',
            first_name='scuio',
            last_name='scuio',
        )
        self.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
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

        self.client = Client()
        self.client.login(username='scuio', password='pass')

        Group.objects.get(name='SCUIO-IP').user_set.add(self.scuio_user)
        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_comp)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)

        self.today = datetime.today()
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
            course=self.course, course_type=self.course_type, campus=self.campus,
            building=self.building, room='room 1', date=self.today,
            start_time=time(12, 0), end_time=time(14, 0), n_places=20
        )
        self.slot.teachers.add(self.teacher1),
        self.high_school = HighSchool.objects.create(label='HS1', address='here',
                         department=67, city='STRASBOURG', zip_code=67000, phone_number='0123456789',
                         email='a@b.c', head_teacher_name='M. A B', referent_name='my name',
                         referent_phone_number='0123456789', referent_email='a@b.c')
        self.hs_record = HighSchoolStudentRecord.objects.create(student=self.highschool_user,
                        highschool=self.high_school, birth_date=datetime.today(), civility=1,
                        phone='0123456789', level=1, class_name='1ere S 3',
                        bachelor_type=3, professional_bachelor_mention='My spe')
        self.lyc_ref.highschool = self.high_school
        self.lyc_ref.save()


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
        self.assertEqual(len(content['data']), 1)
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
        self.assertEqual(slot['n_register'], 10)  # TODO:
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
        self.assertEqual(len(content['data']), 1)
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
        self.assertEqual(slot['n_register'], 10)  # TODO:
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
        self.assertEqual(len(content['data']), 1)
        hs_record = content['data'][0]
        self.assertEqual(hs_record['id'], self.hs_record.id)
        self.assertEqual(hs_record['first_name'], self.hs_record.student.first_name)
        self.assertEqual(hs_record['last_name'], self.hs_record.student.last_name)
        self.assertEqual(hs_record['level'], self.hs_record.level)
        self.assertEqual(hs_record['class_name'], self.hs_record.class_name)

    def test_API_get_student_records__VALIDATED(self):
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