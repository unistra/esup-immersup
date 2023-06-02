#!/usr/bin/env python
"""
Send a message containing the global survey link
"""
import datetime
import logging
import sys

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.management.base import BaseCommand, CommandError

from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting

from ...models import Immersion, MailTemplate, Slot, UniversityYear
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = _("Send global evaluation message : success")
        template_code = 'EVALUATION_GLOBALE'
        today = timezone.localdate()

        # Settings check
        # Get evaluation date in University year
        try:
            year = UniversityYear.get_active()
        except Exception as e:
            msg = _("University year settings errors : %s") % e
            logger.error(msg)
            raise CommandError(msg)

        if not year:
            msg = ("""Cannot find university year global evaluation date. """
                   """Please check your University year settings in admin section.""")
            logger.error(msg)
            raise CommandError(msg)

        if not settings.DEBUG and today != year.global_evaluation_date: # Not today. Oh, except for the DEBUG mode ;)
            return _("Send global evaluation message : nothing to do")

        # Get the mailing list address
        try:
            mailing_list_address = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            msg = _("Cannot find GLOBAL_MAILING_LIST address. Please check the General Settings in admin section.")
            logger.error(msg)
            raise CommandError(msg)

        # Email template
        try:
            template = MailTemplate.objects.get(code=template_code, active=True)
            logger.debug("Template found : %s" % template)
        except MailTemplate.DoesNotExist:
            msg = _("Cannot find active template '%s'. Please check the Messages Templates in admin section.")\
                  % template_code
            logger.error(msg)
            raise CommandError(msg)

        #############

        # Here we are.
        try:
            message_body = template.parse_vars(user=None, request=None)
            logger.debug("Message body : %s" % message_body)
            send_email(mailing_list_address, template.subject, message_body)
        except Exception as e:
            msg = _("Cannot send email to mailing list : '%s'") % e
            logger.error(msg)
            raise CommandError(msg)

        logger.info(success)
        return success
