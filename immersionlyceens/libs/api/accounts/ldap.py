import ldap3
import logging
from ldap3 import Connection, Server, SUBTREE, ALL
from .base import BaseAccountsAPI
from django.conf import settings

logger = logging.getLogger(__name__)


class LdapAPI(BaseAccountsAPI):
    def __init__(self):
        try:
            logger.debug('Host: %s, port: %s, dn: %s, base: %s',
                settings.LDAP_API_HOST, settings.LDAP_API_PORT,
                settings.LDAP_API_DN, settings.LDAP_API_BASE_DN)
            ldap_server = Server(settings.LDAP_API_HOST, port=int(settings.LDAP_API_PORT),
                       get_info=ALL)
            logger.debug('Server: %s', ldap_server)
            self.ldap_connection = Connection(ldap_server, auto_bind=True,
                user=settings.LDAP_API_DN, password=settings.LDAP_API_PASSWORD)
        except Exception:
            logger.error("Cannot connect to LDAP server : %s", sys.exc_info()[0])
            raise


    def decode_value(self, value):
        return value.decode(utf8) if isinstance(value, bytes) else value

    
    def search_user(self, search_value):
        search_attr = settings.LDAP_API_SEARCH_ATTR

        attributes = {
            'username': settings.LDAP_API_USERNAME_ATTR,
            'email': settings.LDAP_API_EMAIL_ATTR,
            'lastname': settings.LDAP_API_LASTNAME_ATTR,
            'firstname': settings.LDAP_API_FIRSTNAME_ATTR,
            'display_name': settings.LDAP_API_DISPLAY_ATTR,
        }

        search_filter = "(%s=%s)" % (
            settings.LDAP_API_SEARCH_ATTR,
            search_value,
        )

        if settings.LDAP_API_ACCOUNTS_FILTER:
            search_filter = "(&%s%s)" % (
                search_filter,
                settings.LDAP_API_ACCOUNTS_FILTER
            )
 
        logger.debug("LDAP Filter : %s", search_filter)

        try:
            self.ldap_connection.search(
                search_base=settings.LDAP_API_BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=list(attributes.values())
            )
        except Exception as e:
            logger.error("Can't perform LDAP search : %s", e)
            return False

        results = []
        
        for account in self.ldap_connection.response:
            result = {}
            for k in attributes.keys():
                val = account['attributes'].get(attributes[k], b'')
                result[k] = self.decode_value(val[0]) \
                    if isinstance(val, list) else self.decode_value(val)
            results.append(result)

        return results


