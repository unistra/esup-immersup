"""
Core commands tests
"""
import datetime
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail, management
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from immersionlyceens.apps.core.models import (
    AttestationDocument, BachelorType, Building, Campus, CancelType, Course,
    CourseType, Establishment, EvaluationFormLink, EvaluationType,
    GeneralSettings, HigherEducationInstitution, HighSchool, HighSchoolLevel,
    Immersion, MailTemplate, PendingUserGroup, Period, PostBachelorLevel,
    Profile, RefStructuresNotificationsSettings, ScheduledTask,
    ScheduledTaskLog, Slot, Structure, StudentLevel, Training, TrainingDomain,
    TrainingSubdomain, UniversityYear, UserCourseAlert, Vacation)
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument)
from immersionlyceens.libs.mails.variables_parser import parser
from immersionlyceens.libs.utils import get_general_setting


class CommandsTestCase(TestCase):
    """
    Core app Management Commands tests
    """

    fixtures = ['group', 'evaluationtype', 'canceltype', 'high_school_levels', 'post_bachelor_levels',
                'student_levels', 'higher']

    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.today = timezone.localdate()

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
        cls.highschool_user.destruction_date = cls.today + datetime.timedelta(days=settings.DESTRUCTION_DELAY)
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
            start_date=cls.today + datetime.timedelta(days=1),
            end_date=cls.today + datetime.timedelta(days=10),
            registration_start_date=cls.today + datetime.timedelta(days=1),
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
        cls.structure = Structure.objects.create(label="test structure")
        cls.t_domain = TrainingDomain.objects.create(label="test t_domain")
        cls.t_sub_domain = TrainingSubdomain.objects.create(label="test t_sub_domain", training_domain=cls.t_domain)
        cls.training = Training.objects.create(label="test training")
        cls.training2 = Training.objects.create(label="test training 2")
        cls.training.training_subdomains.add(cls.t_sub_domain)
        cls.training2.training_subdomains.add(cls.t_sub_domain)
        cls.training.structures.add(cls.structure)
        cls.training2.structures.add(cls.structure)
        cls.course = Course.objects.create(label="course 1", training=cls.training, structure=cls.structure)
        cls.course2 = Course.objects.create(label="course 2", training=cls.training, structure=cls.structure)
        cls.course.speakers.add(cls.speaker1)
        cls.campus = Campus.objects.create(label='Esplanade')
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM', full_label='Cours magistral')
        cls.slot = Slot.objects.create(
            course=cls.course,
            course_type=cls.course_type,
            campus=cls.campus,
            building=cls.building,
            room='room 1',
            date=cls.today,
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
            date=cls.today + datetime.timedelta(days=2),
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        cls.slot3 = Slot.objects.create(
            course=cls.course,
            course_type=cls.course_type,
            campus=cls.campus,
            building=cls.building,
            room='room 2',
            date=cls.today + datetime.timedelta(days=35),
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=20,
            additional_information="Hello there!"
        )
        # slot used for course alert
        cls.slot4 = Slot.objects.create(
            course=cls.course2,
            course_type=cls.course_type,
            campus=cls.campus,
            building=cls.building,
            room='room 2',
            date=cls.today + datetime.timedelta(days=35),
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=1,
            additional_information="Hello there!"
        )
        cls.slot.speakers.add(cls.speaker1),
        cls.slot2.speakers.add(cls.speaker1),
        cls.slot3.speakers.add(cls.speaker1),
        cls.hs_record = HighSchoolStudentRecord.objects.create(
            student=cls.highschool_user,
            highschool=cls.high_school,
            birth_date=cls.today,
            phone='0123456789',
            level=HighSchoolLevel.objects.get(pk=1),
            class_name='1ere S 3',
            bachelor_type=BachelorType.objects.get(label__iexact='professionnel'),
            professional_bachelor_mention='My spe',
            visible_immersion_registrations=True,
            visible_email=True,
            validation=1,
        )

        # Today
        cls.immersion = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot,
        )
        # Immersion in 2 days
        cls.immersion2 = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot2,
        )

        # in 35 days (beyond the auto-cancellation delay)
        cls.immersion3 = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot3,
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

        cls.attestation_2.profiles.add(Profile.objects.get(code='LYC_W_CONV'))
        cls.attestation_2.profiles.add(Profile.objects.get(code='VIS'))

        # This attestation expires in 5 days
        cls.hs_record_document = HighSchoolStudentRecordDocument.objects.create(
            record=cls.hs_record,
            attestation=cls.attestation_1,
            mandatory=True,
            for_minors=False,
            requires_validity_date=True,
            validity_date=cls.today + datetime.timedelta(days=5)
        )

        # This one doesn't
        cls.hs_record_document2 = HighSchoolStudentRecordDocument.objects.create(
            record=cls.hs_record,
            attestation=cls.attestation_2,
            mandatory=True,
            for_minors=False,
            requires_validity_date=True,
            validity_date=cls.today + datetime.timedelta(days=300)
        )


    def test_send_attestation_expiration_warning(self):
        """
        Test attestation expiration warning message
        """
        expiration_delay = GeneralSettings.get_setting("ATTESTATION_DOCUMENT_DEPOSIT_DELAY")
        expiration_date = self.today + datetime.timedelta(days=expiration_delay)

        # Check statuses before command
        for attestation in self.hs_record.attestation.all():
            self.assertFalse(attestation.renewal_email_sent)

        # Send the reminders
        management.call_command("send_attestation_expiration_warning", verbosity=0)
        self.assertEqual(len(mail.outbox), 1)

        # Check new statuses
        for attestation in self.hs_record.attestation.all():
            if attestation.validity_date <= expiration_date:
                self.assertTrue(attestation.renewal_email_sent)
            else:
                self.assertFalse(attestation.renewal_email_sent)

    def test_auto_immersion_cancellation(self):
        """
        Test immersion cancellation when attestations are out of date
        """
        # 3 active immersions, none cancelled
        self.assertEqual(
            Immersion.objects.filter(student=self.highschool_user, cancellation_type__isnull=True).count(),
            3
        )
        self.assertFalse(
            Immersion.objects.filter(student=self.highschool_user, cancellation_type__isnull=False).exists()
        )

        # manually expires student attestations and run the command
        self.hs_record.attestation.all().update(validity_date=self.today - datetime.timedelta(days=3))

        management.call_command("auto_immersion_cancellation", verbosity=0)

        # Result : 2 cancelled immersions, 1 remains active (beyond the cancellation delay)
        self.assertEqual(
            Immersion.objects.filter(student=self.highschool_user, cancellation_type__code="ATT").count(),
            2
        )
        self.assertEqual(
            Immersion.objects.filter(student=self.highschool_user, cancellation_type__isnull=True).count(),
            1
        )

        # 2 Cancellation email sent
        self.assertEqual(len(mail.outbox), 2)

    def test_send_course_alerts(self):
        """
        Test course alerts
        """
        self.assertEqual(len(mail.outbox), 0)

        alert = UserCourseAlert.objects.create(
            email='anything@domain.tld',
            email_sent=False,
            course=self.course2
        )

        management.call_command("send_course_alerts", verbosity=0)

        alert.refresh_from_db()

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(alert.email_sent)

        # Reset the alert, change slot4 registration_limit_delay and call again
        alert.email_sent = False
        alert.save()
        self.slot4.registration_limit_delay = 36*24 # limit date = yesterday ... to late for the alert
        self.slot4.save()
        management.call_command("send_course_alerts", verbosity=0)
        self.assertEqual(len(mail.outbox), 1) # no change
        self.assertFalse(alert.email_sent) # not sent

        # Reset the alert and the delay, add an immersion on slot 4 (=> remaining seats = 0) and retry
        alert.email_sent = False
        alert.save()
        self.slot4.registration_limit_delay = 0
        self.slot4.save()
        Immersion.objects.create(slot=self.slot4, student=self.highschool_user)
        management.call_command("send_course_alerts", verbosity=0)

        alert.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1) # no change
        self.assertFalse(alert.email_sent) # not sent


    def test_cron_master(self):
        """
        Test Scheduled tasks
        """
        devnull = open("/dev/null", 'w+')

        today = datetime.date.today()

        self.assertFalse(ScheduledTaskLog.objects.exists())

        # Inactive task
        task = ScheduledTask.objects.create(
            command_name='crontest',
            description='whatever',
            active=False,
            date=None,
            time=datetime.time(14, 0),
            frequency=None
        )
        management.call_command("cron_master", time="1400", stdout=devnull)
        self.assertFalse(ScheduledTaskLog.objects.exists())

        # Active task but no selected days : still nothing
        task.active=True
        task.save()

        management.call_command("cron_master", time="1400", stdout=devnull)
        self.assertFalse(ScheduledTaskLog.objects.exists())

        # =========================================
        # With a specific date (tomorrow)
        # =========================================
        task.date = datetime.date.today() + datetime.timedelta(days=1)
        task.save()

        # Not today :
        management.call_command(
            "cron_master",
            date=f"{str(today.month).zfill(2)}{str(today.day).zfill(2)}",
            time="1400",
            stdout=devnull
        )
        self.assertFalse(ScheduledTaskLog.objects.exists())

        # Tomorrow : success
        management.call_command(
            "cron_master",
            date=f"{str(task.date.month).zfill(2)}{str(task.date.day).zfill(2)}",
            time="1400",
            stdout=devnull
        )

        self.assertEqual(
            ScheduledTaskLog.objects.filter(task=task, success=True, message="Cron test success").count(),
            1
        )

        # =========================================
        # With a day of the week
        # =========================================
        # First remove the previous date
        task.date = None

        week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        current_day = week_days[datetime.date.today().weekday()]

        setattr(task, current_day, True)
        task.save()

        management.call_command("cron_master", time="1400", stdout=devnull)
        self.assertEqual(
            ScheduledTaskLog.objects.filter(task=task, success=True, message="Cron test success").count(),
            2
        )

        # =========================================
        # With a frequency
        # =========================================
        # clean logs
        ScheduledTaskLog.objects.all().delete()
        task.frequency = 2 # every 2 hours
        task.save()

        # Won't run before 'time' (14h00)
        management.call_command("cron_master", time="1200", stdout=devnull)
        self.assertFalse(ScheduledTaskLog.objects.exists())

        # Will still run at 1400
        management.call_command("cron_master", time="1400", stdout=devnull)
        self.assertEqual(
            ScheduledTaskLog.objects.filter(task=task, success=True, message="Cron test success").count(),
            1
        )

        ScheduledTaskLog.objects.all().delete()

        # and 5 more times, at 14h00, 16h00, 18h00, 20h00, 22h00:
        for h in range(14, 23, 2):
            management.call_command("cron_master", time=f"{h}00", stdout=devnull)

        self.assertEqual(
            ScheduledTaskLog.objects.filter(task=task, success=True, message="Cron test success").count(),
            5
        )


    def test_send_speakers_and_structures_managers_slot_reminder(self):
        """ Tests send_speaker_slot_reminder & send_slot_reminder_on_closed_registrations"""    
        
        self.slot.published = False
        self.slot2.published = False
        self.slot3.published = False
        self.slot4.published = False
        self.slot.save()
        self.slot2.save()
        self.slot3.save()
        self.slot4.save()
        
        # first nothing to do !
        management.call_command("send_speaker_slot_reminder", verbosity=0)
        management.call_command("send_slot_reminder_on_closed_registrations", verbosity=0)
        self.assertEqual(len(mail.outbox), 0)

        with self.settings(DEFAULT_NB_DAYS_SPEAKER_SLOT_REMINDER=0):
            management.call_command("send_speaker_slot_reminder", verbosity=0)
            self.assertEqual(len(mail.outbox), 0)

        with self.settings(DEFAULT_NB_DAYS_SPEAKER_SLOT_REMINDER=None):
            management.call_command('send_speaker_slot_reminder', verbosity=0)
            self.assertEqual(len(mail.outbox), 0)            

        slot5 = Slot.objects.create(
            course=self.course2,
            course_type=self.course_type,
            campus=self.campus,
            building=self.building,
            room='room 666',
            # TODO: use default nb days reminder settings (??)
            date=self.today + datetime.timedelta(days=3),
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            n_places=1,
            additional_information="Hello there!",
            registration_limit_delay=24*4,
        )        
        slot5.speakers.add(self.speaker1)

        # No registered student still nothing to do
        management.call_command("send_speaker_slot_reminder", verbosity=0)
        management.call_command("send_slot_reminder_on_closed_registrations", verbosity=0)
        self.assertEqual(len(mail.outbox), 0)              

        # One registered student
        immersion_from_hell = Immersion.objects.create(
            student=self.highschool_user,
            slot=slot5,
        )
        self.assertFalse(slot5.reminder_notification_sent)
        
        management.call_command("send_speaker_slot_reminder", verbosity=0)
        
        # Reminder sent for slot !
        self.assertEqual(len(mail.outbox), 1)
        slot5.refresh_from_db()
        self.assertFalse(slot5.reminder_notification_sent)
        # Reminder sent for slot (again) !
        management.call_command("send_slot_reminder_on_closed_registrations", verbosity=0)
        self.assertEqual(len(mail.outbox), 2)
        slot5.refresh_from_db()
        # Reminder notification sent flag set to True
        self.assertTrue(slot5.reminder_notification_sent)

        # Add a structure manager 
        slot5.reminder_notification_sent=False
        slot5.save()
        new_ref_str = get_user_model().objects.create_user(
            username='new_ref_str',
            password='pass',
            email='new_ref_str@no-reply.com',
            first_name='new_ref_str',
            last_name='new_ref_str',
            establishment=self.establishment,
        )
        new_ref_str.structures.add(self.structure)
        Group.objects.get(name='REF-STR').user_set.add(new_ref_str)
        
        # No mail for REF-STR for now no notification setting initialised
        management.call_command("send_speaker_slot_reminder", verbosity=0)
        self.assertEqual(len(mail.outbox), 3)
        slot5.refresh_from_db()
        self.assertFalse(slot5.reminder_notification_sent)
        
        # Structure manager has set notifications for his structure
        setting = RefStructuresNotificationsSettings.objects.create(
            user = new_ref_str
        )
        setting.structures.add(self.structure)
        slot5.reminder_notification_sent=False
        slot5.save()
        management.call_command("send_speaker_slot_reminder", verbosity=0)
        
        # Mail for ref-str and speaker
        self.assertEqual(len(mail.outbox), 5)
        slot5.refresh_from_db()
        self.assertFalse(slot5.reminder_notification_sent)

        management.call_command("send_speaker_slot_reminder", verbosity=0)
        self.assertEqual(len(mail.outbox), 7)

        management.call_command("send_slot_reminder_on_closed_registrations", verbosity=0)
        self.assertEqual(len(mail.outbox), 9)
        # Reminder notification sent flag set to True
        slot5.refresh_from_db()      
        self.assertTrue(slot5.reminder_notification_sent)