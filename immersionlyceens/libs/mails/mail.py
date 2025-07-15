import logging
from email_validator import validate_email, EmailNotValidError
from typing import Any, Dict, Optional, List, Union

from django.utils.translation import pgettext, gettext
from immersionlyceens.apps.core.models import ImmersionUser, MailTemplate

from .utils import send_email

logger = logging.getLogger(__name__)

class Mail(object):
    """
    Mail object to parse and send a template depending on multiple settings
    """
    def __init__(
            self,
            request,
            recipient_type: Optional[str],
            template_code: str,
            recipient_user: Union[ImmersionUser, None] = None,
            copies: Optional[List] = (),
            **kwargs):
        """
        :param request: request objet
        :param recipient_type: 'user', 'group' or an email
        :param recipient_user: ImmersionUser the mail will be sent to
        :param template_code: Template object code to use
        :param copies: list of other emails to send the message (CCs)
        """
        self.request = request
        self.recipient_type = recipient_type
        self.recipient_user = recipient_user
        self.template_code = template_code
        self.template = None
        self.recipient = None
        self.body = None

        try:
            self.set_template()
        except Exception as e:
            logger.error(f"Cannot set template {self.template_code}: {e}")
            raise

        try:
            self.recipient = self.set_recipient()
        except Exception as e:
            logger.error(f"Cannot parse recipient type {self.recipient_type}: {e}")
            raise

        # Multiple recipients ?
        self.other_recipients = copies if copies and isinstance(copies, list) else []

        try:
            self.parse_template(**kwargs)
        except Exception as e:
            logger.error(f"Cannot parse template {self.template_code}: {e}")
            raise

    def set_template(self):
        try:
            self.template = MailTemplate.objects.get(code=self.template_code, active=True)
            logger.debug("Template found : %s" % self.template)
        except MailTemplate.DoesNotExist:
            msg = "Template %s not found or inactive" % self.template_code
            logger.error(msg)
            raise Exception(msg)

    def parse_template(self, **kwargs):
        try:
            self.body = self.template.parse_vars(
                user=self.recipient_user,
                request=self.request,
                recipient=self.recipient,
                **kwargs
            )
        except Exception as e:
            msg = gettext("Couldn't parse template vars : %s" % e)
            logger.error(msg)
            raise Exception(msg)

    def set_recipient(self):
        if self.recipient_type == 'user':
            return self.recipient_user.email

        # No direct recipient : depends on the group
        if self.recipient_type == 'group':
            return

        # Eventually assume it's an email address
        try:
            validate_email(self.recipient_type)
            return self.recipient_type
        except EmailNotValidError as e:
            raise

    def send(self):
        try:
            send_email(self.recipient, self.template.subject, self.body, copies=self.other_recipients)
        except Exception as e:
            msg = gettext("Couldn't send email : %s" % e)
            logger.exception(msg)
            raise Exception(msg)