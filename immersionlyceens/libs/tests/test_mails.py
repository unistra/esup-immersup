"""
Mails tests
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils.formats import date_format
from django.test import Client, RequestFactory, TestCase
from django.conf import settings
from django.contrib.auth.models import Group

from immersionlyceens.libs.utils import get_general_setting
from ..mails.variables_parser import parser

from immersionlyceens.apps.core.models import (
    UniversityYear, MailTemplate, Component, Slot, Course, TrainingDomain, TrainingSubdomain, Campus,
    Building, CourseType, Training, Calendar, Vacation, HighSchool, Immersion, EvaluationFormLink, EvaluationType,
    CancelType
)

from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

class APITestCase(TestCase):
    """Tests for API"""

    fixtures = ['group', 'generalsettings', 'mailtemplate', 'mailtemplatevars', 'evaluationtype', 'canceltype']

    def setUp(self):
        self.today = datetime.datetime.today()

        self.highschool_user = get_user_model().objects.create_user(
            username='the_username', password='pass', email='hs@no-reply.com', first_name='Jean', last_name='MICHEL',
        )

        self.highschool_user.set_validation_string()
        self.highschool_user.destruction_date = self.today.date() + datetime.timedelta(days=settings.DESTRUCTION_DELAY)
        self.highschool_user.save()

        self.teacher1 = get_user_model().objects.create_user(
            username='teacher1',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='teach',
            last_name='HER',
        )

        self.ref_comp = get_user_model().objects.create_user(
            username='refcomp',
            password='pass',
            email='refcomp@no-reply.com',
            first_name='refcomp',
            last_name='refcomp',
        )

        self.lyc_ref = get_user_model().objects.create_user(
            username='lycref',
            password='pass',
            email='teacher-immersion@no-reply.com',
            first_name='lyc',
            last_name='REF',
        )

        self.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=self.today.date() + datetime.timedelta(days=1),
            end_date=self.today.date() + datetime.timedelta(days=10),
            registration_start_date=self.today.date() + datetime.timedelta(days=1),
            active=True,
        )

        Group.objects.get(name='ENS-CH').user_set.add(self.teacher1)
        Group.objects.get(name='LYC').user_set.add(self.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(self.lyc_ref)
        Group.objects.get(name='REF-CMP').user_set.add(self.ref_comp)

        self.calendar = Calendar.objects.create(
            calendar_mode=Calendar.CALENDAR_MODE[0][0],
            year_start_date=self.today - datetime.timedelta(days=10),
            year_end_date=self.today + datetime.timedelta(days=10),
            year_nb_authorized_immersion=4,
            year_registration_start_date=self.today - datetime.timedelta(days=9)
        )
        self.vac = Vacation.objects.create(
            label="vac",
            start_date=self.today - datetime.timedelta(days=2),
            end_date=self.today + datetime.timedelta(days=2)
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
        self.course_type = CourseType.objects.create(label='CM', full_label='Cours magistral')
        self.slot = Slot.objects.create(
            course=self.course,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 1',
            date=self.today,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
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
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
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
            convention_start_date=self.today - datetime.timedelta(days=10),
            convention_end_date=self.today + datetime.timedelta(days=10),
        )
        self.lyc_ref.highschool = self.high_school
        self.lyc_ref.save()

        self.hs_record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date=datetime.datetime.today(),
            civility=1,
            phone='0123456789',
            level=1,
            class_name='1ere S 3',
            bachelor_type=3,
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
            validation=1,
        )

        self.immersion = Immersion.objects.create(
            student=self.highschool_user,
            slot=self.slot,
        )

        self.slot_eval_type = EvaluationType.objects.get(code='EVA_CRENEAU')
        self.global_eval_type = EvaluationType.objects.get(code='EVA_DISPOSITIF')

        self.slot_eval_link = EvaluationFormLink.objects.create(
            evaluation_type=self.slot_eval_type, active=True, url='http://slot.evaluation.test/')
        self.global_eval_link = EvaluationFormLink.objects.create(
            evaluation_type=self.global_eval_type, active=True, url='http://disp.evaluation.test/')

    def test_variables(self):
        # user : ${prenom} ${nom} ${jourDestructionCptMin} ${lienValidation} ${identifiant}
        # university year : ${annee}

        message_body = MailTemplate.objects.get(code='CPT_MIN_CREATE_LYCEEN')
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
        message_body = MailTemplate.objects.get(code='IMMERSION_RAPPEL_ENS')
        parsed_body = parser(message_body.body, user=self.teacher1, slot=self.slot)
        self.assertIn(self.teacher1.first_name, parsed_body)
        self.assertIn(self.teacher1.last_name, parsed_body)
        self.assertIn(self.highschool_user.first_name, parsed_body)
        self.assertIn(self.highschool_user.last_name, parsed_body)

        # Slots : slot list
        message_body = MailTemplate.objects.get(code='RAPPEL_COMPOSANTE')
        parsed_body = parser(message_body.body, user=self.ref_comp, slot_list=[self.slot])
        self.assertIn(self.slot.course.label, parsed_body)
        self.assertIn(self.slot.course_type.label, parsed_body)
        self.assertIn(self.slot.building.label, parsed_body)
        self.assertIn(self.slot.room, parsed_body)
        self.assertIn(self.teacher1.last_name, parsed_body)

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
        self.assertIn(self.teacher1.last_name, parsed_body)

        # highschool
        message_body = MailTemplate.objects.get(code='CPT_AVALIDER_LYCEE')
        parsed_body = parser(message_body.body, user=self.lyc_ref, slot=self.slot)

        self.assertIn(self.lyc_ref.first_name, parsed_body)
        self.assertIn(self.lyc_ref.last_name, parsed_body)
        self.assertIn(self.high_school.label, parsed_body)
        self.assertIn(get_general_setting("PLATFORM_URL"), parsed_body)

        # high school referent account creation : check recovery string
        self.lyc_ref.set_recovery_string()
        message_body = MailTemplate.objects.get(code='CPT_CREATE_LYCEE')
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

        """
        ${cours.nbplaceslibre}
        ${creneau.composante}
        """