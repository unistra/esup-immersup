import datetime
import logging
import os
import smtplib
import sys

from django.conf import settings

logger = logging.getLogger(__name__)


class BaseEmailBackend:
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def send_message(self, email_message):
        raise NotImplementedError


class EmailBackend(BaseEmailBackend):

    def __init__(self, *args, **kwargs):
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        self.port = getattr(settings, 'EMAIL_PORT', 25)
        self.host = getattr(settings, 'EMAIL_HOST', '127.0.0.1')
        self.host_user = getattr(settings, 'EMAIL_HOST_USER', '')
        self.host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.ssl_on_connect = getattr(settings, 'EMAIL_SSL_ON_CONNECT', False)
        # self.from_addr = getattr(settings, 'FROM_ADDR', None)
        super().__init__(*args, **kwargs)

    def send_message(self, email_message):
        sent = False

        smtp_func = smtplib.SMTP_SSL if self.ssl_on_connect else smtplib.SMTP

        with smtp_func(host=self.host, port=self.port) as s:
            if self.use_tls and not self.ssl_on_connect:
                s.starttls()

            if self.host_user and self.host_password:
                s.login(self.host_user, self.host_password)

            try:
                s.send_message(email_message, from_addr=email_message["From"])
                sent = True
            except Exception:
                logger.error("Cannot send email : %s" %
                             sys.exc_info()[0],
                             extra={'locals': locals()})
                if not self.fail_silently:
                    raise

        return sent


class ConsoleBackend(BaseEmailBackend):

    def send_message(self, email_message):
        print(email_message.as_string())
        print('-' * 80)


class FileBackend(BaseEmailBackend):

    def __init__(self, *args, **kwargs):
        self.file_path = getattr(settings, 'EMAIL_FILE_PATH', None)
        if os.path.exists(self.file_path)\
                and not os.path.isdir(self.file_path):
            raise Exception('EMAIL_FILE_PATH parameter %s is not a directory'
                            % self.file_path)
        elif not os.path.exists(self.file_path):
            os.makedirs(self.file_path)

    def send_message(self, email_message):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = os.path.join(self.file_path, 'immersionlyceens-%s' % timestamp)
        with open(file_name, 'w') as fh:
            fh.write(email_message.as_string())
            fh.write('-' * 80)
            fh.write('\n')
