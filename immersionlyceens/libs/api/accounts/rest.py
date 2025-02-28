import json
import logging
import requests

from typing import Any, Dict, List, Optional, Union
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext, gettext_lazy as _
from immersionlyceens.apps.core.models import Establishment

from .base import BaseAccountsAPI

logger = logging.getLogger(__name__)

class AccountAPI(BaseAccountsAPI):
    attrs_list = [
        'HOST', 'PORT', 'PATH', 'HEADERS', 'SEARCH_ATTR', 'DISPLAY_ATTR',
        'EMAIL_ATTR', 'LASTNAME_ATTR', 'FIRSTNAME_ATTR'
    ]

    def __init__(self, establishment: Establishment):
        self.establishment = establishment

        try:
            self.check_settings()
        except Exception as e:
            raise ImproperlyConfigured(_("Please check establishment REST plugin settings : %s") % e)


    @classmethod
    def get_plugin_attrs(self):
        return self.attrs_list

    def check_settings(self):
        if not isinstance(self.establishment, Establishment):
            raise Exception(_("Not an Establishment object"))

        if self.establishment.data_source_plugin != "REST":
            raise Exception(_("Establishment is not configured with REST plugin"))

        for attr in self.attrs_list:
            try:
                value = self.establishment.data_source_settings[attr]
                setattr(self, attr.upper(), value)
            except TypeError:
                raise ImproperlyConfigured(_("REST plugin settings are empty"))
            except KeyError:
                raise ImproperlyConfigured(_("REST plugin setting '%s' not found") % attr)
            except Exception as e:
                raise Exception(attr, e)

        if hasattr(self, "HEADERS") and not isinstance(self.HEADERS, dict):
            raise ImproperlyConfigured(_("HEADERS must be a dict"))

        if hasattr(self, "PORT"):
            try:
                self.PORT = int(self.PORT)
            except:
                raise ImproperlyConfigured(_("PORT must be an integer"))


    def decode_value(self, value: Union[bytes, str]) -> str:
        return value.decode("utf8") if isinstance(value, bytes) else value

    def search_user(self, search_value: str, search_attr: Optional[str] = None) -> Union[bool, List[Dict[str, Any]]]:
        response = None

        if search_attr is None:
            search_attr = self.SEARCH_ATTR

        attributes = {
            self.EMAIL_ATTR: 'email',
            self.LASTNAME_ATTR: 'lastname',
            self.FIRSTNAME_ATTR: 'firstname',
            self.DISPLAY_ATTR: 'display_name',
        }

        # GET format, will be appended to
        search_filter = f"?{search_attr}={search_value}*"
        logger.debug(f"REST Filter : {search_filter}")

        try:
            response = requests.get(f"{self.HOST}:{self.PORT}/{self.PATH}{search_filter}", headers=self.HEADERS)
            content = json.loads(response.content.decode("utf-8"))
            if response.status_code != 200:
                raise
        except Exception as e:
            if response and hasattr(response, "status_code"):
                logger.error("Can't perform REST search (error {response.status_code}) : %s", e)
            else:
                logger.error("Can't perform REST search : %s", e)
                
            return False

        results = []

        for account in content:
            result = {
                attributes[k]:v
                for k,v in account.items() if k in attributes.keys()
            }

            results.append(result)

        return results

