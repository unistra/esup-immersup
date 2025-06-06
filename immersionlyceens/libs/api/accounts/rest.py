import hashlib
import json
import logging
import requests
import string
from datetime import datetime

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

    optional_attrs_list = ["FUNCTION"]

    # functions-dependant mandatory attributes
    FUNC_ATTRS = {
        "generate_x_token_with_timestamp": ["SECRET"]
    }

    def __init__(self, establishment: Establishment):
        self.establishment = establishment
        self.search_value = None

        try:
            self.check_settings()
        except Exception as e:
            raise ImproperlyConfigured(_("Please check establishment REST plugin settings : %s") % e)

    def generate_x_token_with_timestamp(self):
        """
        Generate a header value with this format "key=sha512(secret-timestamp),timestamp=timestamp"
        Return a header dict {'X-Token': value}
        """
        timestamp = datetime.now().strftime('%s')
        key=f"{self.SECRET}-{timestamp}"
        hash = hashlib.sha512(key.encode('utf-8')).hexdigest()

        return {'X-Token': f"key={hash},timestamp={timestamp}"}


    @classmethod
    def get_plugin_attrs(self):
        return self.attrs_list

    def check_settings(self):
        if not isinstance(self.establishment, Establishment):
            raise Exception(_("Not an Establishment object"))

        if self.establishment.data_source_plugin != "REST":
            raise Exception(_("Establishment is not configured with REST plugin"))

        # Mandatory attributes
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

        # Optional attributes
        for attr in self.optional_attrs_list:
            value = self.establishment.data_source_settings.get(attr)
            if value:
                setattr(self, attr.upper(), value)


        if hasattr(self, "HEADERS") and not isinstance(self.HEADERS, dict):
            raise ImproperlyConfigured(_("HEADERS must be a dict"))

        if hasattr(self, "PORT"):
            try:
                self.PORT = int(self.PORT)
            except:
                raise ImproperlyConfigured(_("PORT must be an integer"))

        if hasattr(self, "FUNCTION"):
            # check that function name exists

            try:
                func = getattr(self, self.FUNCTION)
            except AttributeError:
                raise ImproperlyConfigured(_("%s function is not implemented") % (self.FUNCTION))

            # get and set FUNCTION specific attributes
            if self.FUNCTION in self.FUNC_ATTRS:
                for attr in self.FUNC_ATTRS[self.FUNCTION]:
                    value = self.establishment.data_source_settings.get(attr)
                    if value:
                        setattr(self, attr.upper(), value)

            if not hasattr(self, "HEADERS") or not isinstance(self.HEADERS, dict):
                self.HEADERS = {}

            try:
                self.HEADERS.update(func())
            except Exception as e:
                raise ImproperlyConfigured(_("Error while generating header : %s") % e)

    def decode_value(self, value: Union[bytes, str]) -> str:
        return value.decode("utf8") if isinstance(value, bytes) else value

    def search_user(self, search_value: str, search_attr: Optional[str] = None) -> Union[bool, List[Dict[str, Any]]]:
        response = None
        self.search_value = search_value

        if search_attr is None:
            search_attr = self.SEARCH_ATTR

        attributes = {
            self.EMAIL_ATTR: 'email',
            self.LASTNAME_ATTR: 'lastname',
            self.FIRSTNAME_ATTR: 'firstname',
            self.DISPLAY_ATTR: 'display_name',
        }

        # GET format, will be appended to
        # look at PATH and search for string format parameters
        formatter = string.Formatter()
        fields = [field[1] for field in formatter.parse(self.PATH) if field[1] is not None]

        if fields:
            try:
                string_args = {field: getattr(self, field) for field in fields}
            except AttributeError as e:
                raise ImproperlyConfigured(_("Unknown value : %s") % e)

            request_string = f"{self.HOST}:{self.PORT}/{self.PATH.format(**string_args)}"

        else:
            # default
            search_filter = f"?{search_attr}={search_value}*"
            logger.debug(f"REST Filter : {search_filter}")
            request_string = f"{self.HOST}:{self.PORT}/{self.PATH}{search_filter}"

        try:
            response = requests.get(request_string, headers=self.HEADERS)
            content = json.loads(response.content.decode("utf-8"))
            if response.status_code != 200:
                raise
        except Exception as e:
            if response and hasattr(response, "status_code"):
                logger.error("Can't perform REST search (error %s) : %s", (response.status_code, e))
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

