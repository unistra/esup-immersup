import logging
import time
from typing import List, Any

from django.core.management import BaseCommand
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from immersionlyceens.apps.core.models import ImmersionUser
from immersionlyceens.libs.api.accounts import AccountAPI


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        """Delete users not present in ldap of establishments"""

        t: float = time.time()
        users: QuerySet = ImmersionUser.objects.filter(
            establishment__data_source_plugin="LDAP",
            is_superuser=False,
        )
        username_list: List[str] = []
        for user in users:
            account_api: AccountAPI = AccountAPI(user.establishment)
            ldap_reponse: List[Any] = account_api.search_user_by_email(user.email)
            if ldap_reponse == []:
                username_list.append(user.username)

        n = ImmersionUser.objects.filter(username__in=username_list).delete()
        t = time.time() - t

        logger.info(_("%s users deleted in %s seconds"), n[0], round(t, 3))
