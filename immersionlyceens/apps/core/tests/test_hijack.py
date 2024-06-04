"""
Immersup hijacking tests suite
"""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse_lazy


from immersionlyceens.libs.utils import get_general_setting


from ..models import (
    Establishment,
    HighSchool,
    HigherEducationInstitution,
    GeneralSettings,
)

request_factory = RequestFactory()
request = request_factory.get('/admin')


class HijackingTestCase(TestCase):
    """
    Hijacking tests class
    """

    fixtures = [
        'group',
    ]

    @classmethod
    def setUpTestData(cls):
        """
        Data that do not change in tests below
        They are only set once
        """
        cls.master_establishment = Establishment.objects.create(
            code='ETA1',
            label='Etablissement 1',
            short_label='Eta 1',
            active=True,
            master=True,
            email='test1@test.com',
            address='address',
            department='departmeent',
            city='city',
            zip_code='zip_code',
            phone_number='+33666',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first(),
        )

        cls.master_establishment2 = Establishment.objects.create(
            code='ETA4',
            label='Etablissement 4',
            short_label='Eta 4',
            active=True,
            master=True,
            email='test4@test.com',
            address='address',
            department='departmeent',
            city='city',
            zip_code='zip_code',
            phone_number='+33666',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.first(),
        )

        cls.establishment = Establishment.objects.create(
            code='ETA2',
            label='Etablissement 2',
            short_label='Eta 2',
            active=True,
            master=False,
            email='test2@test.com',
            address='address2',
            department='departmeent2',
            city='city2',
            zip_code='zip_code2',
            phone_number='+33666666',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last(),
        )

        cls.establishment2 = Establishment.objects.create(
            code='ETA3',
            label='Etablissement 3',
            short_label='Eta 3',
            active=True,
            master=False,
            email='test3@test.com',
            address='address3',
            department='departmeent3',
            city='city3',
            zip_code='zip_code3',
            phone_number='+33666666',
            signed_charter=True,
            uai_reference=HigherEducationInstitution.objects.last(),
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
            convention_start_date=datetime.datetime.today() - datetime.timedelta(days=2),
            convention_end_date=datetime.datetime.today() + datetime.timedelta(days=2),
            signed_charter=True,
        )

        cls.highschool_user = get_user_model().objects.create_user(
            username='hs',
            password='pass',
            email='hs@no-reply.com',
            first_name='high',
            last_name='SCHOOL',
        )

        cls.speaker1 = get_user_model().objects.create_user(
            username='speaker1',
            password='pass',
            email='speaker-immersion@no-reply.com',
            first_name='speak',
            last_name='HER',
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

        cls.ref_master_etab_user = get_user_model().objects.create_user(
            username='ref_master_etab',
            password='pass',
            email='ref_master_etab@no-reply.com',
            first_name='ref_master_etab',
            last_name='ref_master_etab',
            establishment=cls.master_establishment,
        )

        cls.ref_master_etab_user2 = get_user_model().objects.create_user(
            username='ref_master_etab2',
            password='pass',
            email='ref_master_etab2@no-reply.com',
            first_name='ref_master_etab2',
            last_name='ref_master_etab2',
            establishment=cls.master_establishment2,
        )

        cls.operator_user = get_user_model().objects.create_user(
            username='operator',
            password='pass',
            email='operator@no-reply.com',
            first_name='operator',
            last_name='operator',
        )

        cls.operator_user2 = get_user_model().objects.create_user(
            username='operator2',
            password='pass',
            email='operator2@no-reply.com',
            first_name='operator2',
            last_name='operator2',
        )

        cls.ref_etab_user = get_user_model().objects.create_user(
            username='ref_etab',
            password='pass',
            email='immersion@no-reply.com',
            first_name='ref_etab',
            last_name='ref_etab',
            establishment=cls.establishment,
        )

        cls.ref_etab_user2= get_user_model().objects.create_user(
            username='ref_etab2',
            password='pass',
            email='immersion2@no-reply.com',
            first_name='ref_etab2',
            last_name='ref_etab2',
            establishment=cls.establishment,
        )

        cls.ref_etab_user3 = get_user_model().objects.create_user(
            username='ref_etab3',
            password='pass',
            email='immersion3@no-reply.com',
            first_name='ref_etab3',
            last_name='ref_etab3',
            establishment=cls.establishment2,
        )

        cls.ref_str_user = get_user_model().objects.create_user(
            username='ref_str',
            password='pass',
            email='ref_str@no-reply.com',
            first_name='ref_str',
            last_name='ref_str',
            establishment=cls.establishment,
        )

        cls.not_active_superuser = get_user_model().objects.create_superuser(
            username='sleeping_admin',
            password='admin',
            email='sleepingevil@evil.net',
            first_name='sleeping',
            last_name='admin',
            is_active = False,
        )

        cls.active_superuser = get_user_model().objects.create_superuser(
            username='admin',
            password='admin',
            email='evil@evil.net',
            first_name='admin',
            last_name='admin',
            is_active=True,
        )

        Group.objects.get(name='INTER').user_set.add(cls.speaker1)
        Group.objects.get(name='LYC').user_set.add(cls.highschool_user)
        Group.objects.get(name='REF-LYC').user_set.add(cls.lyc_ref)
        Group.objects.get(name='REF-STR').user_set.add(cls.ref_str_user)
        Group.objects.get(name='REF-TEC').user_set.add(cls.operator_user)
        Group.objects.get(name='REF-TEC').user_set.add(cls.operator_user2)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user)
        Group.objects.get(name='REF-ETAB-MAITRE').user_set.add(cls.ref_master_etab_user2)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user)
        Group.objects.get(name='REF-ETAB').user_set.add(cls.ref_etab_user2)

        cls.hijack_url = reverse_lazy("hijack:acquire")
        cls.release_url = reverse_lazy("hijack:release")

    def test_hijacking(self):
        """ Test hijacking permissions """

        # First be sure that activate hijack is not set
        self.assertEqual(get_general_setting('ACTIVATE_HIJACK'), False)

        # Speaker can't hijack
        self.client.force_login(self.speaker1)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.highschool_user.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Highschool user can't hijack
        self.client.force_login(self.highschool_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Ref lyc user can't hijack
        self.client.force_login(self.lyc_ref)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Ref structure can't hijack
        self.client.force_login(self.ref_str_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Ref tech can't hijack without ACTIVATE_HIJACK setting = True
        self.client.force_login(self.operator_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Ref master etab can't hijack without ACTIVATE_HIJACK setting = True
        self.client.force_login(self.ref_master_etab_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Ref etab can't hijack without ACTIVATE_HIJACK setting = True
        self.client.force_login(self.ref_etab_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Activate hijack
        s = GeneralSettings.objects.get(setting="ACTIVATE_HIJACK")
        s.parameters['value'] = True
        s.save()
        self.assertEqual(get_general_setting('ACTIVATE_HIJACK'), True)

        # Not active user can't be hijacked if ACTIVATE_HIJACK setting = True
        self.client.force_login(self.active_superuser)
        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.not_active_superuser.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Active user can be hijacked
        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.speaker1.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

        # Operator can hijack speaker
        self.client.force_login(self.operator_user)
        response = self.client.post(
            self.hijack_url, {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(self.release_url)

        # Operator can't hijack operator
        response = self.client.post(
            self.hijack_url, {"user_pk": self.operator_user2.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Master establishment manager could hijack all users except superuser, operator and master establishment manager
        self.client.force_login(self.ref_master_etab_user)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.operator_user.pk},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.active_superuser.pk},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 302)

        # Establishment manager could hijack all users except superuser,
        # operator, master establishment manager, establishment manager

        self.client.force_login(self.ref_etab_user)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.operator_user.pk},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.active_superuser.pk},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.ref_etab_user2.pk},
        )
        self.assertEqual(response.status_code, 403)

        # Hijack user from different establishment is forbidden
        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.ref_etab_user3.pk},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.lyc_ref.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(self.release_url)

        response = self.client.post(
            self.hijack_url,
            {"user_pk": self.speaker1.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(self.release_url)
