from django.conf import settings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from importlib import import_module
import logging
import sys

logger = logging.getLogger(__name__)


def import_mail_backend():
    default = 'immersionlyceens.libs.mails.backends.ConsoleBackend'
    path = getattr(settings, 'EMAIL_BACKEND', default).split('.')
    return getattr(import_module('.'.join(path[:-1])), path[-1])


mail_backend = import_mail_backend()


def send_email(address, subject, body):
    """
    """

    recipient = settings.FORCE_EMAIL_ADDRESS if settings.FORCE_EMAIL_ADDRESS else address

    if not recipient:
        logger.warning("Cannot send mail (no email address specified)")
        return

    # Email data
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.DEFAULT_FROM_EMAIL
    msg['To'] = recipient
    html = body

    # part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    # msg.attach(part1)
    msg.attach(part2)
    try:
        mail_backend().send_message(msg)
    except Exception as e:
        logger.error("Cannot send message to {} : unexpected error: {} - {}"
                     .format(recipient, e, sys.exc_info()[0]),
                     extra={'locals': locals()})
    else:
        logger.info("Mail sent to %s", recipient)
