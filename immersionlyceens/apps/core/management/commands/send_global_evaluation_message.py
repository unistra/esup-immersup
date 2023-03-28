#!/usr/bin/env python
"""
Send a message containing the global survey link
"""
import datetime
import logging
import sys

from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError

from immersionlyceens.libs.mails.utils import send_email
from immersionlyceens.libs.utils import get_general_setting

from ...models import Immersion, MailTemplate, Slot, UniversityYear

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        template_code = 'EVALUATION_GLOBALE'
        today = timezone.localdate()

        # Settings check
        # Get evaluation date in University year
        try:
            year = UniversityYear.get_active()
        except Exception as e:
            logger.error("University year settings errors : %s", e)
            return

        if not year:
            logger.error(
                """Cannot find university year global evaluation date. """
                """Please check your University year settings in admin section."""
            )

        if not settings.DEBUG and today != year.global_evaluation_date: # Not today. Oh, except for the DEBUG mode ;)
            return

        # Get the mailing list address
        try:
            mailing_list_address = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            logger.error("Cannot find GLOBAL_MAILING_LIST address. Please check the General Settings in admin section.")
            sys.exit("GLOBAL_MAILING_LIST variable not configured properly in core General Settings")

        # Email template
        try:
            template = MailTemplate.objects.get(code=template_code, active=True)
            logger.debug("Template found : %s" % template)
        except MailTemplate.DoesNotExist:
            logger.error(
                "Cannot find an active template named '%s'. Please check the Messages Templates in admin section.",
                template_code
            )
            return

        #############

        # Here we are.
        try:
            message_body = template.parse_vars(user=None, request=None)
            logger.debug("Message body : %s" % message_body)
            send_email(mailing_list_address, template.subject, message_body)
        except Exception as e:
            logger.exception(e)
            logger.error("Cannot send email to mailing list : '%s'", e)

        return
