"""
Immersion app forms tests
"""
import datetime
from os.path import abspath, dirname, join

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from immersionlyceens.apps.core.models import (
    AttestationDocument, BachelorMention, Building, Campus,
    Course, CourseType, Establishment, GeneralBachelorTeaching,
    HigherEducationInstitution, HighSchool, HighSchoolLevel,
    Immersion, ImmersionUser, ImmersionUserGroup, PendingUserGroup,
    Period, PostBachelorLevel, Profile, Slot, Structure,
    StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UniversityYear,
)

from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument,
    HighSchoolStudentRecordQuota, StudentRecord, StudentRecordQuota,
    VisitorRecord, VisitorRecordDocument, VisitorRecordQuota
)

request_factory = RequestFactory()
request = request_factory.get('/admin')

class ImmersionViewsTestCase(TestCase):
    """
    Immersion app views tests
    """

    fixtures = ['group', 'generalsettings', 'mailtemplatevars', 'mailtemplate', 'images', 'high_school_levels',
                'student_levels', 'post_bachelor_levels', 'higher']

    @classmethod
    def setUpTestData(cls):
        cls.today = datetime.datetime.today()

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

        cls.high_school2 = HighSchool.objects.create(
            label='HS2',
            address='here',
            department=67,
            city='STRASBOURG',
            zip_code=67000,
            phone_number='0123456789',
            email='d@e.fr',
            head_teacher_name='M. A B',
            convention_start_date=cls.today - datetime.timedelta(days=10),
            convention_end_date=cls.today + datetime.timedelta(days=10),
            signed_charter=True,
        )

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string='whatever',
        )

        cls.highschool_user.set_password('pass')
        cls.highschool_user.save()

        # Set a second high school student for duplicates search
        cls.highschool_user2 = get_user_model().objects.create_user(
            username='hs2',
            password='pass',
            email='hs2@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
            validation_string=None,
        )

        cls.highschool_user2.set_password('pass')
        cls.highschool_user2.save()

        cls.student_user = get_user_model().objects.create_user(
            username='test@student.fr',
            password='pass',
            email='test@student.fr',
            first_name='student',
            last_name='user'
        )

        cls.student_user.set_password('pass')
        cls.student_user.save()

        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
            establishment=cls.establishment,
        )
        cls.speaker2 = get_user_model().objects.create_user(
            username='speaker2',
            password='pass',
            email='speaker-immersion2@no-reply.com',
            first_name='Another',
            last_name='Speaker',
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
        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='ref_etab@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=cls.establishment,
        )

        cls.ref_etab_user.set_password('pass')
        cls.ref_etab_user.save()

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='INTER').user_set.add(cls.speaker2)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user2)
        Group.objects.get(name='ETU').user_set.add(cls.student_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)

        BachelorMention.objects.create(
            label="Sciences et technologies du management et de la gestion (STMG)",
            active=True
        )

        GeneralBachelorTeaching.objects.create(label="Maths", active=True)

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
        cls.course.speakers.add(cls.speaker1)
        cls.campus = Campus.objects.create(label='Esplanade')
        cls.building = Building.objects.create(label='Le portique', campus=cls.campus)
        cls.course_type = CourseType.objects.create(label='CM')
        cls.slot = Slot.objects.create(
            course=cls.course, course_type=cls.course_type, campus=cls.campus,
            building=cls.building, room='room 1', date=cls.today,
            start_time=datetime.time(12, 0), end_time=datetime.time(14, 0), n_places=20
        )
        cls.slot.speakers.add(cls.speaker1)

        cls.period1 = Period.objects.create(
            label='Period 1',
            immersion_start_date=cls.today + datetime.timedelta(days=2),
            immersion_end_date=cls.today + datetime.timedelta(days=100),
            registration_start_date=cls.today + datetime.timedelta(days=1),
            allowed_immersions=4
        )

        cls.university_year = UniversityYear.objects.create(
            label='2020-2021',
            start_date=cls.today.date() - datetime.timedelta(days=10),
            end_date=cls.today.date() + datetime.timedelta(days=20),
            registration_start_date=cls.today.date() - datetime.timedelta(days=1),
            active=True,
        )

        cls.immersion = Immersion.objects.create(
            student=cls.highschool_user,
            slot=cls.slot,
            attendance_status=1
        )

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
            requires_validity_date=False
        )

        cls.attestation_2.profiles.add(Profile.objects.get(code='VIS'))


    def setUp(self):
        """
        SetUp for Immersion app tests
        """
        self.client = Client()


    def test_login(self):
        self.university_year.start_date = self.today.date() + datetime.timedelta(days=10)
        self.university_year.save()

        # This will fail (year not valid yet)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("""Sorry, the university year has not begun (or already over), you can't login yet.""",
            response.content.decode('utf-8'))

        self.university_year.start_date = self.today.date() - datetime.timedelta(days=10)
        self.university_year.save()

        # This will fail (authentication error)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'wrong_pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Authentication error", response.content.decode('utf-8'))

        # This will fail (account not validated yet)
        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Your account hasn't been enabled yet.", response.content.decode('utf-8'))

        # Validate account then retry
        self.highschool_user.validation_string = None
        self.highschool_user.save()

        response = self.client.post('/immersion/login', {'login': 'hs', 'password': 'pass'})
        self.assertEqual(response.status_code, 302)
        # The record doesn't exist : the user is redirected to the record creation page
        self.assertEqual(response.url, "/immersion/hs_record")


    def test_shibboleth_login(self):
        # Fail with one missing attribute (http_supannetablissement)
        header = {
            'HTTP_REMOTE_USER': 'new_student@domain.fr',
            'HTTP_GIVENNAME': 'student',
            'HTTP_SN': 'user',
            'HTTP_MAIL': 'new_student@domain.fr',
            'HTTP_AFFILIATION': 'student@domain.fr;member@domain.fr'
        }
        response = self.client.get('/shib/', request, **header, follow=True)
        self.assertIn("Missing attributes, account not created.", response.content.decode('utf-8'))

        response = self.client.post('/shib/', data={'submit': 1}, request=request, **header, follow=True)
        self.assertIn("Missing attributes, account not created.", response.content.decode('utf-8'))

        # FIXME : test use cases where a non-student try to authenticate

        # Tests with all attributes
        header = {
            'HTTP_REMOTE_USER': 'new_student@domain.fr',
            'HTTP_GIVENNAME': 'student',
            'HTTP_SN': 'user',
            'HTTP_MAIL': 'new_student@domain.fr',
            'HTTP_SUPANNETABLISSEMENT': '{UAI}0673021V',
            'HTTP_AFFILIATION': 'student@domain.fr;member@domain.fr'
        }

        response = self.client.get('/shib/', request, **header)
        self.assertIn("Are you sure you want to create your account ?", response.content.decode('utf-8'))

        # Account creation
        response = self.client.post('/shib/', data={'submit':1}, request=request, **header, follow=True)
        self.assertIn("Account created. Please look at your emails for the activation procedure.",
            response.content.decode('utf-8'))

        try:
            new_user = ImmersionUser.objects.get(email='new_student@domain.fr')
        except ImmersionUser.DoesNotExist:
            new_user = None

        self.assertNotEqual(new_user, None)
        self.assertNotEqual(new_user.validation_string, None)
        self.assertTrue(new_user.is_student())

        # Connection with a not-enabled-yet account
        response = self.client.get('/shib/', request, **header, follow=True)
        self.assertIn("Your account hasn't been enabled yet.", response.content.decode('utf-8'))

        new_user.validate_account()
        response = self.client.get('/shib/', request, **header, follow=True)
        self.assertIn("Please fill this form to complete the personal record", response.content.decode('utf-8'))

        # Student record data
        record_data = {
            "student": new_user.id,
            "last_name": "",
            "first_name": new_user.first_name,
            "email": new_user.email,
            "birth_date": "",
            "phone": "0388010101",
            "uai_code": "0673021V",
            "level": 1,
            "origin_bachelor_type": 1,
            "current_diploma": "DUT 1ere année",
            "submit": 1,
        }

        # Missing fields
        response = self.client.post('/immersion/student_record', record_data, follow=True)
        self.assertIn("This field is required", response.content.decode('utf-8'))

        # All fields
        record_data["last_name"] = new_user.last_name
        record_data["birth_date"] = "1999-01-04"
        record_data["current_diploma"] = "DUT 1ere année",

        response = self.client.post('/immersion/student_record', record_data, follow=True)
        self.assertIn("Record successfully saved.", response.content.decode('utf-8'))

        # Post with an another email
        record_data["email"] = "another@email.com"
        response = self.client.post('/immersion/student_record', record_data, follow=True)

        user = ImmersionUser.objects.get(pk=new_user.id)
        self.assertNotEqual(user.validation_string, None)

        # Test uai code update
        record = StudentRecord.objects.get(student=user)
        record.uai_code = "XXXXX"
        record.save()
        response = self.client.get('/immersion/student_record', follow=True)
        record = StudentRecord.objects.get(student=user)
        self.assertEqual(record.uai_code, "0673021V")


        # Test get route as ref-etab user
        record = StudentRecord.objects.get(student=user)
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get('/immersion/student_record/%s' % record.id)
        self.assertIn("Please fill this form to complete the personal record", response.content.decode('utf-8'))


    def test_register(self):
        data = {
            'first_name': 'prenom',
            'last_name': 'nom',
            'email': 'mon_email@mondomaine.fr',
            'password1': 'passw',
            'password2': 'passw_2',
            'registration_type': 'hs',
        }

        # Will fail (passwords don't match, missing email2)
        response = self.client.post('/immersion/register', data)

        self.assertIn("The two password fields didn’t match.", response.content.decode('utf-8'))
        self.assertIn("This field is required.", response.content.decode('utf-8'))
        self.assertIn("Emails do not match", response.content.decode('utf-8'))

        # Will fail (password too short)
        data['email2'] = "mon_email@mondomaine.fr"
        data['password2'] = "passw"
        response = self.client.post('/immersion/register', data)

        self.assertIn("This password is too short. It must contain at least 8 characters.",
            response.content.decode('utf-8'))

        # Should succeed and redirect
        data['password1'] = "Is this password long enough ?"
        data['password2'] = "Is this password long enough ?"

        response = self.client.post('/immersion/register', data, follow=True)
        self.assertIn("Account created. Please look at your emails for the activation procedure.",
            response.content.decode('utf-8'))

        # Check some attributes
        new_account = ImmersionUser.objects.get(username="mon_email@mondomaine.fr")
        self.assertNotEqual(new_account.validation_string, None)
        self.assertNotEqual(new_account.destruction_date, None)
        self.assertIsInstance(new_account.destruction_date, datetime.date)
        self.assertFalse(new_account.is_valid())

        lyc_group = Group.objects.get(name='LYC')
        self.assertIn(lyc_group, new_account.groups.all())

        # Fail with duplicated email address (lower/upper case mix)
        data["email"] = 'MoN_EmaiL@monDomaine.FR'
        data["email2"] = 'MoN_EmaiL@monDomaine.FR'

        response = self.client.post('/immersion/register', data)
        self.assertIn("An account already exists with this email address", response.content.decode('utf-8'))

        # Fail with an invalid year
        self.university_year.registration_start_date = self.today + datetime.timedelta(days=10)
        self.university_year.registration_end_date = self.today + datetime.timedelta(days=20)
        self.university_year.save()

        response = self.client.get('/immersion/register', follow=True)
        self.assertIn("Sorry, you can't register right now.", response.content.decode('utf-8'))

    def test_recovery(self):
        # Fail : not a highschool user
        response = self.client.post('/immersion/recovery', {'email': 'test@student.fr'})
        self.assertIn("Please use your establishment credentials.", response.content.decode('utf-8'))

        # Fail : email not found but the response should not expose the fact that the mail is not found !
        response = self.client.post('/immersion/recovery', {'email': 'test@domaine.fr'})
        self.assertIn("An email has been sent with the procedure to set a new password.",
                      response.content.decode('utf-8')
        )

        # Success
        response = self.client.post('/immersion/recovery', {'email': "lycref-immersion@no-reply.com"})
        self.assertIn("An email has been sent with the procedure to set a new password.",
                      response.content.decode('utf-8')
        )

        # Success with email mixing lower/uppercase letters
        response = self.client.post('/immersion/recovery', {'email': "LycRef-Immersion@NO-RepLY.com"})
        self.assertIn("An email has been sent with the procedure to set a new password.",
                      response.content.decode('utf-8')
        )

        user = ImmersionUser.objects.get(username="lycref")
        self.assertNotEqual(user.recovery_string, None)

    def test_reset_password(self):
        # Fail because of invalid hash
        response = self.client.get('/immersion/reset_password/wrong_hash', follow=True)
        self.assertIn("Password recovery : invalid data", response.content.decode('utf-8'))

        # Set a hash and retry
        self.highschool_user.recovery_string="hashtest"
        self.highschool_user.save()
        response = self.client.get('/immersion/reset_password/hashtest', follow=True)
        self.assertNotIn("Password recovery : invalid data", response.content.decode('utf-8'))

        # Password too short
        response = self.client.post('/immersion/reset_password/hashtest',
            {'password1': 'short', 'password2': 'short'}
        )
        self.assertIn("This password is too short. It must contain at least 8 characters.",
            response.content.decode('utf-8')
        )

        # This one should be ok
        response = self.client.post('/immersion/reset_password/hashtest',
            {'password1': 'a_better_password', 'password2': 'a_better_password'}, follow=True
        )
        self.assertIn("Password successfully updated.", response.content.decode('utf-8'))

    def test_change_password(self):
        # Simple get change password page
        self.client.login(username='hs', password='pass')
        response = self.client.get('/immersion/change_password', follow=True)
        self.assertIn("Password change", response.content.decode('utf-8'))

        current_password = ImmersionUser.objects.get(pk=self.highschool_user.id).password

        # Post new password
        # Fail
        data = {
            "old_password": "pass",
            "new_password1": "this_is_my_new_pass",
            "new_password2": "this_is_my_new_pass_with_error",
        }
        response = self.client.post('/immersion/change_password', data)
        self.assertIn("The two password fields didn’t match", response.content.decode('utf-8'))

        # Success
        data["new_password2"] = "this_is_my_new_pass"
        response = self.client.post('/immersion/change_password', data)
        self.assertIn("Password successfully updated", response.content.decode('utf-8'))
        self.assertNotEqual(ImmersionUser.objects.get(pk=self.highschool_user.id).password, current_password)


    def test_activate(self):
        # Set an activation string
        self.highschool_user.validation_string = "activate_this"
        self.highschool_user.save()

        # Fail with incorrect hash
        response = self.client.get('/immersion/activate/wrong_string', follow=True)
        self.assertIn("Invalid activation data", response.content.decode('utf-8'))

        # Success
        response = self.client.get('/immersion/activate/activate_this', follow=True)
        self.assertIn("Your account is now enabled. Thanks !", response.content.decode('utf-8'))

    def test_resend_activation(self):
        # Fail with account not found but the response should not expose the fact that the mail is not found !
        response = self.client.post('/immersion/resend_activation', {'email': 'this.email@is_wrong.com'}, follow=True)
        self.assertIn("The activation message has been resent.", response.content.decode('utf-8'))

        # Success
        response = self.client.post('/immersion/resend_activation', {'email': 'hs@no-reply.com'}, follow=True)
        self.assertIn("The activation message has been resent.", response.content.decode('utf-8'))

        # Success with an email mixing lower/uppercase lettres
        response = self.client.post('/immersion/resend_activation', {'email': 'HS@No-RePlY.com'}, follow=True)
        self.assertIn("The activation message has been resent.", response.content.decode('utf-8'))

        # Fail with account already activated
        self.highschool_user.validation_string = None
        self.highschool_user.save()
        response = self.client.post('/immersion/resend_activation', {'email': 'hs@no-reply.com'}, follow=True)
        self.assertIn("This account has already been activated, please login.", response.content.decode('utf-8'))

    def test_home(self):
        # Not logged : redirection
        response = self.client.post('/immersion/')
        self.assertEqual(response.url, "/accounts/login/?next=/immersion/")

        # Logged
        self.client.login(username='hs', password='pass')
        response = self.client.post('/immersion/')
        self.assertEqual(response.status_code, 200)

    def test_high_school_student_record(self):
        # First check that high school student record doesn't exist yet
        self.assertFalse(HighSchoolStudentRecord.objects.filter(student=self.highschool_user).exists())
        self.assertFalse(HighSchoolStudentRecordDocument.objects.exists())

        self.client.login(username='hs', password='pass')
        response = self.client.get('/immersion/hs_record')

        self.assertIn("Your record status : To complete", response.content.decode('utf-8'))
        self.assertIn("Please fill this form to complete the personal record", response.content.decode('utf-8'))

        record_data = {
            "student": self.highschool_user.id,
            "last_name": "",
            "first_name": self.highschool_user.first_name,
            "email": self.highschool_user.email,
            "birth_date": "",
            "phone": "0388010101",
            "highschool": self.high_school.id,
            "level": 1,
            "class_name": "S10",
            "bachelor_type": 1,
            "general_bachelor_teachings": [GeneralBachelorTeaching.objects.first().id],
            "technological_bachelor_mention": "",
            "professional_bachelor_mention": "",
            "post_bachelor_level": "",
            "origin_bachelor_type": 1,
            "current_diploma": "",
            "visible_immersion_registrations": 1,
            "visible_email": 1,
            "submit": 1,
        }

        # Missing fields
        response = self.client.post('/immersion/hs_record', record_data, follow=True)
        self.assertIn("This field is required", response.content.decode('utf-8'))

        # All fields
        record_data["last_name"] = self.highschool_user.last_name
        record_data["birth_date"] = (self.today - datetime.timedelta(days=5840)).strftime("%Y-%m-%d") # ~16 years (=under 18)
        record_data["post_bachelor_level"] = 1

        response = self.client.post('/immersion/hs_record', record_data, follow=True)
        self.assertTrue(HighSchoolStudentRecord.objects.filter(student=self.highschool_user).exists())

        self.assertIn("Record saved. Please fill all the required attestation documents below.",
            response.content.decode('utf-8'))
        self.assertIn("Record successfully saved.", response.content.decode('utf-8'))
        self.assertIn("Your record status : To complete", response.content.decode('utf-8'))

        record = self.highschool_user.get_high_school_student_record()

        # Check attestations objects (only 1)
        documents = HighSchoolStudentRecordDocument.objects.filter(record=record)

        self.assertEqual(documents.count(), 1)
        self.assertEqual(documents.first().attestation, self.attestation_1)

        document = documents.first()

        # repost without attestations
        response = self.client.post('/immersion/hs_record', record_data, follow=True)
        self.assertIn("You have errors in Attestations section", response.content.decode('utf-8'))

        # Add missing file, fields, and repost
        fd = open(join(dirname(abspath(__file__)), 'test_file.pdf'), 'rb')
        prefix = f"document_{self.attestation_1.pk}"

        record_data.update({
            f"{prefix}-record": document.record.pk,
            f"{prefix}-attestation": document.attestation.pk,
            f"{prefix}-document": [SimpleUploadedFile('test_file.pdf', fd.read())],
        })

        # f"{prefix}-validity_date": (self.today + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        response = self.client.post('/immersion/hs_record', record_data, follow=True)
        content = response.content.decode('utf-8')

        self.assertIn("Thank you. Your record is awaiting validation from your high-school referent.", content)
        self.assertIn("Your record status : To validate", response.content.decode('utf-8'))
        document.refresh_from_db()
        self.assertNotEqual(document.document, None)

        # Post with another email - Do not repost the attestation file
        del(record_data[f"{prefix}-document"])
        record_data["email"] = "another@email.com"
        response = self.client.post('/immersion/hs_record', record_data, follow=True)

        self.highschool_user.refresh_from_db()
        self.assertNotEqual(self.highschool_user.validation_string, None)

        # Assume the record has been rejected, then repost with another high school (validation should be set to 1)
        record = HighSchoolStudentRecord.objects.get(student=self.highschool_user)
        self.assertEqual(record.validation, 1)
        record.validation = 3 # Rejected
        record.save()

        record_data["highschool"] = self.high_school2.id
        response = self.client.post('/immersion/hs_record', record_data, follow=True)

        record = HighSchoolStudentRecord.objects.get(student=self.highschool_user)
        self.assertEqual(record.highschool.id, self.high_school2.id)
        self.assertEqual(record.validation, 1)

        # Test record duplication with another student
        self.client.login(username='hs2', password='pass')
        self.assertFalse(HighSchoolStudentRecord.objects.filter(student=self.highschool_user2).exists())
        response = self.client.get('/immersion/hs_record')
        self.assertIn("Your record status : To complete", response.content.decode('utf-8'))
        self.assertIn("Please fill this form to complete the personal record", response.content.decode('utf-8'))

        record_data.update({
            'student': self.highschool_user2.id,
            'last_name': self.highschool_user2.last_name,
            'first_name': self.highschool_user2.first_name,
            'email': self.highschool_user2.email,
        })

        response = self.client.post('/immersion/hs_record', record_data, follow=True)
        self.assertIn("A record already exists with this identity, please contact the establishment referent.",
            response.content.decode('utf-8'))

        # Test get route as ref_etab user
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get('/immersion/hs_record/%s' % record.id)
        self.assertIn("Please fill this form to complete the personal record", response.content.decode('utf-8'))


    def test_immersions(self):
        # Should redirect to login page
        response = self.client.get('/immersion/registrations')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/immersion/registrations")

        # Simple view check
        self.client.login(username='hs', password='pass')
        response = self.client.get('/immersion/registrations')
        self.assertIn("Immersions to come", response.content.decode('utf-8'))


    def test_immersion_attestation_download(self):
        # as a student
        self.client.login(username='hs', password='pass')
        response = self.client.get('/immersion/dl/attestation/%s' % self.immersion.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')

        # as a ref-etab manager
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get('/immersion/dl/attestation/%s' % self.immersion.id, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')


    def test_immersion_attendance_list_download(self):
        # as a ref-etab manager
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get('/immersion/dl/attendance_list/%s' % self.immersion.slot.id, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')


    def test_record_duplicates(self):
        record = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user,
            highschool=self.high_school,
            birth_date="1990-02-19",
            level=HighSchoolLevel.objects.get(pk=1),
            class_name="S20",
            bachelor_type=1,
            visible_immersion_registrations=False,
            visible_email=False,
            validation=2,
            duplicates="[5,6,4]"
        )

        record2 = HighSchoolStudentRecord.objects.create(
            student=self.highschool_user2,
            highschool=self.high_school,
            birth_date="1990-02-19",
            level=HighSchoolLevel.objects.get(pk=1),
            class_name="S20",
            bachelor_type=1,
            visible_immersion_registrations=False,
            visible_email=False,
            validation=2,
            duplicates="[5,6,4]"
        )

        self.assertEqual(
            HighSchoolStudentRecord.get_duplicate_tuples(),
            {tuple(sorted([4, 5, 6, record2.id])), tuple(sorted([4, 5, 6, record.id]))}
        )

        self.assertTrue(record.has_duplicates())
        self.assertEqual(record.get_duplicates(), [4,5,6])
        record.remove_duplicate(id=5)
        self.assertEqual(record.get_duplicates(), [4,6])
        self.assertEqual(record.solved_duplicates, "5")

        record.solved_duplicates = "6,7"
        record.save()

        HighSchoolStudentRecord.clear_duplicate(6)

        record = HighSchoolStudentRecord.objects.get(pk=record.id)
        record2 = HighSchoolStudentRecord.objects.get(pk=record2.id)

        self.assertEqual(record.get_duplicates(), [4])
        self.assertEqual(record.solved_duplicates, "7")
        self.assertEqual(record2.get_duplicates(), [4,5])

    def test_link_accounts(self):
        url = reverse('immersion:link_accounts')

        self.assertFalse(PendingUserGroup.objects.all().exists())

        # as a ref-etab manager : redirection
        self.client.login(username='ref_etab', password='pass')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username='speaker1', password='pass')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Post requests
        # With an unknown email
        response = self.client.post(url, {'email': 'unknown@email.net'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("No account found with this email address", response.content.decode('utf8'))

        # Attempt to link a non-speaker user
        response = self.client.post(url, {'email': self.lyc_ref.email})
        self.assertEqual(response.status_code, 200)
        self.assertIn("This account is not a speaker-only one, it can't be linked", response.content.decode('utf8'))

        # Success
        response = self.client.post(url, {'email': self.speaker2.email})
        self.assertEqual(response.status_code, 200)
        self.assertIn("The link message has been sent to this email address", response.content.decode('utf8'))

        self.assertTrue(PendingUserGroup.objects.all().exists())
        pending_group = PendingUserGroup.objects.first()
        self.assertEqual(pending_group.creation_date.date(), self.today.date())
        self.assertEqual(pending_group.immersionuser1, self.speaker1)
        self.assertEqual(pending_group.immersionuser2, self.speaker2)

        # Accepted as a success : users are already linked
        user_group = ImmersionUserGroup.objects.create()
        user_group.immersionusers.add(self.speaker1)
        user_group.immersionusers.add(self.speaker2)

        response = self.client.post(url, {'email': self.speaker2.email})
        self.assertEqual(response.status_code, 200)
        self.assertIn("These accounts are already linked", response.content.decode('utf8'))


    def test_link_validation(self):
        self.assertFalse(PendingUserGroup.objects.all().exists())
        self.assertEqual(self.speaker1.linked_users(), [self.speaker1, ])
        self.assertEqual(self.speaker2.linked_users(), [self.speaker2, ])

        PendingUserGroup.objects.create(
            immersionuser1=self.speaker1,
            immersionuser2=self.speaker2,
            validation_string="whatever"
        )

        self.client.login(username='speaker1', password='pass')
        response = self.client.get(reverse('immersion:link', args=("whatever", )), follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertIn("Your accounts have been linked", response.content.decode('utf8'))
        self.assertEqual(self.speaker1.linked_users(), [self.speaker1, self.speaker2])
