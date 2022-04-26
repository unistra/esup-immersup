import time
from typing import List, Any

from django.core.management import BaseCommand
from django.db.models import QuerySet

from immersionlyceens.apps.core.models import ImmersionUser
from immersionlyceens.libs.api.accounts import AccountAPI


class Command(BaseCommand):
    def handle(self, *args, **options):
        """Delete users not present in ldap of establishments"""
        users: QuerySet = ImmersionUser.objects.filter(
            establishment__data_source_plugin="LDAP",
            is_superuser=False,
        )
        for user in users:
            account_api: AccountAPI = AccountAPI(user.establishment)
            ldap_reponse: List[Any] = account_api.search_user_by_email(user.email)
            if ldap_reponse == []:
                user.delete()
