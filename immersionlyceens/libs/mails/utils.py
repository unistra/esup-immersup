import logging
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from importlib import import_module

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.message import sanitize_address
from immersionlyceens.libs.utils import get_general_setting

logger = logging.getLogger(__name__)


def import_mail_backend():
    default = 'immersionlyceens.libs.mails.backends.ConsoleBackend'
    path = getattr(settings, 'EMAIL_BACKEND', default).split('.')
    return getattr(import_module('.'.join(path[:-1])), path[-1])


mail_backend = import_mail_backend()


def send_email(address, subject, body, from_addr=None, reply_to=None, copies=()):
    """
    """
    # Get configured 'from' address or the default settings/<env>.py one
    encoding = settings.DEFAULT_CHARSET

    if not from_addr:
        try:
            from_addr = get_general_setting("MAIL_FROM")
        except Exception as e:
            from_addr = settings.DEFAULT_FROM_EMAIL

    if settings.FORCE_EMAIL_ADDRESS:
        recipient = settings.FORCE_EMAIL_ADDRESS
        cc = [settings.FORCE_EMAIL_ADDRESS] if copies else []
    else:
        recipient = address
        cc = list(map(lambda a: sanitize_address(a, encoding), copies))

    if not recipient:
        logger.warning("Cannot send mail (no email address specified)")
        return

    # Email data
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sanitize_address(from_addr, encoding)
    msg['To'] = sanitize_address(recipient, encoding)
    msg['Cc'] = ", ".join(cc)

    if reply_to:
        msg['Reply-To'] = sanitize_address(reply_to, encoding)

    html = body

    # part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    # msg.attach(part1)
    msg.attach(part2)
    try:
        mail_backend().send_message(msg)
    except AttributeError:
        # For unittests, use Django Email Backend
        email = EmailMessage(
            subject,
            html,
            settings.DEFAULT_FROM_EMAIL,
            [sanitize_address(recipient, encoding)]
        )
        email.send()
    except Exception as e:
        logger.error(
            f"Cannot send message to {recipient} : unexpected error: {e} - {sys.exc_info()[0]}",
            extra={'locals': locals()},
        )
        raise
    else:
        logger.info("Mail sent to %s", recipient)
