#!/usr/bin/env python
"""
Send a notification when a slot is available for registration
This command is meant to be run in the evening
"""
import logging

import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from immersionlyceens.libs.mails.utils import send_email

from ...models import Course, MailTemplate, UserCourseAlert
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = _("Send course alerts : success")
        returns = []
        template_code = 'ALERTE_DISPO'
        courses_dict = {}
        today = datetime.datetime.today().date()

        # Email template
        try:
            template = MailTemplate.objects.get(code=template_code, active=True)
            logger.debug("Template found : %s" % template)
        except MailTemplate.DoesNotExist:
            msg = _("Cannot find an active template named '%s'. Please check the Messages Templates in admin section.")\
                % template_code
            logger.error(msg)
            raise CommandError(msg)

        courses = Course.objects.prefetch_related('slots').filter(slots__date__gt=today)

        for course in courses:
            slot_list = []
            for slot in course.slots.filter(date__gt=today).order_by('date', 'start_time'):
                if slot.available_seats() > 0:
                    slot_list.append(slot)

            if slot_list:
                courses_dict[course.id] = slot_list.copy()

        alerts = UserCourseAlert.objects.prefetch_related('course')\
                .filter(course__id__in=courses_dict.keys(), email_sent=False)

        for alert in alerts:
            slots = courses_dict[alert.course.id]
            try:
                message_body = template.parse_vars(user=None, request=None, slot_list=slots, course=alert.course)
                logger.debug("Message body : %s" % message_body)
                send_email(alert.email, template.subject, message_body)
                alert.email_sent = True
                alert.save()
            except Exception as e:
                logger.exception(e)
                returns.append(_("Cannot send email to %s : '%s'") % (alert.email, e))

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)

        logger.info(success)
        return success