import logging
import time
from typing import List, Any, Union

from django.core.management import BaseCommand
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from immersionlyceens.apps.core.models import ImmersionUser
from immersionlyceens.libs.api.accounts import AccountAPI
from . import Schedulable

logger = logging.getLogger(__name__)


class Command(BaseCommand, Schedulable):
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
            ldap_response: Union[bool, List[Any]] = account_api.search_user(
                search_value=user.email,
                search_attr=account_api.EMAIL_ATTR
            )
            if ldap_response == [] or ldap_response is False:
                username_list.append(user.username)

        n = ImmersionUser.objects.filter(username__in=username_list).delete()
        t = time.time() - t

        msg = _("%s users deleted in %s seconds"), n[0], round(t, 3)

        logger.info(msg)
        return msg
