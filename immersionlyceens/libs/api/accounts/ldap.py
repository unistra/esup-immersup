import logging
import ssl
from typing import Any, Dict, List, Optional, Union
from os import path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext, gettext_lazy as _
from immersionlyceens.apps.core.models import Establishment
from ldap3 import ALL, SUBTREE, Connection, Server, SIMPLE, Tls
from ldap3.core.exceptions import LDAPBindError

from .base import BaseAccountsAPI

logger = logging.getLogger(__name__)

class AccountAPI(BaseAccountsAPI):
    attrs_list = [
        'HOST', 'PORT', 'DN', 'PASSWORD', 'BASE_DN', 'ACCOUNTS_FILTER', 'SEARCH_ATTR', 'DISPLAY_ATTR',
        'EMAIL_ATTR', 'LASTNAME_ATTR', 'FIRSTNAME_ATTR'
    ]

    optional_attrs_list = [
        'CACERT'
    ]

    def __init__(self, establishment: Establishment):
        self.establishment = establishment
        self.tls = self.set_tls()

        try:
            self.check_settings()
        except Exception as e:
            raise ImproperlyConfigured(_("Please check establishment LDAP plugin settings : %s") % e)

        try:
            server_settings = {
                "host": self.HOST,
                "port": int(self.PORT),
                "get_info": ALL
            }

            if self.tls:
                server_settings['tls'] = self.tls
                server_settings['use_ssl'] = True

            logger.debug(f"Host: {self.HOST}, port: {self.PORT}, dn: {self.DN}, base: {self.BASE_DN}")
            ldap_server = Server(**server_settings)
            logger.debug(f"Server: {ldap_server}")
        except Exception as e:
            logger.error("Cannot connect to LDAP server : %s", e)
            raise

        # LDAP Connection settings
        connection_settings = {
            "server": ldap_server,
            "user": self.DN,
            "password": self.PASSWORD
        }

        if not self.tls:
            connection_settings["auto_bind"] = "NO_TLS"
        else:
            connection_settings["authentication"] = SIMPLE

        try:
            self.ldap_connection = Connection(**connection_settings)
            self.ldap_connection.bind()
        except LDAPBindError:
            bound = False

            # For older TLSv1 protocols
            connection_settings["auto_bind"] = "NONE"
            self.ldap_connection = Connection(**connection_settings)
            tls_success = self.ldap_connection.start_tls()

            if tls_success:
                bound = self.ldap_connection.bind()

            if not bound:
                logger.error("Cannot connect to LDAP server")
                raise

    @classmethod
    def get_plugin_attrs(self):
        return self.attrs_list

    def set_tls(self):
        """
        Set LDAP Tls object
        :return: a Tls object using CACERT file from LDAP config, relative to SITE_ROOT/config symlink
        """
        try:
            return Tls(
                ca_certs_file=path.join(
                    settings.SITE_ROOT,
                    "config",
                    self.establishment.data_source_settings["CACERT"]
                ),
                validate=ssl.CERT_OPTIONAL

            )
        except Exception as e:
            logger.error(f"LDAP TLS error: {e}")
            return None

    def check_settings(self):
        if not isinstance(self.establishment, Establishment):
            raise Exception(_("Not an Establishment object"))

        if self.establishment.data_source_plugin != "LDAP":
            raise Exception(_("Establishment is not configured with LDAP plugin"))

        for attr in self.attrs_list:
            try:
                value = self.establishment.data_source_settings[attr]
                setattr(self, attr.upper(), value)
            except TypeError:
                raise ImproperlyConfigured(_("LDAP plugin settings are empty"))
            except KeyError:
                raise ImproperlyConfigured(_("LDAP plugin setting '%s' not found") % attr)
            except Exception as e:
                raise Exception(attr, e)


    def decode_value(self, value: Union[bytes, str]) -> str:
        return value.decode("utf8") if isinstance(value, bytes) else value

    def search_user(self, search_value: str, search_attr: Optional[str] = None) -> Union[bool, List[Dict[str, Any]]]:
        if search_attr is None:
            search_attr = self.SEARCH_ATTR

        attributes = {
            'email': self.EMAIL_ATTR,
            'lastname': self.LASTNAME_ATTR,
            'firstname': self.FIRSTNAME_ATTR,
            'display_name': self.DISPLAY_ATTR,
        }
        search_filter = f"({search_attr}={search_value}*)"

        if self.ACCOUNTS_FILTER:
            search_filter = f"(&{search_filter}{self.ACCOUNTS_FILTER})"

        logger.debug(f"LDAP Filter : {search_filter}")

        try:
            self.ldap_connection.search(
                search_base=self.BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=list(attributes.values())
            )
        except Exception as e:
            logger.error("Can't perform LDAP search : %s", e)
            return False

        results = []

        for account in filter(lambda x: 'attributes' in x.keys(), self.ldap_connection.response):
            result = {}
            for k in attributes.keys():
                val = account['attributes'].get(attributes[k], b'')
                result[k] = self.decode_value(val[0]) \
                    if isinstance(val, list) and len(val) else self.decode_value(val)
            results.append(result)

        return results

